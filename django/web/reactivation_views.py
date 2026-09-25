import json
import uuid
from datetime import timedelta
from decimal import Decimal

import razorpay
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Prefetch

from .models import (
    CentreReactivationAuditLog,
    CentreReactivationPayment,
    CentreReactivationSettings,
    CentreUserAccount,
)
from .reactivation_forms import CentreManualDisableForm, CentreReactivationSettingsForm
from .reactivation_services import (
    calculate_reactivation_amount,
    centre_payment_available,
    centre_reactivation_message,
    complete_reactivation_payment,
    get_reactivation_settings,
    manually_disable_centre,
    manually_enable_centre,
    set_payment_status,
)
from .views import AdminOrHeadOfficeRequiredMixin, FranchiseAuthenticatedMixin


def _razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _centre_for_request(request):
    return get_object_or_404(
        CentreUserAccount.objects.select_related("user"), user=request.user
    )


class CentreReactivationView(FranchiseAuthenticatedMixin, View):
    template_name = "web/franchise/reactivation.html"

    def get(self, request, *args, **kwargs):
        centre = _centre_for_request(request)
        if not (centre.inactive_due_to_inactivity or centre.manual_disabled):
            return redirect("web:centre_dashboard")
        settings_obj = get_reactivation_settings()
        payment_available = centre_payment_available(centre, settings_obj)
        return render(
            request,
            self.template_name,
            {
                "centre": centre,
                "reactivation_settings": settings_obj,
                "reactivation_amount": calculate_reactivation_amount(centre, settings_obj),
                "reactivation_message": centre_reactivation_message(centre, settings_obj),
                "payment_available": payment_available,
                "is_manual_restriction": centre.manual_disabled,
                "enquiry_subject": "Centre Enable Request",
                "reactivation_centre_id": centre.formatted_id,
                "reactivation_centre_name": (
                    centre.centre_name
                    or centre.owner_centre
                    or centre.name
                    or centre.user.username
                ),
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            },
        )


class CentreReactivationOrderView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        centre = _centre_for_request(request)
        settings_obj = get_reactivation_settings()
        if not (centre.inactive_due_to_inactivity or centre.manual_disabled):
            return JsonResponse(
                {"success": False, "message": "This centre does not require reactivation."},
                status=409,
            )
        if not centre_payment_available(centre, settings_obj):
            return JsonResponse(
                {"success": False, "message": "Online reactivation payment is currently disabled. Please contact Head Office."},
                status=403,
            )

        with transaction.atomic():
            # Serialise order creation per centre so double-clicks or concurrent
            # requests reuse one active Razorpay order.
            centre = CentreUserAccount.objects.select_for_update().get(pk=centre.pk)
            if not (centre.inactive_due_to_inactivity or centre.manual_disabled):
                return JsonResponse(
                    {"success": False, "message": "This centre does not require reactivation."},
                    status=409,
                )
            if not centre_payment_available(centre, settings_obj):
                return JsonResponse(
                    {"success": False, "message": "Online reactivation payment is currently disabled. Please contact Head Office."},
                    status=403,
                )
            amount = calculate_reactivation_amount(centre, settings_obj)
            recent_pending = (
                CentreReactivationPayment.objects.filter(
                    centre=centre,
                    status__in=(
                        CentreReactivationPayment.Status.CREATED,
                        CentreReactivationPayment.Status.PENDING,
                        CentreReactivationPayment.Status.AUTHORIZED,
                    ),
                    created_at__gte=timezone.now() - timedelta(minutes=30),
                )
                .order_by("-created_at", "-pk")
                .first()
            )
            if recent_pending:
                return JsonResponse(
                    {
                        "success": True,
                        "razorpay_order_id": recent_pending.razorpay_order_id,
                        "amount": int(recent_pending.amount * Decimal("100")),
                        "currency": recent_pending.currency,
                    }
                )

            try:
                client = _razorpay_client()
                order = client.order.create(
                    data={
                        "amount": int(amount * Decimal("100")),
                        "currency": "INR",
                        "payment_capture": 1,
                        "receipt": f"reactivation-{centre.pk}-{uuid.uuid4().hex[:12]}",
                    }
                )
            except Exception:
                return JsonResponse(
                    {"success": False, "message": "Unable to start payment right now. Please retry or contact Head Office."},
                    status=502,
                )

            payment = CentreReactivationPayment.objects.create(
                centre=centre,
                amount=amount,
                currency="INR",
                status=CentreReactivationPayment.Status.CREATED,
                razorpay_order_id=order["id"],
            )
            CentreReactivationAuditLog.objects.create(
                centre=centre,
                actor=request.user,
                event=CentreReactivationAuditLog.Event.PAYMENT_ATTEMPT,
                details={
                    "order_id": payment.razorpay_order_id,
                    "amount": str(amount),
                },
            )

        return JsonResponse(
            {
                "success": True,
                "razorpay_order_id": payment.razorpay_order_id,
                "amount": int(amount * Decimal("100")),
                "currency": "INR",
            }
        )


class CentreReactivationCallbackView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "message": "Invalid payment response."}, status=400)

        order_id = payload.get("razorpay_order_id", "")
        payment_id_value = payload.get("razorpay_payment_id", "")
        signature = payload.get("razorpay_signature", "")
        payment = get_object_or_404(
            CentreReactivationPayment,
            centre__user=request.user,
            razorpay_order_id=order_id,
        )
        if not centre_payment_available(payment.centre, get_reactivation_settings()):
            return JsonResponse(
                {"success": False, "message": "Online reactivation payment is not enabled for this centre."},
                status=403,
            )
        if not order_id or not payment_id_value or not signature:
            return JsonResponse({"success": False, "message": "Incomplete payment verification data."}, status=400)

        client = _razorpay_client()
        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id_value,
                    "razorpay_signature": signature,
                }
            )
            payment_details = client.payment.fetch(payment_id_value)
        except razorpay.errors.SignatureVerificationError:
            set_payment_status(
                payment,
                CentreReactivationPayment.Status.FAILED,
                payment_id_value=payment_id_value,
                failure_code="signature_verification_failed",
                failure_description="Razorpay signature verification failed.",
                actor=request.user,
            )
            return JsonResponse({"success": False, "message": "Payment verification failed."}, status=400)
        except Exception:
            return JsonResponse({"success": False, "message": "Payment verification is temporarily unavailable."}, status=502)

        provider_order_id = payment_details.get("order_id")
        if provider_order_id and provider_order_id != order_id:
            set_payment_status(
                payment,
                CentreReactivationPayment.Status.FAILED,
                payment_id_value=payment_id_value,
                failure_code="order_mismatch",
                failure_description="Razorpay payment order mismatch.",
                actor=request.user,
            )
            return JsonResponse({"success": False, "message": "Payment verification failed."}, status=400)

        provider_amount = payment_details.get("amount")
        expected_amount = int(payment.amount * Decimal("100"))
        try:
            amount_matches = provider_amount is None or int(provider_amount) == expected_amount
        except (TypeError, ValueError):
            amount_matches = False
        if not amount_matches:
            set_payment_status(
                payment,
                CentreReactivationPayment.Status.FAILED,
                payment_id_value=payment_id_value,
                failure_code="amount_mismatch",
                failure_description="Razorpay payment amount did not match the server-calculated amount.",
                actor=request.user,
            )
            return JsonResponse({"success": False, "message": "Payment verification failed."}, status=400)

        provider_status = str(payment_details.get("status", "")).lower()
        if provider_status != "captured":
            status = (
                CentreReactivationPayment.Status.AUTHORIZED
                if provider_status == "authorized"
                else CentreReactivationPayment.Status.PENDING
            )
            if status == CentreReactivationPayment.Status.AUTHORIZED:
                set_payment_status(
                    payment,
                    CentreReactivationPayment.Status.PENDING,
                    payment_id_value=payment_id_value,
                    actor=request.user,
                )
            else:
                set_payment_status(
                    payment,
                    status,
                    payment_id_value=payment_id_value,
                    actor=request.user,
                )
            return JsonResponse(
                {"success": False, "status": provider_status or "pending", "message": "Payment is still pending."},
                status=202,
            )

        payment, result = complete_reactivation_payment(
            payment.pk,
            payment_id_value=payment_id_value,
            signature=signature,
            actor=request.user,
        )
        if result == "manual_review":
            return JsonResponse(
                {
                    "success": False,
                    "status": result,
                    "message": (
                        "Payment received successfully. Your enable request has been sent "
                        "to Head Office for approval."
                    ),
                },
                status=409,
            )
        return JsonResponse(
            {
                "success": True,
                "status": result,
                "redirect_url": "/franchise-dashboard/dashboard/",
            }
        )


class CentreReactivationStatusView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"success": False}, status=400)
        payment = get_object_or_404(
            CentreReactivationPayment,
            centre__user=request.user,
            razorpay_order_id=payload.get("razorpay_order_id", ""),
        )
        if not centre_payment_available(payment.centre, get_reactivation_settings()):
            return JsonResponse(
                {"success": False, "message": "Online reactivation payment is not enabled for this centre."},
                status=403,
            )
        status = payload.get("status", "")
        if status == "failed":
            payment_status = CentreReactivationPayment.Status.FAILED
        elif status == "cancelled":
            payment_status = CentreReactivationPayment.Status.CANCELLED
        else:
            payment_status = CentreReactivationPayment.Status.PENDING
        set_payment_status(
            payment,
            payment_status,
            payment_id_value=payload.get("razorpay_payment_id", ""),
            failure_code=str(payload.get("error_code", "")),
            failure_description=str(payload.get("error_description", "")),
            actor=request.user,
        )
        return JsonResponse({"success": True, "status": payment_status})


