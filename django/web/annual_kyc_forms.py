from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import AnnualKYCSettings, CentreAnnualKYCStatus
from .whatsapp_utils import normalize_whatsapp_number


class AnnualKYCSettingsForm(forms.ModelForm):
    class Meta:
        model = AnnualKYCSettings
        fields = (
            "enabled",
            "renewal_interval_months",
            "warning_period_days",
            "grace_period_days",
            "default_amount",
            "otp_expiry_minutes",
            "otp_resend_cooldown_seconds",
            "max_otp_verification_attempts",
            "dashboard_warning_text",
            "due_date_popup_title",
            "due_date_popup_message",
            "grace_period_warning_text",
            "expired_message",
            "payment_enabled",
            "whatsapp_support_number",
            "whatsapp_message_template",
        )
        widgets = {
            "renewal_interval_months": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "warning_period_days": forms.NumberInput(attrs={"min": 0, "step": 1}),
            "grace_period_days": forms.NumberInput(attrs={"min": 0, "step": 1}),
            "default_amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "otp_expiry_minutes": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "otp_resend_cooldown_seconds": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "max_otp_verification_attempts": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "dashboard_warning_text": forms.Textarea(attrs={"rows": 2}),
            "due_date_popup_message": forms.Textarea(attrs={"rows": 3}),
            "grace_period_warning_text": forms.Textarea(attrs={"rows": 2}),
            "expired_message": forms.Textarea(attrs={"rows": 3}),
            "whatsapp_message_template": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_default_amount(self):
        value = self.cleaned_data["default_amount"]
        if value <= Decimal("0.00"):
            raise forms.ValidationError("The annual KYC amount must be greater than zero.")
        return value

    def clean_whatsapp_support_number(self):
        value = self.cleaned_data.get("whatsapp_support_number", "").strip()
        if not value:
            return ""
        try:
            return normalize_whatsapp_number(value)
        except ValidationError as exc:
            raise forms.ValidationError(str(exc)) from exc


class AnnualKYCCentreControlForm(forms.ModelForm):
    manual_verify_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Required only when using the manual verification action.",
    )

    class Meta:
        model = CentreAnnualKYCStatus
        fields = (
            "fee_override",
            "manual_due_date",
            "manual_blocked",
            "manual_block_reason",
        )
        widgets = {
            "fee_override": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "manual_due_date": forms.DateInput(attrs={"type": "date"}),
            "manual_block_reason": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("manual_blocked") and not (cleaned.get("manual_block_reason") or "").strip():
            self.add_error("manual_block_reason", "A reason is required when manually blocking a centre.")
        if cleaned.get("fee_override") is not None and cleaned["fee_override"] <= Decimal("0.00"):
            self.add_error("fee_override", "The fee override must be greater than zero.")
        return cleaned
