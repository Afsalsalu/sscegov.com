from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from PIL import Image

from .models import StateService


DETAIL_IMAGE_MAX_BYTES = 5 * 1024 * 1024
DETAIL_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


class StateServiceForm(forms.ModelForm):
    class Meta:
        model = StateService
        fields = [
            "service_name",
            "service_link",
            "service_logo",
            "service_details",
            "is_active",
            "is_popular",
        ]
        widgets = {
            "service_details": forms.Textarea(
                attrs={"rows": 9, "placeholder": "Describe this service..."}
            ),
            "service_logo": forms.ClearableFileInput(
                attrs={"accept": ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"}
            ),
        }

    def clean_service_logo(self):
        logo = self.cleaned_data.get("service_logo")
        if not logo:
            if self.instance.pk:
                return self.instance.service_logo
            raise forms.ValidationError("Please select a service logo.")
        return validate_uploaded_image(logo, "Service logo")


def validate_uploaded_image(uploaded_file, label="Image"):
    if uploaded_file.size > DETAIL_IMAGE_MAX_BYTES:
        raise ValidationError(f"{label} must be 5 MB or smaller.")

    suffix = Path(uploaded_file.name).suffix.lower()
    expected_format = DETAIL_IMAGE_FORMATS.get(suffix)
    if not expected_format:
        raise ValidationError("Only JPG, JPEG, PNG, and WebP images are allowed.")

    try:
        with Image.open(uploaded_file) as image:
            if image.format != expected_format:
                raise ValidationError("The file contents do not match its image type.")
            image.verify()
    except ValidationError:
        raise
    except (OSError, Image.DecompressionBombError):
        raise ValidationError("Please upload a valid image file.")
    finally:
        uploaded_file.seek(0)

    return uploaded_file


def validate_detail_image(uploaded_file):
    return validate_uploaded_image(uploaded_file, "Detail images")