@method_decorator(csrf_exempt, name="dispatch")
class CentreReactivationWebhookView(View):
    def post(self, request, *args, **kwargs):
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not webhook_secret or not signature:
            return JsonResponse({"success": False}, status=503)
        client = _razorpay_client()
        try:
            client.utility.verify_webhook_signature(
                request.body.decode("utf-8"), signature, webhook_secret
            )
            payload = json.loads(request.body or "{}")
        except (ValueError, razorpay.errors.SignatureVerificationError):
            return JsonResponse({"success": False}, status=400)

        event = payload.get("event", "")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = entity.get("order_id")
        payment_id_value = entity.get("id", "")
        payment = CentreReactivationPayment.objects.filter(
            razorpay_order_id=order_id
        ).first()
        if not payment:
            return JsonResponse({"success": True})

        if event == "payment.captured" or entity.get("status") == "captured":
            try:
                amount_matches = (
                    entity.get("amount") is None
                    or int(entity.get("amount")) == int(payment.amount * Decimal("100"))
                )
            except (TypeError, ValueError):
                amount_matches = False
            if amount_matches:
                complete_reactivation_payment(
                    payment.pk,
                    payment_id_value=payment_id_value,
                    signature=signature,
                )
            else:
                set_payment_status(
                    payment,
                    CentreReactivationPayment.Status.FAILED,
                    payment_id_value=payment_id_value,
                    failure_code="amount_mismatch",
                    failure_description="Razorpay webhook amount did not match the stored amount.",
                )
        elif event == "payment.failed":
            set_payment_status(
                payment,
                CentreReactivationPayment.Status.FAILED,
                payment_id_value=payment_id_value,
                failure_code=str(entity.get("error_code", "")),
                failure_description=str(entity.get("error_description", "")),
            )
        return JsonResponse({"success": True})


class CentreReactivationSettingsView(AdminOrHeadOfficeRequiredMixin, View):
    template_name = "web/admin_panel/franchise/reactivation_settings.html"

    def _context(self, form):
        settings_obj = CentreReactivationSettings.get_solo()
        payments = CentreReactivationPayment.objects.order_by("-created_at", "-pk")
        centres = CentreUserAccount.objects.select_related("user").prefetch_related(
            Prefetch("reactivation_payments", queryset=payments)
        ).order_by("-inactive_due_to_inactivity", "-pk")
        for centre in centres:
            centre.latest_reactivation_payment = next(iter(centre.reactivation_payments.all()), None)
            centre.reactivation_amount = calculate_reactivation_amount(centre, settings_obj)
        return {
            "form": form,
            "reactivation_settings": settings_obj,
            "centres": centres,
        }

    def get(self, request, *args, **kwargs):
        settings_obj = CentreReactivationSettings.get_solo()
        return render(
            request,
            self.template_name,
            self._context(CentreReactivationSettingsForm(instance=settings_obj)),
        )

    def post(self, request, *args, **kwargs):
        settings_obj = CentreReactivationSettings.get_solo()
        form = CentreReactivationSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Centre Reactivation Settings saved successfully.")
            return redirect("web:centre_reactivation_settings")
        return render(request, self.template_name, self._context(form))


class CentreManualDisableView(AdminOrHeadOfficeRequiredMixin, View):
    template_name = "web/admin_panel/franchise/manual_disable.html"

    def get_centre(self, pk):
        return get_object_or_404(
            CentreUserAccount.objects.select_related("user"), pk=pk
        )

    def get(self, request, pk, *args, **kwargs):
        centre = self.get_centre(pk)
        return render(
            request,
            self.template_name,
            {
                "centre": centre,
                "form": CentreManualDisableForm(
                    initial={"payment_required": False}
                ),
                "reactivation_settings": get_reactivation_settings(),
                "default_amount": calculate_reactivation_amount(
                    centre, get_reactivation_settings()
                ),
            },
        )

    def post(self, request, pk, *args, **kwargs):
        centre = self.get_centre(pk)
        form = CentreManualDisableForm(request.POST)
        if not form.is_valid():
            settings_obj = get_reactivation_settings()
            return render(
                request,
                self.template_name,
                {
                    "centre": centre,
                    "form": form,
                    "reactivation_settings": settings_obj,
                    "default_amount": calculate_reactivation_amount(centre, settings_obj),
                },
            )
        manually_disable_centre(
            centre.pk,
            actor=request.user,
            reason=form.cleaned_data["disable_reason"],
            payment_required=form.cleaned_data["payment_required"],
            fee_override=form.cleaned_data["amount_override"],
        )
        messages.success(request, "Centre disabled manually. The saved message will be shown at login.")
        return redirect("web:admin_centre_profile", pk=centre.pk)


class CentreManualEnableView(AdminOrHeadOfficeRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        centre = get_object_or_404(CentreUserAccount, pk=pk)
        manually_enable_centre(centre.pk, actor=request.user)
        messages.success(request, "Centre enabled successfully.")
        return redirect("web:admin_centre_profile", pk=centre.pk)
