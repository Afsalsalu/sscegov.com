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
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
        }

    service_logo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/jpeg,image/png,image/webp"}
        ),
    )

    def clean_service_logo(self):
        file_key = self.add_prefix("service_logo")
        if hasattr(self.files, "getlist"):
            uploaded_logos = self.files.getlist(file_key)
        else:
            uploaded_logos = self.files.get(file_key)
            if uploaded_logos is None:
                uploaded_logos = []
            elif not isinstance(uploaded_logos, (list, tuple)):
                uploaded_logos = [uploaded_logos]
        if len(uploaded_logos) > 1:
            raise forms.ValidationError("Upload only one service logo.")
        logo = self.cleaned_data.get("service_logo")
        if not logo:
            clear_logo = self.data.get(f"{self.add_prefix('service_logo')}-clear")
            if clear_logo in {"on", "true", "1"}:
                return False
            if self.instance.pk:
                return self.instance.service_logo
            return logo
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
