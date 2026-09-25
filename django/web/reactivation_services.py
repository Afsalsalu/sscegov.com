from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    CentreReactivationAuditLog,
    CentreReactivationPayment,
    CentreReactivationSettings,
    CentreUserAccount,
)


INACTIVITY_REASON = "inactive_due_to_inactivity"
ACTIVE_PAYMENT_STATUSES = {
    CentreReactivationPayment.Status.CREATED,
    CentreReactivationPayment.Status.PENDING,
    CentreReactivationPayment.Status.AUTHORIZED,
}


def get_reactivation_settings():
    return CentreReactivationSettings.get_solo()


def centre_activity_reference(centre):
    """Return the last real centre activity, falling back to account creation."""

    user = getattr(centre, "user", None)
    return (
        centre.last_successful_login
        or centre.last_login
        or getattr(user, "last_login", None)
        or centre.created_at
        or getattr(user, "date_joined", None)
    )


def inactivity_cutoff(now=None, settings_obj=None):
    now = now or timezone.now()
    settings_obj = settings_obj or get_reactivation_settings()
    return now - timedelta(days=max(1, settings_obj.inactivity_days))


def _audit(centre, event, actor=None, details=None):
    return CentreReactivationAuditLog.objects.create(
        centre=centre,
        actor=actor,
        event=event,
        details=details or {},
    )


def mark_centre_inactive_if_due(centre_id, *, now=None, actor=None):
    """Atomically disable one eligible centre when its activity is overdue."""

    now = now or timezone.now()
    settings_obj = get_reactivation_settings()
    with transaction.atomic():
        centre = (
            CentreUserAccount.objects.select_for_update()
            .select_related("user")
            .get(pk=centre_id)
        )
        if (
            not centre.is_active
            or centre.manual_disabled
            or centre.inactive_due_to_inactivity
            or not centre.user
            or centre.user.usertype != "centre"
        ):
            return False

        activity = centre_activity_reference(centre)
        if not activity or activity > inactivity_cutoff(now, settings_obj):
            return False

        centre.is_active = False
        centre.inactive_due_to_inactivity = True
        centre.inactivity_disabled_at = now
        centre.inactivity_reason = INACTIVITY_REASON
        centre.reactivated_at = None
        centre.save(
            update_fields=(
                "is_active",
                "inactive_due_to_inactivity",
                "inactivity_disabled_at",
                "inactivity_reason",
                "reactivated_at",
            )
        )
        _audit(
            centre,
            CentreReactivationAuditLog.Event.INACTIVITY_DISABLED,
            actor=actor,
            details={
                "reason": INACTIVITY_REASON,
                "activity_reference": activity.isoformat(),
                "inactivity_days": settings_obj.inactivity_days,
            },
        )
        return True


def mark_inactive_centres(*, now=None):
    """Mark every currently active centre overdue for inactivity."""

    centre_ids = CentreUserAccount.objects.filter(
        is_active=True,
        manual_disabled=False,
        inactive_due_to_inactivity=False,
        user__usertype="centre",
    ).values_list("pk", flat=True)
    marked = 0
    for centre_id in centre_ids.iterator():
        if mark_centre_inactive_if_due(centre_id, now=now):
            marked += 1
    return marked


def calculate_reactivation_amount(centre, settings_obj=None):
    settings_obj = settings_obj or get_reactivation_settings()
    override = (
        centre.manual_reactivation_fee_override
        if centre.manual_disabled
        else centre.reactivation_fee_override
    )
    if override is not None and override > Decimal("0.00"):
        return override.quantize(Decimal("0.01"))
    return settings_obj.default_amount.quantize(Decimal("0.01"))


def centre_reactivation_message(centre, settings_obj=None):
    settings_obj = settings_obj or get_reactivation_settings()
    if centre.manual_disabled and centre.manual_disable_reason:
        return centre.manual_disable_reason
    return settings_obj.admin_message


def centre_payment_available(centre, settings_obj=None):
    settings_obj = settings_obj or get_reactivation_settings()
    if not settings_obj.payment_enabled:
        return False
    if centre.manual_disabled:
        return centre.manual_reactivation_payment_required
    return centre.inactive_due_to_inactivity


