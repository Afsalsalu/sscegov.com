from django import forms

from .models import UserRegistration


from django import forms
# exam/forms.py
from django import forms
from .models import UserRegistration




class UserRegistrationForm(forms.ModelForm):
    class Meta:
        model = UserRegistration
        fields = [
            "name",
            "mobile",
            "email",
            "another_name",
            "state",
            "district",
            "panchayat",
            "ward_number",
            "gender",
            "aadhaar_number",
            "cheque_passbook",
            "date_of_birth",
            "address",
            "photo",
        ]
        widgets = {
            "state": forms.Select(attrs={"class": "form-control"}),
            "district": forms.Select(attrs={"class": "form-control"}),
            "panchayat": forms.Select(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "mobile": forms.TextInput(attrs={"class": "form-control", "placeholder": "Mobile Number"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "another_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Parent/Spouse Name"}),
            "ward_number": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ward Number"}),
            "aadhaar_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Aadhaar Number"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Full Address"}),
            "cheque_passbook": forms.FileInput(attrs={"class": "form-control"}),
            "photo": forms.FileInput(attrs={"class": "form-control"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = False
        self.fields["cheque_passbook"].required = False

    def clean(self):
        cleaned_data = super().clean()
        mobile = cleaned_data.get("mobile")
        email = cleaned_data.get("email")
        aadhaar_number = cleaned_data.get("aadhaar_number")

        if UserRegistration.objects.filter(mobile=mobile).exists():
            self.add_error("mobile", "A user with this mobile number already exists.")

        if UserRegistration.objects.filter(email=email).exists():
            self.add_error("email", "A user with this email address already exists.")

        if UserRegistration.objects.filter(aadhaar_number=aadhaar_number).exists():
            self.add_error("aadhaar_number", "A user with this Aadhaar number already exists.")

        return cleaned_data

