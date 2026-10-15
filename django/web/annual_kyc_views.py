import json
import logging
from decimal import Decimal

import razorpay
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .annual_kyc_forms import AnnualKYCCentreControlForm, AnnualKYCSettingsForm
from .annual_kyc_services import (
    annual_kyc_snapshot,
    annual_kyc_whatsapp_url,
    calculate_annual_kyc_amount,
    complete_annual_kyc_payment,
    create_annual_kyc_order,
    ensure_annual_kyc_status,
    get_annual_kyc_settings,
    manual_mark_annual_kyc_verified,
    resend_annual_kyc_otp,
    set_annual_payment_status,
    verify_annual_kyc_otp,
)
from .models import (
    AnnualKYCSettings,
    CentreAnnualKYCAuditLog,
    CentreAnnualKYCOTPVerification,
    CentreAnnualKYCPayment,
    CentreAnnualKYCStatus,
    CentreUserAccount,
)
from .views import AdminOrHeadOfficeRequiredMixin, FranchiseAuthenticatedMixin

logger = logging.getLogger(__name__)


def _centre_for_request(request):
    return get_object_or_404(
        CentreUserAccount.objects.select_related("user"), user=request.user
    )


def _payload(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body or "{}")
        except (TypeError, ValueError):
            return None
    return request.POST


class AnnualKYCRenewalView(FranchiseAuthenticatedMixin, View):
    template_name = "web/franchise/annual_kyc.html"

    def get(self, request, *args, **kwargs):
        centre = _centre_for_request(request)
        if centre.inactive_due_to_inactivity or centre.manual_disabled:
            return redirect("web:centre_reactivation")
        snapshot = annual_kyc_snapshot(centre)
        payment = snapshot["latest_payment"]
        otp = snapshot["latest_otp"]
        if payment and payment.status != CentreAnnualKYCPayment.Status.SUCCESS:
            payment = None
            otp = None
        if payment and otp:
            request.session["annual_kyc_payment_id"] = payment.pk
        days_overdue = 0
        if snapshot["state"] in {"due", "grace", "expired"} and snapshot.get("due_date"):
            days_overdue = max(0, (timezone.localdate() - snapshot["due_date"]).days)
        return render(
            request,
            self.template_name,
            {
                "centre": centre,
                "annual_kyc": snapshot,
                "annual_kyc_settings": snapshot["settings"],
                "annual_kyc_amount": calculate_annual_kyc_amount(centre, snapshot["settings"]),
                "annual_kyc_payment": payment,
                "annual_kyc_otp": otp,
                "annual_kyc_days_overdue": days_overdue,
                "annual_kyc_whatsapp_url": annual_kyc_whatsapp_url(centre, snapshot["settings"]),
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "annual_kyc_flow": True,
            },
        )


class AnnualKYCOrderView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        centre = _centre_for_request(request)
        try:
            payment = create_annual_kyc_order(centre, actor=request.user)
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=403)
        except RuntimeError:
            return JsonResponse(
                {"success": False, "message": "Unable to start payment right now. Please retry later."},
                status=502,
            )
        return JsonResponse(
            {
                "success": True,
                "razorpay_order_id": payment.razorpay_order_id,
                "amount": int(payment.amount * Decimal("100")),
                "currency": payment.currency,
            }
        )