def manually_disable_centre(
    centre_id,
    *,
    actor,
    reason,
    payment_required=False,
    fee_override=None,
    now=None,
):
    """Apply a Head Office manual restriction while keeping authentication possible."""

    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("A manual disable reason is required.")

    if payment_required and fee_override is not None:
        fee_override = Decimal(fee_override).quantize(Decimal("0.01"))
        if fee_override <= Decimal("0.00"):
            raise ValueError("The reactivation amount must be greater than zero.")
    else:
        fee_override = None

    now = now or timezone.now()
    with transaction.atomic():
        centre = (
            CentreUserAccount.objects.select_for_update()
            .select_related("user")
            .get(pk=centre_id)
        )
        if not centre.user or centre.user.usertype != "centre":
            raise ValueError("Only a linked centre account can be manually disabled.")

        centre.is_active = False
        centre.manual_disabled = True
        centre.manual_disabled_at = now
        centre.manual_disabled_by = actor
        centre.manual_disable_reason = reason
        centre.manual_reactivation_payment_required = bool(payment_required)
        centre.manual_reactivation_fee_override = fee_override
        # Manual restrictions take priority over a stale automatic restriction.
        centre.inactive_due_to_inactivity = False
        centre.inactivity_reason = ""
        centre.reactivated_at = None
        centre.save(
            update_fields=(
                "is_active",
                "manual_disabled",
                "manual_disabled_at",
                "manual_disabled_by",
                "manual_disable_reason",
                "manual_reactivation_payment_required",
                "manual_reactivation_fee_override",
                "inactive_due_to_inactivity",
                "inactivity_reason",
                "reactivated_at",
            )
        )

        # A restricted centre must still be able to authenticate and reach the
        # restricted workflow. The centre flag, not User.is_active, enforces access.
        if not centre.user.is_active:
            centre.user.is_active = True
            centre.user.save(update_fields=("is_active",))

        _audit(
            centre,
            CentreReactivationAuditLog.Event.MANUAL_DISABLED,
            actor=actor,
            details={
                "reason": reason,
                "payment_required": bool(payment_required),
                "amount_override": str(fee_override) if fee_override is not None else "",
            },
        )
        return centre


def manually_enable_centre(centre_id, *, actor, now=None):
    """Remove the active restriction and preserve all prior audit metadata."""

    now = now or timezone.now()
    with transaction.atomic():
        centre = (
            CentreUserAccount.objects.select_for_update()
            .select_related("user")
            .get(pk=centre_id)
        )
        centre.is_active = True
        centre.manual_disabled = False
        centre.inactive_due_to_inactivity = False
        centre.inactivity_reason = ""
        centre.reactivated_at = now
        centre.last_successful_login = now
        centre.last_login = now
        centre.save(
            update_fields=(
                "is_active",
                "manual_disabled",
                "inactive_due_to_inactivity",
                "inactivity_reason",
                "reactivated_at",
                "last_successful_login",
                "last_login",
            )
        )
        if centre.user_id:
            centre.user.is_active = True
            centre.user.last_login = now
            centre.user.save(update_fields=("is_active", "last_login"))
        _audit(
            centre,
            CentreReactivationAuditLog.Event.MANUAL_ENABLED,
            actor=actor,
            details={"source": "head_office_manual_enable"},
        )
        return centre


