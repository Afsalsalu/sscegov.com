from django import forms
from django.core.exceptions import ValidationError

from .models import AddState
from .whatsapp_utils import normalize_whatsapp_number


class WhatsAppSupportForm(forms.ModelForm):
    whatsapp_number = forms.CharField(required=False, max_length=32)

    class Meta:
        model = AddState
        fields = ("whatsapp_number", "whatsapp_enabled")
        widgets = {
            "whatsapp_number": forms.TextInput(
                attrs={
                    "placeholder": "919876543210",
                    "inputmode": "tel",
                    "autocomplete": "tel",
                }
            ),
        }

    def clean_whatsapp_number(self):
        value = self.cleaned_data.get("whatsapp_number")
        try:
            return normalize_whatsapp_number(value)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc
