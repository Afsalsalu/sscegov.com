import re
import os

from captcha.fields import CaptchaField
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import \
    PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.forms import DateInput
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import (AddState, CentreUserAccount, Department, DownloadForm,
                     Employee, HeadOffice, KeralaSubCentre, OnlineClass, State,
                     StateService, Table_Accountsmaster, Table_Companydetailsmaster)

User = get_user_model()


class DownloadFormForm(forms.ModelForm):
    class Meta:
        model = DownloadForm
        fields = ["title", "state", "service", "pdf"]
        widgets = {
            "state": forms.HiddenInput(),
            "service": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["state"].queryset = AddState.objects.order_by("state_name")
        state_id = None
        if self.is_bound:
            state_id = self.data.get("state")
        elif self.instance.pk:
            state_id = self.instance.state_id
        if state_id:
            self.fields["service"].queryset = StateService.objects.filter(
                state_id=state_id
            ).order_by("service_name")
        else:
            self.fields["service"].queryset = StateService.objects.order_by(
                "service_name"
            )

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get("state")
        service = cleaned_data.get("service")
        if state and service and service.state_id != state.pk:
            self.add_error(
                "service", "Select a service belonging to the selected state."
            )
        return cleaned_data


class OnlineClassForm(forms.ModelForm):
    MAX_VIDEO_SIZE = getattr(
        settings, "ONLINE_CLASS_MAX_VIDEO_SIZE", 100 * 1024 * 1024
    )
    ALLOWED_VIDEO_TYPES = {
        ".mp4": {"video/mp4", "application/mp4"},
        ".webm": {"video/webm"},
    }

    class Meta:
        model = OnlineClass
        fields = [
            "title",
            "class_video_link",
            "video_file",
            "thumbnail",
            "description",
        ]
        labels = {
            "class_video_link": "Class video link",
            "video_file": "Video upload",
            "thumbnail": "Thumbnail",
            "description": "Description",
        }
        widgets = {
            "class_video_link": forms.URLInput(
                attrs={"placeholder": "https://...", "autocomplete": "url"}
            ),
            "video_file": forms.ClearableFileInput(
                attrs={"accept": "video/mp4,video/webm"}
            ),
            "thumbnail": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Describe this class..."}
            ),
        }

    def clean_video_file(self):
        video = self.cleaned_data.get("video_file")
        if not video or not hasattr(video, "size"):
            return video
        if not hasattr(video, "content_type"):
            return video
        max_video_size = getattr(
            settings, "ONLINE_CLASS_MAX_VIDEO_SIZE", self.MAX_VIDEO_SIZE
        )
        if video.size > max_video_size:
            limit_mb = max_video_size // (1024 * 1024)
            raise ValidationError(
                f"Video upload must be {limit_mb} MB or smaller."
            )
        extension = os.path.splitext(video.name)[1].lower()
        allowed_types = self.ALLOWED_VIDEO_TYPES.get(extension)
        if not allowed_types:
            raise ValidationError("Upload an MP4 or WebM video file.")
        content_type = (getattr(video, "content_type", "") or "").lower()
        if content_type not in allowed_types:
            raise ValidationError(
                "The uploaded video content type does not match its file extension."
            )
        return video

    def clean(self):
        cleaned_data = super().clean()
        video = cleaned_data.get("video_file")
        link = cleaned_data.get("class_video_link")
        if not video and not link:
            raise forms.ValidationError(
                "Provide either a video upload or a class video link."
            )
        return cleaned_data


class CustomPasswordChangeForm(DjangoPasswordChangeForm):
    """
    A form that lets a user change their password by entering their old
    password and a new password.
    """

    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "autofocus": True}
        ),
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Enter a strong password that you have not used before."),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add customizations here if needed

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError(
                _("The two password fields didn't match."),
                code="password_mismatch",
            )
        return cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput)
    captcha = CaptchaField()


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label=_("Email"), max_length=254)


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name"]


class HeadOfficeForm(forms.ModelForm):
    class Meta:
        model = HeadOffice
        fields = ["name", "photo", "phone_number", "email"]


class EmployeeForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Employee
        exclude = ["user"]  # Exclude the 'user' field
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }


class CentreUserForm(forms.ModelForm):
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = CentreUserAccount
        exclude = ["user", "username", "password", "usertype"]

        widgets = {
            "photo": forms.FileInput(attrs={"accept": "image/*"}),
            "aadhaar_front_side_uploading": forms.FileInput(
                attrs={"accept": "image/*"}
            ),
            "aadhaar_back_side_uploading": forms.FileInput(attrs={"accept": "image/*"}),
            "pan_card_uploading": forms.FileInput(attrs={"accept": "image/*"}),
            "sign_uploading": forms.FileInput(attrs={"accept": "image/*"}),
            "another_document": forms.FileInput(attrs={"accept": "image/*"}),
            # "latitude": forms.TextInput(attrs={"placeholder": "Enter latitude"}),
            # "longitude": forms.TextInput(attrs={"placeholder": "Enter longitude"}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if len(str(mobile)) != 10:
            raise ValidationError("Mobile number must be 10 digits long.")
        return mobile

    def clean_alternative_mobile(self):
        alternative_mobile = self.cleaned_data.get("alternative_mobile")
        if alternative_mobile and len(str(alternative_mobile)) != 10:
            raise ValidationError("Alternative mobile number must be 10 digits long.")
        return alternative_mobile

    def clean_aadhaar_number(self):
        aadhaar_number = self.cleaned_data.get("aadhaar_number")
        if aadhaar_number and len(str(aadhaar_number)) != 12:
            raise ValidationError("Aadhaar number must be 12 digits long.")
        return aadhaar_number

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValidationError("Enter a valid email address.")
        return email

    def clean_centre_phone_number(self):
        centre_phone_number = self.cleaned_data.get("centre_phone_number")
        if len(str(centre_phone_number)) != 10:
            raise ValidationError("Centre phone number must be 10 digits long.")
        return centre_phone_number

    def clean_state(self):
        state = self.cleaned_data.get("state")
        if not re.match(r"^[a-zA-Z\s]+$", state):
            raise ValidationError("State must contain only letters and spaces.")
        return state

    def clean_district(self):
        district = self.cleaned_data.get("district")
        if not re.match(r"^[a-zA-Z\s]+$", district):
            raise ValidationError("District must contain only letters and spaces.")
        return district

    def clean_taluk(self):
        taluk = self.cleaned_data.get("taluk")
        if taluk and not re.match(r"^[a-zA-Z\s]+$", taluk):
            raise ValidationError("Taluk must contain only letters and spaces.")
        return taluk

    def clean_pin_code(self):
        pin_code = self.cleaned_data.get("pin_code")
        if len(str(pin_code)) < 4:
            raise ValidationError("PIN code must be at least 4 digits long.")
        return pin_code

    # def clean_latitude(self):
    #     latitude = self.cleaned_data.get("latitude")
    #     if latitude:
    #         # Convert decimal latitude to string for regex or string-based operations
    #         latitude_str = str(latitude)
    #         # Example of validation using regex (for illustration purposes)
    #         latitude_pattern = re.compile(r"^[+-]?([1-8]?\d(\.\d+)?|90(\.0+)?)$")
    #         if not latitude_pattern.match(latitude_str):
    #             raise forms.ValidationError("Invalid latitude format.")
    #     return latitude

    # def clean_longitude(self):
    #     longitude = self.cleaned_data.get("longitude")
    #     if longitude:
    #         # Convert decimal longitude to string for regex or string-based operations
    #         longitude_str = str(longitude)
    #         # Example of validation using regex (for illustration purposes)
    #         longitude_pattern = re.compile(
    #             r"^[+-]?((1[0-7]\d(\.\d+)?|180(\.0+)?)|(\d{1,2}(\.\d+)?))$"
    #         )
    #         if not longitude_pattern.match(longitude_str):
    #             raise forms.ValidationError("Invalid longitude format.")
    #     else:
    #         raise forms.ValidationError("no longitude")
    #     return longitude

class ServiceFilterForm(forms.Form):
    show_popular = forms.BooleanField(required=False, label="Show Popular Services")


class KeralaSubCentreForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    username = forms.CharField(max_length=255)

    class Meta:
        model = KeralaSubCentre
        exclude = ["user"]

        widgets = {
            "photo": forms.FileInput(
                attrs={"accept": "image/*"}
            ),  # Add this to accept only image files
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = False


class StateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    username = forms.CharField(max_length=255)

    class Meta:
        model = State
        exclude = ["user"]

        widgets = {
            "photo": forms.FileInput(attrs={"accept": "image/*"}),
            "aadhaar_uploading": forms.FileInput(attrs={"accept": "image/*"}),
            "pan_card_uploading": forms.FileInput(attrs={"accept": "image/*"}),
            "sign_uploading": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = False
        self.fields["aadhaar_uploading"].required = True
        self.fields["pan_card_uploading"].required = True
        self.fields["sign_uploading"].required = True

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if len(str(mobile)) != 10:
            raise ValidationError("Mobile number must be 10 digits long.")
        return mobile

    def clean_aadhaar_number(self):
        aadhaar_number = self.cleaned_data.get("aadhaar_number")
        if len(str(aadhaar_number)) != 12:
            raise ValidationError("Aadhaar number must be 12 digits long.")
        return aadhaar_number

    def clean_pan_card_number(self):
        pan_card_number = self.cleaned_data.get("pan_card_number")
        if len(pan_card_number) != 10:
            raise ValidationError("PAN card number must be 10 characters long.")
        return pan_card_number

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValidationError("Enter a valid email address.")
        return email

    def clean_state(self):
        state = self.cleaned_data.get("state")
        if not re.match(r"^[a-zA-Z\s]+$", state):
            raise ValidationError("State must contain only letters and spaces.")
        return state

    def clean_District(self):
        District = self.cleaned_data.get("District")
        if not re.match(r"^[a-zA-Z\s]+$", District):
            raise ValidationError("District must contain only letters and spaces.")
        return District

    def clean_taluk(self):
        taluk = self.cleaned_data.get("taluk")
        if not re.match(r"^[a-zA-Z\s]+$", taluk):
            raise ValidationError("Taluk must contain only letters and spaces.")
        return taluk

    def clean_pin_code(self):
        pin_code = self.cleaned_data.get("pin_code")
        if len(str(pin_code)) < 4:
            raise ValidationError("PIN code must be at least 4 digits long.")
        return pin_code




# //////////////////////////////////////////// ACCOUNTS FORMS START //////////////////////////////////////////// #


# ACCOUNT MASTER


# ACCOUNT MASTER

from django import forms
from django.utils.html import mark_safe
from .models import Table_Accountsmaster

class AccountMasterForm(forms.ModelForm):
    class Meta:
        model = Table_Accountsmaster
        fields = [
            'head', 'group', 'gstno', 'category', 'address1', 'state', 'address2',
            'statecode', 'address3', 'panno', 'district', 'creditlimit', 'email',
            'creditdays', 'telno', 'pricegroup', 'mobile', 'opbalance', 'whattsapp',
            'debitcredit', 'currentbalance',
        ]
        widgets = {
            'head': forms.TextInput(attrs={
                'class': 'custom-class',
                'style': 'background-color:rgb(185, 233, 246);text-transform: uppercase;',
            }),
            'gstno': forms.TextInput(attrs={
                'style': 'text-transform: uppercase;',
            }),
            'state': forms.TextInput(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'statecode': forms.TextInput(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'panno': forms.TextInput(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'creditlimit': forms.NumberInput(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'creditdays': forms.NumberInput(attrs={
                'style': 'width: 350px;',   # Adjust the width as needed
            }),
            'opbalance': forms.NumberInput(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'currentbalance': forms.NumberInput(attrs={
                'style': 'width: 150px; height: 40px; background-color: rgb(185, 233, 246);',  # Increased height and color red
                'readonly': 'readonly',  # Make the field read-only
            }),
            'group': forms.Select(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'category': forms.Select(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'pricegroup': forms.Select(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
            'debitcredit': forms.Select(attrs={
                'style': 'width: 350px;',  # Adjust the width as needed
            }),
        }
        labels = {
            'head': 'Head',
            'group': 'Account Group',
            'gstno': 'GST Number',
            'category': 'Category',
            'address1': 'Address 1',
            'state': 'State',
            'address2': 'Address 2',
            'statecode': 'State Code',
            'address3': 'Address 3',
            'panno': 'PAN Number',
            'district': 'District',
            'creditlimit': 'Credit Limit',
            'email': 'Email Address',
            'creditdays': 'Credit Days',
            'telno': 'Telephone Number',
            'pricegroup': 'Price Group',
            'mobile': 'Mobile Number',
            'opbalance': 'Opening Balance',
            'whattsapp': 'WhatsApp Number',
            'debitcredit': 'Debit/Credit',
            'currentbalance': 'Current Balance',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(AccountMasterForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['head'].widget.attrs['readonly'] = False
            self.fields['head'].required = False

    def clean_head(self):
        head = self.cleaned_data.get('head')
        if self.user is None:
            raise forms.ValidationError("User must be provided for validation.")

        # Check if the head already exists for this user
        if Table_Accountsmaster.objects.filter(head=head, user=self.user).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This head already exists for your account. Please choose a different one.")
        
        return head

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile and len(mobile) != 10:
            raise forms.ValidationError(mark_safe("<span style='color:red; font-size:12px;'>Mobile number must be 10 digits long.</span>"))
        return mobile

    def clean_whattsapp(self):
        whattsapp = self.cleaned_data.get('whattsapp')
        if whattsapp and len(whattsapp) != 10:
            raise forms.ValidationError(mark_safe("<span style='color:red; font-size:12px;'>WhatsApp number must be 10 digits long.</span>"))
        return whattsapp




class ComapnyDetailsMasterForm(forms.ModelForm):
    class Meta:
        model = Table_Companydetailsmaster
        fields = [
            "company_id",
            "companyname",
            "address1",
            "pinCode",
            "address2",
            "phoneno",
            "address3",
            "mobile",
            "email",
            "gst",
            "pan",
            "finyearfrom",
            "finyearto",
        ]

        labels = {
            "company_id": "Company ID",
            "companyname": "Company Name",
            "address1": "Address 1",
            "address2": "Address 2",
            "address3": "Address 3",
            "pinCode": "Pin Code",
            "phoneno": "Phone Number",
            "mobile": "Mobile Number",
            "email": "Email Address",
            "gst": "GST Number",
            "pan": "PAN Number",
            "finyearfrom": "Financial Year From",
            "finyearto": "Financial Year To",
        }

        widgets = {
            "companyname": forms.TextInput(
                attrs={
                    "class": "custom-class",
                    "style": "background-color:rgb(185, 233, 246); text-transform: uppercase;",
                }
            ),
            "company_id": forms.TextInput(
                attrs={
                    "style": "text-transform: uppercase; width:90px; padding-left:35px"
                }
            ),
            "gst": forms.TextInput(attrs={"style": "text-transform: uppercase;"}),
            "pan": forms.TextInput(attrs={"style": "text-transform: uppercase;"}),
            "finyearfrom": DateInput(
                format="%d/%m/%Y", attrs={"type": "date", "style": "width: 130px;"}
            ),
            "finyearto": DateInput(
                format="%d/%m/%Y",
                attrs={"type": "date", "style": "width: 130px; margin-left: 18px;"},
            ),
        }

    def _init_(self, *args, **kwargs):
        self.instance = kwargs.get("instance", None)
        super(ComapnyDetailsMasterForm, self)._init_(*args, **kwargs)

        if self.instance and self.instance.pk:
            # If editing an existing instance, exclude finyearfrom and finyearto fields
            self.fields.pop("finyearfrom")
            self.fields.pop("finyearto")

        if self.instance and self.instance.pk:
            self.fields["company_id"].widget.attrs["readonly"] = True
            self.fields["company_id"].widget.attrs[
                "style"
            ] += " background-color: lightgrey; text-align: center;"

    def clean_companyname(self):
        companyname = self.cleaned_data.get("companyname")
        if companyname:
            companyname = companyname.upper()
            # Check for uniqueness of companyname excluding the current instance if it's an update
            qs = Table_Companydetailsmaster.objects.filter(companyname=companyname)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This COMPANY NAME already exists.")
        return companyname

    def clean_company_id(self):
        company_id = self.cleaned_data.get("company_id")
        if company_id and not company_id.isalpha():
            raise forms.ValidationError("Company ID must contain only letters.")
        return company_id.upper() if company_id else None

    def clean_gst(self):
        gst = self.cleaned_data.get("gst")
        if gst and len(gst) != 15:
            raise forms.ValidationError(
                "GST number must be exactly 15 characters long."
            )
        # Check for uniqueness of GST number excluding the current instance if it's an update
        qs = Table_Companydetailsmaster.objects.filter(gst=gst)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This GST number already exists.")
        return gst.upper() if gst else None

    def clean_pan(self):
        pan = self.cleaned_data.get("pan")
        if pan and len(pan) != 10:
            raise forms.ValidationError(
                "PAN number must be exactly 10 characters long."
            )
        return pan.upper() if pan else None

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if mobile and (not mobile.isdigit() or len(mobile) != 10):
            raise forms.ValidationError("Mobile number must contain 10 digits only.")
        return mobile

    def clean(self):
        cleaned_data = super().clean()
        company_id = cleaned_data.get("company_id")
        if company_id:
            # Check for uniqueness of company_id excluding the current instance if it's an update
            qs = Table_Companydetailsmaster.objects.filter(company_id=company_id)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "company_id", f"Company ID '{company_id}' already exists."
                )
        return cleaned_data

    def save(self, commit=True):
        try:
            return super(ComapnyDetailsMasterForm, self).save(commit=commit)
        except IntegrityError:
            self.add_error(
                "company_id",
                f"Company ID '{self.cleaned_data.get('company_id')}' already exists.",
            )
            raise ValidationError(
                f"Company ID '{self.cleaned_data.get('company_id')}' already exists."
            )



# //////////////////////////////////////////// ACCOUNTS FORMS END //////////////////////////////////////////// #



 

    
