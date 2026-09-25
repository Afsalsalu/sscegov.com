from django import forms
from decimal import Decimal

from .models import CentreReactivationSettings


class CentreReactivationSettingsForm(forms.ModelForm):
    class Meta:
        model = CentreReactivationSettings
        fields = (
            "inactivity_days",
            "default_amount",
            "payment_enabled",
            "admin_message",
        )
        widgets = {
            "inactivity_days": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "default_amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "admin_message": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_inactivity_days(self):
        value = self.cleaned_data["inactivity_days"]
        if value < 1:
            raise forms.ValidationError("The inactivity period must be at least 1 day.")
        return value

    def clean_default_amount(self):
        value = self.cleaned_data["default_amount"]
        if value <= 0:
            raise forms.ValidationError("The reactivation amount must be greater than zero.")
        return value


class CentreManualDisableForm(forms.Form):
    disable_reason = forms.CharField(
        label="Disable reason / message",
        required=True,
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Explain why this centre is being disabled."}),
    )
    payment_required = forms.BooleanField(
        label="Show payment option?",
        required=False,
        initial=False,
        help_text="When selected, the centre will see the configured reactivation amount.",
    )
    amount_override = forms.DecimalField(
        label="Per-centre amount override (INR)",
        required=False,
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        help_text="Leave blank to use the configured default amount.",
    )

    def clean_disable_reason(self):
        value = self.cleaned_data["disable_reason"].strip()
        if not value:
            raise forms.ValidationError("A disable reason / message is required.")
        return value

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("payment_required"):
            cleaned["amount_override"] = None
        return cleaned