def complete_reactivation_payment(payment_id, *, payment_id_value, signature, actor=None):
    """Capture a verified payment and only auto-enable inactivity restrictions."""

    now = timezone.now()
    with transaction.atomic():
        payment = CentreReactivationPayment.objects.select_for_update().get(pk=payment_id)
        centre = CentreUserAccount.objects.select_for_update().get(pk=payment.centre_id)

        if payment.status == CentreReactivationPayment.Status.CAPTURED:
            return payment, "already_captured"
        if payment.status == CentreReactivationPayment.Status.MANUAL_REVIEW:
            return payment, "manual_review"

        payment.razorpay_payment_id = payment_id_value or payment.razorpay_payment_id
        payment.razorpay_signature = signature or payment.razorpay_signature
        payment.status = CentreReactivationPayment.Status.CAPTURED
        payment.paid_at = payment.paid_at or now
        payment.failure_code = ""
        payment.failure_description = ""

        if centre.manual_disabled:
            payment.save(
                update_fields=(
                    "razorpay_payment_id",
                    "razorpay_signature",
                    "status",
                    "paid_at",
                    "failure_code",
                    "failure_description",
                    "updated_at",
                )
            )
            _audit(
                centre,
                CentreReactivationAuditLog.Event.PAYMENT_SUCCESS,
                actor=actor,
                details={
                    "payment_id": payment.razorpay_payment_id,
                    "order_id": payment.razorpay_order_id,
                    "amount": str(payment.amount),
                    "requires_manual_enable": True,
                },
            )
            _audit(
                centre,
                CentreReactivationAuditLog.Event.MANUAL_REVIEW,
                actor=actor,
                details={
                    "payment_id": payment.razorpay_payment_id,
                    "reason": "manual_disable_requires_head_office_enable",
                },
            )
            return payment, "manual_review"

        if not centre.inactive_due_to_inactivity:
            payment.save(
                update_fields=(
                    "razorpay_payment_id",
                    "razorpay_signature",
                    "status",
                    "paid_at",
                    "failure_code",
                    "failure_description",
                    "updated_at",
                )
            )
            _audit(
                centre,
                CentreReactivationAuditLog.Event.MANUAL_REVIEW,
                actor=actor,
                details={
                    "payment_id": payment.razorpay_payment_id,
                    "reason": "centre_not_restricted_by_inactivity",
                },
            )
            return payment, "manual_review"

        centre.is_active = True
        centre.manual_disabled = False
        centre.inactive_due_to_inactivity = False
        centre.inactivity_reason = ""
        centre.reactivated_at = now
        centre.last_successful_login = now
        centre.last_login = now
        centre.save(
            update_fields=(
                "is_active",
                "manual_disabled",
                "inactive_due_to_inactivity",
                "inactivity_reason",
                "reactivated_at",
                "last_successful_login",
                "last_login",
            )
        )
        if centre.user_id:
            centre.user.last_login = now
            centre.user.save(update_fields=["last_login"])
        payment.save(
            update_fields=(
                "razorpay_payment_id",
                "razorpay_signature",
                "status",
                "paid_at",
                "failure_code",
                "failure_description",
                "updated_at",
            )
        )
        _audit(
            centre,
            CentreReactivationAuditLog.Event.PAYMENT_SUCCESS,
            actor=actor,
            details={
                "payment_id": payment.razorpay_payment_id,
                "order_id": payment.razorpay_order_id,
                "amount": str(payment.amount),
            },
        )
        _audit(
            centre,
            CentreReactivationAuditLog.Event.REACTIVATED,
            actor=actor,
            details={"payment_id": payment.razorpay_payment_id},
        )
        return payment, "reactivated"


def set_payment_status(payment, status, *, payment_id_value="", failure_code="", failure_description="", actor=None):
    if status not in {
        CentreReactivationPayment.Status.PENDING,
        CentreReactivationPayment.Status.FAILED,
        CentreReactivationPayment.Status.CANCELLED,
    }:
        raise ValueError("Unsupported client payment status")

    with transaction.atomic():
        payment = CentreReactivationPayment.objects.select_for_update().get(pk=payment.pk)
        if payment.status in {
            CentreReactivationPayment.Status.CAPTURED,
            CentreReactivationPayment.Status.MANUAL_REVIEW,
        }:
            return payment
        payment.status = status
        if payment_id_value:
            payment.razorpay_payment_id = payment_id_value
        payment.failure_code = failure_code[:100]
        payment.failure_description = failure_description
        payment.save(
            update_fields=(
                "status",
                "razorpay_payment_id",
                "failure_code",
                "failure_description",
                "updated_at",
            )
        )
        event = {
            CentreReactivationPayment.Status.PENDING: CentreReactivationAuditLog.Event.PAYMENT_PENDING,
            CentreReactivationPayment.Status.FAILED: CentreReactivationAuditLog.Event.PAYMENT_FAILED,
            CentreReactivationPayment.Status.CANCELLED: CentreReactivationAuditLog.Event.PAYMENT_CANCELLED,
        }[status]
        _audit(
            payment.centre,
            event,
            actor=actor,
            details={"order_id": payment.razorpay_order_id, "status": status},
        )
        return payment
