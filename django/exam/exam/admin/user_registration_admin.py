# exam/admin/user_registration_admin.py
from django.contrib import admin
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html

from exam.models import UserRegistration


@admin.register(UserRegistration)
class UserRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "mobile",
        "email",
        "state",
        "district",
        "certificate_paid_status",
        "certificate_downloaded_status",
        "details_filled_status",
        "view_user_link",
        "registration_date",
    )

    readonly_fields = (
        "name",
        "mobile",
        "email",
        "state",
        "district",
        "certificate_paid",
        "certificate_downloaded",
        "details_filled",
        "registration_date",  # Ensure this is in readonly_fields
        "view_user_link",
    )

    # List filter
    list_filter = (
        "state",
        "district",
        "gender",
        "certificate_paid",
        "certificate_downloaded",
        "details_filled",
    )

    # Search fields
    search_fields = ("name", "mobile", "email", "state", "district")

    # Ordering
    ordering = ("-registration_date",)

    # Fieldsets for organizing fields
    fieldsets = (
        (
            "Personal Information",
            {
                "fields": (
                    "user",
                    "name",
                    "mobile",
                    "email",
                    "another_name",
                    "state",
                    "district",
                    "gender",
                    "date_of_birth",
                    "address",
                    "photo",
                )
            },
        ),
        (
            "Registration Details",
            {
                "fields": (
                    "registration_date",
                    "certificate_paid",
                    "certificate_downloaded",
                    "details_filled",
                ),
            },
        ),
    )

    # Custom actions
    actions = [
        "mark_certificate_paid",
        "mark_certificate_unpaid",
        "mark_details_filled",
        "mark_details_unfilled",
    ]

    def mark_certificate_paid(self, request, queryset):
        queryset.update(certificate_paid=True)

    mark_certificate_paid.short_description = "Mark selected registrations as Paid"

    def mark_certificate_unpaid(self, request, queryset):
        queryset.update(certificate_paid=False)

    mark_certificate_unpaid.short_description = "Mark selected registrations as Unpaid"

    def mark_details_filled(self, request, queryset):
        queryset.update(details_filled=True)

    mark_details_filled.short_description = (
        "Mark selected registrations as Details Filled"
    )

    def mark_details_unfilled(self, request, queryset):
        queryset.update(details_filled=False)

    mark_details_unfilled.short_description = (
        "Mark selected registrations as Details Unfilled"
    )

    # Custom display for certificate paid status
    def certificate_paid_status(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if obj.certificate_paid else "red",
            "Paid" if obj.certificate_paid else "Not Paid",
        )

    certificate_paid_status.short_description = "Certificate Paid Status"

    # Custom display for certificate downloaded status
    def certificate_downloaded_status(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if obj.certificate_downloaded else "red",
            "Downloaded" if obj.certificate_downloaded else "Not Downloaded",
        )

    certificate_downloaded_status.short_description = "Certificate Downloaded Status"

    # Custom display for details filled status
    def details_filled_status(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if obj.details_filled else "red",
            "Filled" if obj.details_filled else "Not Filled",
        )

    details_filled_status.short_description = "Details Filled Status"

    # Link to related user model
    def view_user_link(self, obj):
        if obj.user:
            try:
                url = reverse("admin:auth_user_change", args=[obj.user.id])
                return format_html('<a href="{}">{}</a>', url, obj.user.username)
            except NoReverseMatch:
                return format_html('<span style="color: red;">Link not found</span>')
        return "-"

    view_user_link.short_description = "User"

    # Customizing the admin form
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["user"].disabled = True
        return form