class AnnualKYCCallbackView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        payload = _payload(request)
        if payload is None:
            return JsonResponse({"success": False, "message": "Invalid payment response."}, status=400)
        order_id = payload.get("razorpay_order_id", "")
        payment_id_value = payload.get("razorpay_payment_id", "")
        signature = payload.get("razorpay_signature", "")
        payment = get_object_or_404(
            CentreAnnualKYCPayment,
            centre__user=request.user,
            razorpay_order_id=order_id,
        )
        if not annual_kyc_snapshot(payment.centre)["online_allowed"]:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Online annual KYC payment is no longer available. Please contact Head Office.",
                },
                status=403,
            )
        if not order_id or not payment_id_value or not signature:
            return JsonResponse({"success": False, "message": "Incomplete payment verification data."}, status=400)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
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
            set_annual_payment_status(
                payment,
                CentreAnnualKYCPayment.Status.FAILED,
                payment_id_value=payment_id_value,
                signature=signature,
                failure_code="signature_verification_failed",
                actor=request.user,
            )
            return JsonResponse({"success": False, "message": "Payment verification failed."}, status=400)
        except Exception:
            logger.exception("Annual KYC Razorpay verification failed for centre %s", payment.centre_id)
            return JsonResponse({"success": False, "message": "Payment verification is temporarily unavailable."}, status=502)

        if payment_details.get("order_id") and payment_details.get("order_id") != order_id:
            set_annual_payment_status(
                payment, CentreAnnualKYCPayment.Status.FAILED,
                payment_id_value=payment_id_value, signature=signature,
                failure_code="order_mismatch", actor=request.user,
            )
            return JsonResponse({"success": False, "message": "Payment verification failed."}, status=400)
        try:
            amount_matches = int(payment_details.get("amount")) == int(payment.amount * Decimal("100"))
        except (TypeError, ValueError):
            amount_matches = False
        if not amount_matches:
            set_annual_payment_status(
                payment, CentreAnnualKYCPayment.Status.FAILED,
                payment_id_value=payment_id_value, signature=signature,
                failure_code="amount_mismatch", actor=request.user,
            )
            return JsonResponse({"success": False, "message": "Payment verification failed."}, status=400)

        if str(payment_details.get("status", "")).lower() != "captured":
            set_annual_payment_status(
                payment, CentreAnnualKYCPayment.Status.PENDING,
                payment_id_value=payment_id_value, signature=signature, actor=request.user,
            )
            return JsonResponse({"success": False, "status": "pending", "message": "Payment is still pending."}, status=202)

        payment, otp, _ = complete_annual_kyc_payment(
            payment.pk,
            payment_id_value=payment_id_value,
            signature=signature,
            actor=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        request.session["annual_kyc_payment_id"] = payment.pk
        return JsonResponse(
            {
                "success": True,
                "otp_required": otp is not None,
                "otp_delivery_available": otp and otp.status == CentreAnnualKYCOTPVerification.Status.SENT,
                "message": (
                    "Payment verified. Enter the OTP sent to your registered mobile number."
                    if otp and otp.status == CentreAnnualKYCOTPVerification.Status.SENT
                    else "Payment verified, but OTP delivery is temporarily unavailable. Please use resend or contact Head Office."
                ),
            }
        )


class AnnualKYCStatusView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        payload = _payload(request)
        if payload is None:
            return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
        payment = get_object_or_404(
            CentreAnnualKYCPayment,
            centre__user=request.user,
            razorpay_order_id=payload.get("razorpay_order_id", ""),
        )
        if not annual_kyc_snapshot(payment.centre)["online_allowed"]:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Online annual KYC payment is no longer available. Please contact Head Office.",
                },
                status=403,
            )
        status_value = payload.get("status", "")
        payment_status = (
            CentreAnnualKYCPayment.Status.FAILED
            if status_value == "failed"
            else CentreAnnualKYCPayment.Status.CANCELLED
            if status_value == "cancelled"
            else CentreAnnualKYCPayment.Status.PENDING
        )
        set_annual_payment_status(
            payment,
            payment_status,
            payment_id_value=payload.get("razorpay_payment_id", ""),
            failure_code=payload.get("error_code", ""),
            failure_description=payload.get("error_description", ""),
            actor=request.user,
        )
        return JsonResponse({"success": True, "status": payment_status})


class AnnualKYCResendOTPView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        centre = _centre_for_request(request)
        if not annual_kyc_snapshot(centre)["online_allowed"]:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Online annual KYC renewal is no longer available. Please contact Head Office.",
                },
                status=403,
            )
        payment_id = request.session.get("annual_kyc_payment_id")
        payment = get_object_or_404(
            CentreAnnualKYCPayment,
            pk=payment_id,
            centre=centre,
            status=CentreAnnualKYCPayment.Status.SUCCESS,
        )
        try:
            otp, _ = resend_annual_kyc_otp(
                payment,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=429)
        return JsonResponse(
            {
                "success": otp.status == CentreAnnualKYCOTPVerification.Status.SENT,
                "message": "A new OTP has been sent." if otp.status == CentreAnnualKYCOTPVerification.Status.SENT else "OTP delivery is temporarily unavailable.",
            },
            status=200,
        )


