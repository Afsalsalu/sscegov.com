"""Business rules for the independent annual centre KYC workflow."""

import calendar
import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from importlib import import_module
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import (
    AnnualKYCSettings,
    CentreAnnualKYCAuditLog,
    CentreAnnualKYCOTPVerification,
    CentreAnnualKYCPayment,
    CentreAnnualKYCStatus,
    CentreUserAccount,
)
from .whatsapp_utils import normalize_whatsapp_number, resolve_user_state

logger = logging.getLogger(__name__)


def get_annual_kyc_settings():
    return AnnualKYCSettings.get_solo()


def add_months(value, months):
    """Add calendar months without turning 31 January into an invalid date."""

    month_index = value.month - 1 + int(months)
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def centre_activation_at(centre):
    user = getattr(centre, "user", None)
    return (
        getattr(centre, "created_at", None)
        or getattr(user, "date_joined", None)
        or timezone.now()
    )


def ensure_annual_kyc_status(centre, *, settings_obj=None):
    """Create/repair the annual cycle using account activation, never login activity."""

    settings_obj = settings_obj or get_annual_kyc_settings()
    status, created = CentreAnnualKYCStatus.objects.get_or_create(centre=centre)
    if created or status.next_kyc_due_at is None:
        base = status.last_kyc_verified_at or centre_activation_at(centre)
        status.next_kyc_due_at = add_months(base, settings_obj.renewal_interval_months)
        status.save(update_fields=("next_kyc_due_at", "updated_at"))
    return status


def _centre_name(centre):
    user = getattr(centre, "user", None)
    return (
        centre.centre_name
        or centre.owner_centre
        or centre.name
        or getattr(user, "username", "centre")
    )


def _format_message(template, *, centre, days=0, grace_days=0, due_at=None):
    due_at = due_at or getattr(centre.annual_kyc_status, "next_kyc_due_at", timezone.now())
    values = {
        "days": max(0, int(days)),
        "grace_days": max(0, int(grace_days)),
        "due_date": timezone.localtime(due_at).strftime("%d %b %Y"),
        "centre_name": _centre_name(centre),
        "centre_id": centre.formatted_id,
    }
    try:
        return str(template).format(**values)
    except (KeyError, IndexError, ValueError):
        return str(template)


def effective_due_at(status):
    if status.manual_due_date:
        due_date = datetime.combine(status.manual_due_date, datetime.min.time())
        return timezone.make_aware(due_date, timezone.get_current_timezone())
    return status.next_kyc_due_at


def annual_kyc_snapshot(centre, *, now=None, settings_obj=None):
    """Return the authoritative current KYC state used by views, middleware and UI."""

    now = now or timezone.now()
    settings_obj = settings_obj or get_annual_kyc_settings()
    status = ensure_annual_kyc_status(centre, settings_obj=settings_obj)
    due_at = effective_due_at(status)
    due_date = timezone.localtime(due_at).date() if due_at else None
    today = timezone.localdate(now)
    days_to_due = (due_date - today).days if due_date else None

    state = "disabled"
    if settings_obj.enabled:
        if status.manual_blocked:
            state = "blocked"
        elif due_at and now < due_at:
            state = (
                "warning"
                if days_to_due is not None and days_to_due <= settings_obj.warning_period_days
                else "not_due"
            )
        elif due_at:
            grace_end = due_at + timedelta(days=settings_obj.grace_period_days)
            if due_date and today == due_date:
                state = "due"
            else:
                state = "grace" if now < grace_end else "expired"

    warning_days = max(0, days_to_due or 0)
    grace_end = due_at + timedelta(days=settings_obj.grace_period_days) if due_at else None
    grace_days = max(0, (timezone.localtime(grace_end).date() - today).days) if grace_end else 0
    online_allowed = state in {"warning", "due", "grace"} and settings_obj.payment_enabled
    restricted = state in {"blocked", "due", "grace", "expired"}
    latest_payment = centre.annual_kyc_payments.order_by("-created_at", "-pk").first()
    latest_otp = None
    if latest_payment:
        latest_otp = latest_payment.otp_verifications.order_by("-sent_at", "-pk").first()

    if state == "warning":
        message = _format_message(
            settings_obj.dashboard_warning_text,
            centre=centre,
            days=warning_days,
            grace_days=grace_days,
            due_at=due_at,
        )
    elif state == "grace":
        message = _format_message(
            settings_obj.grace_period_warning_text,
            centre=centre,
            days=grace_days,
            grace_days=grace_days,
            due_at=due_at,
        )
    elif state == "expired" or state == "blocked":
        message = settings_obj.expired_message
    else:
        message = ""

    return {
        "settings": settings_obj,
        "status_obj": status,
        "state": state,
        "due_at": due_at,
        "due_date": due_date,
        "days_to_due": warning_days,
        "grace_days": grace_days,
        "grace_end": grace_end,
        "online_allowed": online_allowed,
        "restricted": restricted,
        "message": message,
        "popup_title": settings_obj.due_date_popup_title,
        "popup_message": settings_obj.due_date_popup_message,
        "latest_payment": latest_payment,
        "latest_otp": latest_otp,
        "centre_name": _centre_name(centre),
        "centre_id": centre.formatted_id,
    }


