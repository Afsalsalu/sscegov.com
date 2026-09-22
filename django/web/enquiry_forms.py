from pathlib import Path
import zipfile

from django import forms


MAX_ENQUIRY_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_ENQUIRY_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}


class FranchiseEnquiryForm(forms.Form):
    subject = forms.CharField(
        max_length=200,
        label="Subject",
        widget=forms.TextInput(
            attrs={"placeholder": "What do you need help with?", "autocomplete": "off"}
        ),
    )
    message = forms.CharField(
        max_length=10000,
        label="Message",
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": "Share the details so our Head Office team can help.",
            }
        ),
    )
    attachment = forms.FileField(
        label="Attachment",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png"}),
        help_text="Optional. PDF, DOC, DOCX, JPG, JPEG, or PNG. Maximum 10 MB.",
    )

    def clean_attachment(self):
        uploaded = self.cleaned_data.get("attachment")
        if not uploaded:
            return uploaded

        extension = Path(uploaded.name).suffix.lower()
        if extension not in ALLOWED_ENQUIRY_EXTENSIONS:
            raise forms.ValidationError(
                "Choose a PDF, DOC, DOCX, JPG, JPEG, or PNG file."
            )
        if uploaded.size > MAX_ENQUIRY_ATTACHMENT_SIZE:
            raise forms.ValidationError("The attachment must be 10 MB or smaller.")

        try:
            uploaded.seek(0)
            header = uploaded.read(8)
            uploaded.seek(0)

            if extension == ".pdf":
                valid_content = header.startswith(b"%PDF-")
            elif extension in {".jpg", ".jpeg"}:
                valid_content = header.startswith(b"\xff\xd8\xff")
            elif extension == ".png":
                valid_content = header.startswith(b"\x89PNG\r\n\x1a\n")
            elif extension == ".doc":
                valid_content = header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
            else:
                valid_content = False
                try:
                    with zipfile.ZipFile(uploaded) as document:
                        names = set(document.namelist())
                    valid_content = {
                        "[Content_Types].xml",
                        "word/document.xml",
                    }.issubset(names)
                except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
                    valid_content = False
        finally:
            uploaded.seek(0)

        if not valid_content:
            raise forms.ValidationError(
                "The file contents do not match the selected document or image type."
            )
        return uploaded


class FranchiseEnquiryReplyForm(forms.Form):
    reply = forms.CharField(
        label="Reply",
        required=False,
        max_length=10000,
        widget=forms.Textarea(
            attrs={"rows": 7, "placeholder": "Write a clear reply for the franchise."}
        ),
    )
    status = forms.ChoiceField(
        label="Update status",
        required=False,
        choices=(
            ("", "Keep current status"),
            ("replied", "Replied"),
            ("closed", "Closed"),
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("reply") and not cleaned_data.get("status"):
            raise forms.ValidationError("Write a reply or choose a status update.")
        return cleaned_data