class AnnualKYCVerifyOTPView(FranchiseAuthenticatedMixin, View):
    def post(self, request, *args, **kwargs):
        payload = _payload(request)
        if payload is None:
            return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
        centre = _centre_for_request(request)
        if not annual_kyc_snapshot(centre)["online_allowed"]:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Online annual KYC renewal is no longer available. Please contact Head Office.",
                },
                status=403,
            )
        payment = get_object_or_404(
            CentreAnnualKYCPayment,
            pk=request.session.get("annual_kyc_payment_id"),
            centre=centre,
            status=CentreAnnualKYCPayment.Status.SUCCESS,
        )
        try:
            verify_annual_kyc_otp(
                payment,
                payload.get("otp", ""),
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=400)
        request.session.pop("annual_kyc_payment_id", None)
        return JsonResponse(
            {
                "success": True,
                "message": "Annual KYC renewal completed successfully.",
                "redirect_url": "/franchise-dashboard/dashboard/",
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class AnnualKYCWebhookView(View):
    def post(self, request, *args, **kwargs):
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not webhook_secret or not signature:
            return JsonResponse({"success": False}, status=503)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_webhook_signature(request.body.decode("utf-8"), signature, webhook_secret)
            payload = json.loads(request.body or "{}")
        except (ValueError, razorpay.errors.SignatureVerificationError):
            return JsonResponse({"success": False}, status=400)
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        payment = CentreAnnualKYCPayment.objects.filter(razorpay_order_id=entity.get("order_id")).first()
        if not payment:
            return JsonResponse({"success": True})
        event = payload.get("event", "")
        if event == "payment.captured" or entity.get("status") == "captured":
            try:
                amount_matches = int(entity.get("amount")) == int(payment.amount * Decimal("100"))
            except (TypeError, ValueError):
                amount_matches = False
            if amount_matches:
                complete_annual_kyc_payment(
                    payment.pk,
                    payment_id_value=entity.get("id", ""),
                    signature=signature,
                )
            else:
                set_annual_payment_status(
                    payment, CentreAnnualKYCPayment.Status.FAILED,
                    payment_id_value=entity.get("id", ""),
                    failure_code="amount_mismatch",
                )
        elif event == "payment.failed":
            set_annual_payment_status(
                payment, CentreAnnualKYCPayment.Status.FAILED,
                payment_id_value=entity.get("id", ""),
                failure_code=entity.get("error_code", ""),
                failure_description=entity.get("error_description", ""),
            )
        return JsonResponse({"success": True})


class AnnualKYCSettingsView(AdminOrHeadOfficeRequiredMixin, View):
    template_name = "web/admin_panel/franchise/annual_kyc_settings.html"

    def _context(self, form):
        settings_obj = AnnualKYCSettings.get_solo()
        centres = CentreUserAccount.objects.filter(user__usertype="centre").select_related("user").order_by("owner_centre", "pk")
        rows = []
        for centre in centres:
            status = ensure_annual_kyc_status(centre, settings_obj=settings_obj)
            snapshot = annual_kyc_snapshot(centre, settings_obj=settings_obj)
            latest_payment = centre.annual_kyc_payments.order_by("-created_at", "-pk").first()
            latest_otp = latest_payment.otp_verifications.order_by("-sent_at", "-pk").first() if latest_payment else None
            rows.append({"centre": centre, "status": status, "snapshot": snapshot, "payment": latest_payment, "otp": latest_otp})
        return {"form": form, "annual_kyc_settings": settings_obj, "centre_rows": rows}

    def get(self, request, *args, **kwargs):
        settings_obj = AnnualKYCSettings.get_solo()
        return render(request, self.template_name, self._context(AnnualKYCSettingsForm(instance=settings_obj)))

    def post(self, request, *args, **kwargs):
        settings_obj = AnnualKYCSettings.get_solo()
        form = AnnualKYCSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            changed = form.changed_data
            form.save()
            CentreAnnualKYCAuditLog.objects.create(
                actor=request.user,
                event=CentreAnnualKYCAuditLog.Event.SETTINGS_UPDATED,
                details={"fields": changed},
            )
            messages.success(request, "Annual Centre KYC settings saved successfully.")
            return redirect("web:annual_kyc_settings")
        return render(request, self.template_name, self._context(form))


class AnnualKYCCentreDetailView(AdminOrHeadOfficeRequiredMixin, View):
    template_name = "web/admin_panel/franchise/annual_kyc_centre.html"

    def get_centre(self, pk):
        return get_object_or_404(CentreUserAccount.objects.select_related("user"), pk=pk)

    def _context(self, centre, form):
        status = ensure_annual_kyc_status(centre)
        snapshot = annual_kyc_snapshot(centre)
        payments = centre.annual_kyc_payments.order_by("-created_at", "-pk")[:25]
        audits = centre.annual_kyc_audit_logs.select_related("actor").order_by("-created_at", "-pk")[:100]
        return {
            "centre": centre,
            "status": status,
            "annual_kyc": snapshot,
            "form": form,
            "payments": payments,
            "audits": audits,
            "annual_kyc_amount": calculate_annual_kyc_amount(centre),
        }

    def get(self, request, pk, *args, **kwargs):
        centre = self.get_centre(pk)
        status = ensure_annual_kyc_status(centre)
        return render(request, self.template_name, self._context(centre, AnnualKYCCentreControlForm(instance=status)))

    def post(self, request, pk, *args, **kwargs):
        centre = self.get_centre(pk)
        status = ensure_annual_kyc_status(centre)
        action = request.POST.get("action", "save_controls")
        if action == "manual_verify":
            try:
                manual_mark_annual_kyc_verified(
                    centre,
                    actor=request.user,
                    reason=request.POST.get("manual_verify_reason", ""),
                )
            except ValueError as exc:
                form = AnnualKYCCentreControlForm(request.POST, instance=status)
                form.add_error("manual_verify_reason", str(exc))
                return render(request, self.template_name, self._context(centre, form))
            messages.success(request, "Centre marked as verified and the next due date was recalculated.")
            return redirect("web:annual_kyc_centre", pk=centre.pk)

        form = AnnualKYCCentreControlForm(request.POST, instance=status)
        if form.is_valid():
            changed = form.changed_data
            before_blocked = status.manual_blocked
            before_due = status.manual_due_date
            before_fee = status.fee_override
            saved = form.save()
            if before_fee != saved.fee_override:
                CentreAnnualKYCAuditLog.objects.create(
                    centre=centre, actor=request.user,
                    event=CentreAnnualKYCAuditLog.Event.FEE_OVERRIDE_UPDATED,
                    details={"old": str(before_fee or ""), "new": str(saved.fee_override or "")},
                )
            if before_due != saved.manual_due_date:
                CentreAnnualKYCAuditLog.objects.create(
                    centre=centre, actor=request.user,
                    event=CentreAnnualKYCAuditLog.Event.DUE_DATE_EXTENDED,
                    details={"old": str(before_due or ""), "new": str(saved.manual_due_date or "")},
                )
            if before_blocked != saved.manual_blocked:
                CentreAnnualKYCAuditLog.objects.create(
                    centre=centre, actor=request.user,
                    event=(CentreAnnualKYCAuditLog.Event.MANUAL_BLOCKED if saved.manual_blocked else CentreAnnualKYCAuditLog.Event.MANUAL_UNBLOCKED),
                    details={"reason": saved.manual_block_reason},
                )
            messages.success(request, "Annual KYC centre controls saved.")
            return redirect("web:annual_kyc_centre", pk=centre.pk)
        return render(request, self.template_name, self._context(centre, form))
