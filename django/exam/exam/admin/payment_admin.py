# exam/admin/payment_admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from exam.constants import PaymentStatus
from exam.models.payment import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user_registration_link",
        "amount",
        "status",
        "provider_order_id",
        "payment_id",
        "signature_id",
        "is_certificate_payment",
    )
    readonly_fields = (
        "user_registration_link",
        "provider_order_id",
        "payment_id",
        "signature_id",
    )

    list_filter = (
        "status",
        "is_certificate_payment",
        "user_registration__state",
        "user_registration__district",
    )

    search_fields = (
        "user_registration__name",
        "user_registration__mobile",
        "provider_order_id",
        "payment_id",
        "signature_id",
    )

    # Use a different field for ordering if created_at does not exist
    ordering = ("-id",)  # Ordering by ID or any other available field

    fieldsets = (
        (
            "Payment Information",
            {
                "fields": (
                    "user_registration",
                    "amount",
                    "status",
                    "provider_order_id",
                    "payment_id",
                    "signature_id",
                    "is_certificate_payment",
                )
            },
        ),
    )

    # Custom display for user registration link
    def user_registration_link(self, obj):
        if obj.user_registration:
            url = reverse(
                "admin:exam_userregistration_change", args=[obj.user_registration.id]
            )
            return format_html('<a href="{}">{}</a>', url, obj.user_registration.name)
        return "-"

    user_registration_link.short_description = "User Registration"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["user_registration"].disabled = True
        return form

    # Custom actions
    actions = ["mark_as_successful", "mark_as_failed"]

    def mark_as_successful(self, request, queryset):
        queryset.update(status=PaymentStatus.SUCCESS)

    mark_as_successful.short_description = "Mark selected payments as Successful"

    def mark_as_failed(self, request, queryset):
        queryset.update(status=PaymentStatus.FAILED)

    mark_as_failed.short_description = "Mark selected payments as Failed"