def annual_kyc_access_restricted(centre, *, now=None):
    """Return True only for annual KYC restrictions, independent of reactivation flags."""

    if not centre or not centre.is_active:
        return False
    return annual_kyc_snapshot(centre, now=now)["restricted"]


def record_annual_kyc_access_restricted(centre, *, actor=None, snapshot=None):
    snapshot = snapshot or annual_kyc_snapshot(centre)
    return _audit(
        centre,
        CentreAnnualKYCAuditLog.Event.ACCESS_RESTRICTED,
        actor=actor,
        details={"state": snapshot["state"]},
    )


def calculate_annual_kyc_amount(centre, settings_obj=None):
    settings_obj = settings_obj or get_annual_kyc_settings()
    status = ensure_annual_kyc_status(centre, settings_obj=settings_obj)
    override = status.fee_override
    if override is not None and override > Decimal("0.00"):
        return override.quantize(Decimal("0.01"))
    return settings_obj.default_amount.quantize(Decimal("0.01"))


def _audit(centre, event, *, actor=None, details=None):
    return CentreAnnualKYCAuditLog.objects.create(
        centre=centre,
        actor=actor,
        event=event,
        details=details or {},
    )


def audit_global(event, *, actor=None, details=None):
    return CentreAnnualKYCAuditLog.objects.create(
        actor=actor,
        event=event,
        details=details or {},
    )


def annual_kyc_whatsapp_url(centre, settings_obj=None):
    settings_obj = settings_obj or get_annual_kyc_settings()
    number = settings_obj.whatsapp_support_number
    if not number:
        state = resolve_user_state(getattr(centre, "user", None)) if centre.user_id else None
        number = state.whatsapp_number if state and state.whatsapp_enabled else ""
        number = number or getattr(settings, "SUPPORT_WHATSAPP_NUMBER", "")
    try:
        number = normalize_whatsapp_number(number)
    except ValidationError:
        return ""
    if not number:
        return ""
    status = ensure_annual_kyc_status(centre, settings_obj=settings_obj)
    message = _format_message(
        settings_obj.whatsapp_message_template,
        centre=centre,
        due_at=effective_due_at(status),
    )
    return f"https://wa.me/{number}?{urlencode({'text': message})}"


