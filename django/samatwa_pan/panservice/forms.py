from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import UserProfile, State, District,ROLE_CHOICES

User = get_user_model()



GENDER_CHOICES = (
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
)

# ----------------------------------------
# STATE CREATE FORM
# ----------------------------------------
# class StateCreateForm(forms.Form):
#     full_name = forms.CharField(max_length=200, label="Full Name")
#     mobile = forms.CharField(max_length=12, label="Mobile Number")
#     dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
#     gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)
#     aadhar = forms.CharField(max_length=20, required=False)
#     pan = forms.CharField(max_length=20, required=False)
#     # company = forms.CharField(max_length=150, required=False, label="Company/Shop Name")
#     address = forms.CharField(widget=forms.Textarea, required=False)
#     pin_code = forms.CharField(max_length=10, label="PIN Code", required=False)
#     state = forms.CharField(max_length=50, label="State Name", required=False)


# ----------------------------------------
# DISTRICT CREATE FORM
# ----------------------------------------
# class DistrictCreateForm(forms.Form):
#     full_name = forms.CharField(max_length=200)
#     mobile = forms.CharField(max_length=12)
#     district = forms.CharField(max_length=50, label="District Name")
#     state = forms.CharField(max_length=50, required=False)  # Admin only
#     dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
#     gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)
#     aadhar = forms.CharField(max_length=20, required=False)
#     pan = forms.CharField(max_length=20, required=False)
#     company = forms.CharField(max_length=150, required=False)
#     address = forms.CharField(widget=forms.Textarea, required=False)
#     pin_code = forms.CharField(max_length=10, required=False)

#     uti_price = forms.DecimalField(max_digits=8, decimal_places=2, required=False)

#     def __init__(self, *args, creator_price=0, readonly=False, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.fields['uti_price'].label = f"UTI Price: ₹{creator_price}"

#         if readonly:
#             self.fields['uti_price'].widget.attrs['readonly'] = True


# # ----------------------------------------
# # RETAILER CREATE FORM
# # ----------------------------------------
# class RetailerCreateForm(forms.Form):
#     full_name = forms.CharField(max_length=200, label="Full Name")
#     mobile = forms.CharField(max_length=12, label="Mobile Number")

#     state = forms.CharField(max_length=100, required=False, label="State (Admin only)")
#     district = forms.ModelChoiceField(
#         queryset=District.objects.all(),
#         required=False,
#         label="District"
#     )

#     dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
#     gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)
#     aadhar = forms.CharField(max_length=20, required=False)
#     pan = forms.CharField(max_length=20, required=False)
#     company = forms.CharField(max_length=150, required=False)
#     address = forms.CharField(widget=forms.Textarea, required=False)
#     pin_code = forms.CharField(max_length=10, required=False)

#     uti_price = forms.DecimalField(max_digits=8, decimal_places=2, required=False)

#     def __init__(self, *args, creator_price=0, show_price_field=True, editable=False, **kwargs):
#         super().__init__(*args, **kwargs)

#         if show_price_field:
#             self.fields['uti_price'].label = f"UTI Price: ₹{creator_price} +"
#             self.fields['uti_price'].initial = creator_price
#             self.fields['uti_price'].widget.attrs['min'] = creator_price
#             self.fields['uti_price'].widget.attrs['max'] = 107.00

#             if not editable:
#                 self.fields['uti_price'].widget.attrs['readonly'] = True
#         else:
#             self.fields.pop('uti_price', None)




# ----------------------------------------
# OTHER FORMS
# ----------------------------------------
class EditContactForm(forms.Form):
    mobile = forms.CharField(max_length=12, label="Mobile Number")
    email = forms.EmailField(label="Email")


class WalletRequestForm(forms.Form):
    amount = forms.DecimalField(min_value=1, label="Enter Amount (Minimum ₹300)")


class WithdrawForm(forms.Form):
    amount = forms.DecimalField(min_value=1, label="Withdraw Amount")

class CouponPurchaseForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Number of coupons")

class CommissionWithdrawForm(forms.Form):
    amount = forms.DecimalField(min_value=1, label="Withdraw Amount")
