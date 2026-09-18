from pathlib import Path

from django import forms
from PIL import Image

from .models import Banner


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ["image", "display_order", "is_enabled"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            if self.instance.pk:
                return self.instance.image
            raise forms.ValidationError("Please select a banner image.")
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Banner images must be 5 MB or smaller.")
        allowed = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
        suffix = Path(image.name).suffix.lower()
        if suffix not in allowed:
            raise forms.ValidationError("Only JPG, JPEG, PNG, and WebP images are allowed.")
        try:
            with Image.open(image) as opened:
                if opened.format != allowed[suffix]:
                    raise forms.ValidationError("The file contents do not match its image type.")
                opened.verify()
        except (OSError, Image.DecompressionBombError):
            raise forms.ValidationError("Please upload a valid image file.")
        image.seek(0)
        return image