def _razorpay_client():
    import razorpay

    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_annual_kyc_order(centre, *, actor=None):
    settings_obj = get_annual_kyc_settings()
    if not centre.is_active or centre.inactive_due_to_inactivity or centre.manual_disabled:
        raise ValueError("Complete centre reactivation before starting annual KYC renewal.")
    snapshot = annual_kyc_snapshot(centre, settings_obj=settings_obj)
    if not snapshot["online_allowed"]:
        raise ValueError("Online annual KYC payment is not available right now.")
    with transaction.atomic():
        centre = CentreUserAccount.objects.select_for_update().get(pk=centre.pk)
        if not centre.is_active or centre.inactive_due_to_inactivity or centre.manual_disabled:
            raise ValueError("Complete centre reactivation before starting annual KYC renewal.")
        status = ensure_annual_kyc_status(centre, settings_obj=settings_obj)
        snapshot = annual_kyc_snapshot(centre, settings_obj=settings_obj)
        if not snapshot["online_allowed"]:
            raise ValueError("Online annual KYC payment is not available right now.")
        amount = calculate_annual_kyc_amount(centre, settings_obj)
        pending = (
            CentreAnnualKYCPayment.objects.filter(
                centre=centre,
                status__in=(
                    CentreAnnualKYCPayment.Status.CREATED,
                    CentreAnnualKYCPayment.Status.PENDING,
                ),
                created_at__gte=timezone.now() - timedelta(minutes=30),
            )
            .order_by("-created_at", "-pk")
            .first()
        )
        if pending:
            return pending
        try:
            order = _razorpay_client().order.create(
                data={
                    "amount": int(amount * Decimal("100")),
                    "currency": "INR",
                    "payment_capture": 1,
                    "receipt": f"annual-kyc-{centre.pk}-{secrets.token_hex(6)}",
                }
            )
        except Exception as exc:
            logger.exception("Annual KYC Razorpay order creation failed for centre %s", centre.pk)
            raise RuntimeError("Unable to start payment right now.") from exc
        payment = CentreAnnualKYCPayment.objects.create(
            centre=centre,
            amount=amount,
            currency="INR",
            status=CentreAnnualKYCPayment.Status.CREATED,
            razorpay_order_id=order["id"],
        )
        _audit(
            centre,
            CentreAnnualKYCAuditLog.Event.PAYMENT_INITIATED,
            actor=actor,
            details={"order_id": payment.razorpay_order_id, "amount": str(amount)},
        )
        return payment


def set_annual_payment_status(
    payment,
    status,
    *,
    payment_id_value="",
    signature="",
    failure_code="",
    failure_description="",
    actor=None,
):
    allowed = {
        CentreAnnualKYCPayment.Status.PENDING,
        CentreAnnualKYCPayment.Status.FAILED,
        CentreAnnualKYCPayment.Status.CANCELLED,
    }
    if status not in allowed:
        raise ValueError("Unsupported annual KYC payment status")
    with transaction.atomic():
        payment = CentreAnnualKYCPayment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == CentreAnnualKYCPayment.Status.SUCCESS:
            return payment
        payment.status = status
        if payment_id_value:
            payment.razorpay_payment_id = payment_id_value
        if signature:
            payment.razorpay_signature = signature
        payment.failure_code = str(failure_code)[:100]
        payment.failure_description = str(failure_description)
        payment.save(
            update_fields=(
                "status",
                "razorpay_payment_id",
                "razorpay_signature",
                "failure_code",
                "failure_description",
                "updated_at",
            )
        )
        event = (
            CentreAnnualKYCAuditLog.Event.PAYMENT_FAILED
            if status == CentreAnnualKYCPayment.Status.FAILED
            else CentreAnnualKYCAuditLog.Event.PAYMENT_INITIATED
        )
        _audit(payment.centre, event, actor=actor, details={"status": status})
        return payment


def _send_annual_kyc_sms(centre, code):
    """Send through the configured provider; no plaintext code is persisted."""

    message = f"Your annual KYC verification OTP is {code}. It expires shortly."
    backend_path = getattr(settings, "ANNUAL_KYC_SMS_BACKEND", "")
    if backend_path:
        backend = import_string(backend_path)
        return bool(backend(str(centre.mobile), message, centre=centre))

    api_url = getattr(settings, "ANNUAL_KYC_SMS_API_URL", "")
    api_key = getattr(settings, "ANNUAL_KYC_SMS_API_KEY", "")
    if not api_url or not api_key:
        logger.warning("Annual KYC SMS provider is not configured")
        return False
    try:
        response = requests.post(
            api_url,
            json={
                "api_key": api_key,
                "sender": getattr(settings, "ANNUAL_KYC_SMS_SENDER_ID", "SSCEGV"),
                "to": str(centre.mobile),
                "message": message,
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Annual KYC SMS delivery failed for centre %s", centre.pk)
        return False


def _issue_otp(payment, *, actor=None, force=False, ip_address=None):
    settings_obj = get_annual_kyc_settings()
    now = timezone.now()
    with transaction.atomic():
        payment = CentreAnnualKYCPayment.objects.select_for_update().select_related("centre").get(pk=payment.pk)
        existing = payment.otp_verifications.order_by("-sent_at", "-pk").first()
        if (
            existing
            and not force
            and existing.status == CentreAnnualKYCOTPVerification.Status.SENT
            and existing.expires_at > now
        ):
            return existing, False
        code = f"{secrets.randbelow(1_000_000):06d}"
        otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=payment.centre,
            payment=payment,
            otp_hash=make_password(code),
            status=CentreAnnualKYCOTPVerification.Status.SENT,
            expires_at=now + timedelta(minutes=settings_obj.otp_expiry_minutes),
            resend_available_at=now + timedelta(seconds=settings_obj.otp_resend_cooldown_seconds),
            last_ip=ip_address,
        )
    delivered = _send_annual_kyc_sms(payment.centre, code)
    if not delivered:
        otp.status = CentreAnnualKYCOTPVerification.Status.SEND_FAILED
        otp.failure_reason = "sms_delivery_failed"
        otp.save(update_fields=("status", "failure_reason", "updated_at"))
        return otp, True
    _audit(
        payment.centre,
        CentreAnnualKYCAuditLog.Event.OTP_RESENT
        if existing is not None
        else CentreAnnualKYCAuditLog.Event.OTP_SENT,
        actor=actor,
        details={"payment_id": payment.pk},
    )
    return otp, True


def complete_annual_kyc_payment(
    payment_id,
    *,
    payment_id_value,
    signature,
    actor=None,
    ip_address=None,
):
    now = timezone.now()
    with transaction.atomic():
        payment = (
            CentreAnnualKYCPayment.objects.select_for_update()
            .select_related("centre")
            .get(pk=payment_id)
        )
        if payment.status == CentreAnnualKYCPayment.Status.SUCCESS:
            otp = payment.otp_verifications.order_by("-sent_at", "-pk").first()
            return payment, otp, "already_success"
        payment.status = CentreAnnualKYCPayment.Status.SUCCESS
        payment.razorpay_payment_id = payment_id_value or payment.razorpay_payment_id
        payment.razorpay_signature = signature or payment.razorpay_signature
        payment.paid_at = payment.paid_at or now
        payment.failure_code = ""
        payment.failure_description = ""
        payment.save(
            update_fields=(
                "status",
                "razorpay_payment_id",
                "razorpay_signature",
                "paid_at",
                "failure_code",
                "failure_description",
                "updated_at",
            )
        )
        _audit(
            payment.centre,
            CentreAnnualKYCAuditLog.Event.PAYMENT_VERIFIED,
            actor=actor,
            details={"payment_id": payment.razorpay_payment_id, "order_id": payment.razorpay_order_id},
        )
    otp, _ = _issue_otp(payment, actor=actor, ip_address=ip_address)
    return payment, otp, "verified"


def resend_annual_kyc_otp(payment, *, actor=None, ip_address=None):
    otp = payment.otp_verifications.order_by("-sent_at", "-pk").first()
    now = timezone.now()
    if not otp or payment.status != CentreAnnualKYCPayment.Status.SUCCESS:
        raise ValueError("Complete payment before requesting an OTP.")
    if otp.status == CentreAnnualKYCOTPVerification.Status.VERIFIED:
        raise ValueError("This OTP has already been verified.")
    if otp.resend_available_at > now and otp.status != CentreAnnualKYCOTPVerification.Status.SEND_FAILED:
        seconds = max(1, int((otp.resend_available_at - now).total_seconds()))
        raise ValueError(f"Please wait {seconds} seconds before requesting another OTP.")
    return _issue_otp(payment, actor=actor, force=True, ip_address=ip_address)


def verify_annual_kyc_otp(payment, code, *, actor=None, ip_address=None):
    settings_obj = get_annual_kyc_settings()
    now = timezone.now()
    code = str(code or "").strip()
    error_message = None
    already_verified = False
    with transaction.atomic():
        otp = (
            CentreAnnualKYCOTPVerification.objects.select_for_update()
            .select_related("payment", "centre")
            .filter(payment=payment, payment__status=CentreAnnualKYCPayment.Status.SUCCESS)
            .order_by("-sent_at", "-pk")
            .first()
        )
        if not otp:
            error_message = "Complete payment before entering the OTP."
        elif otp.status == CentreAnnualKYCOTPVerification.Status.VERIFIED:
            already_verified = True
        elif otp.expires_at <= now:
            otp.status = CentreAnnualKYCOTPVerification.Status.EXPIRED
            otp.failure_reason = "expired"
            otp.save(update_fields=("status", "failure_reason", "updated_at"))
            _audit(otp.centre, CentreAnnualKYCAuditLog.Event.OTP_EXPIRED, actor=actor)
            error_message = "This OTP has expired. Request a new OTP."
        elif otp.attempt_count >= settings_obj.max_otp_verification_attempts:
            otp.status = CentreAnnualKYCOTPVerification.Status.FAILED
            otp.failure_reason = "maximum_attempts"
            otp.save(update_fields=("status", "failure_reason", "updated_at"))
            error_message = "Maximum OTP attempts reached. Request a new OTP."
        else:
            otp.attempt_count += 1
            otp.last_attempt_at = now
            otp.last_ip = ip_address
            if not check_password(code, otp.otp_hash):
                if otp.attempt_count >= settings_obj.max_otp_verification_attempts:
                    otp.status = CentreAnnualKYCOTPVerification.Status.FAILED
                    otp.failure_reason = "maximum_attempts"
                otp.save(update_fields=("attempt_count", "last_attempt_at", "last_ip", "status", "failure_reason", "updated_at"))
                _audit(
                    otp.centre,
                    CentreAnnualKYCAuditLog.Event.OTP_FAILED,
                    actor=actor,
                    details={"attempt": otp.attempt_count},
                )
                error_message = "The OTP is incorrect."
            else:
                otp.status = CentreAnnualKYCOTPVerification.Status.VERIFIED
                otp.verified_at = now
                otp.save(update_fields=("attempt_count", "last_attempt_at", "last_ip", "status", "verified_at", "updated_at"))
                status = ensure_annual_kyc_status(otp.centre, settings_obj=settings_obj)
                status.last_kyc_verified_at = now
                status.next_kyc_due_at = add_months(now, settings_obj.renewal_interval_months)
                status.manual_due_date = None
                status.save(update_fields=("last_kyc_verified_at", "next_kyc_due_at", "manual_due_date", "updated_at"))
                _audit(otp.centre, CentreAnnualKYCAuditLog.Event.OTP_VERIFIED, actor=actor)
                _audit(
                    otp.centre,
                    CentreAnnualKYCAuditLog.Event.KYC_COMPLETED,
                    actor=actor,
                    details={"payment_id": payment.pk, "verified_at": now.isoformat()},
                )
    if error_message:
        raise ValueError(error_message)
    return otp, True


def manual_mark_annual_kyc_verified(centre, *, actor, reason):
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("A reason is required for manual verification.")
    now = timezone.now()
    settings_obj = get_annual_kyc_settings()
    with transaction.atomic():
        status = ensure_annual_kyc_status(centre, settings_obj=settings_obj)
        status = CentreAnnualKYCStatus.objects.select_for_update().get(pk=status.pk)
        status.last_kyc_verified_at = now
        status.next_kyc_due_at = add_months(now, settings_obj.renewal_interval_months)
        status.manual_due_date = None
        status.save(update_fields=("last_kyc_verified_at", "next_kyc_due_at", "manual_due_date", "updated_at"))
        _audit(centre, CentreAnnualKYCAuditLog.Event.MANUAL_VERIFIED, actor=actor, details={"reason": reason})
    return status


def set_annual_kyc_manual_block(centre, *, actor, blocked, reason=""):
    reason = str(reason or "").strip()
    if blocked and not reason:
        raise ValueError("A reason is required when manually blocking a centre.")
    status = ensure_annual_kyc_status(centre)
    status.manual_blocked = bool(blocked)
    status.manual_block_reason = reason if blocked else ""
    status.save(update_fields=("manual_blocked", "manual_block_reason", "updated_at"))
    _audit(
        centre,
        CentreAnnualKYCAuditLog.Event.MANUAL_BLOCKED
        if blocked
        else CentreAnnualKYCAuditLog.Event.MANUAL_UNBLOCKED,
        actor=actor,
        details={"reason": reason},
    )
    return status
