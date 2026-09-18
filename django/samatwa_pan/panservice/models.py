from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

ROLE_CHOICES = (
    ('admin', 'Admin'),
    ('state', 'State Distributor'),
    ('district', 'District Distributor'),
    ('retailer', 'Retailer'),
)

class RoleRegistrationCharge(models.Model):

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.role} - ₹{self.amount}"

class RoleCouponPrice(models.Model):
    role = models.CharField(max_length = 20, choices = ROLE_CHOICES, unique = True)
    price = models.DecimalField(max_digits = 10, decimal_places = 2)

    def __str__(self):
        return f"{self.get_role_display()} - {self.price}"

class User(AbstractUser):

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='retailer')

    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)

    status = models.CharField(max_length=20, default='active')
    is_email_verified = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_users'
    )
    @property
    def registration_fee(self):
        charge = RoleRegistrationCharge.objects.filter(role=self.role).first()
        if charge:
            return charge.amount
        return 0

    def __str__(self):
        return f"{self.username} ({self.role})"



class State(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class District(models.Model):
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="districts"
    )
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class UserProfile(models.Model):

    GENDER_CHOICES = (
        ('male','Male'),
        ('female', 'Female'),
        ('other', 'Other')
    )
    MARGIN_SLAB_CHOICES = (
        ('default', 'Default'),
        ('ssc_retailer', 'SSC Retailer'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    gender = models.CharField(max_length = 10, choices = GENDER_CHOICES, blank = True, null = True)
    address = models.CharField(max_length=500, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    company = models.CharField(max_length = 50, blank = True, null = True)
    district = models.ForeignKey(District, on_delete = models.SET_NULL, blank = True, null = True)
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    coupons_available = models.PositiveIntegerField(default=0)

    upi_id = models.CharField(max_length=20, blank=True, null=True)
    pan = models.CharField(max_length=20, blank=True, null=True)
    aadhaar = models.CharField(max_length=20, blank=True, null=True)
    margin_slab = models.CharField(max_length=50, choices = MARGIN_SLAB_CHOICES, blank=True, null = True)
    uti_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    nsdl_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class WalletRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} ({self.status})"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} Wallet ₹{self.balance}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    wallet_request = models.OneToOneField(
        WalletRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    txn_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal

class CouponPurchase(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    PSA_STATUS_CHOICES = (
        ('issued', 'Issued'),
        ('started', 'Started'),
        ('partially_completed', 'Partially Completed'),
        ('fully_completed', 'Fully Completed'),
    )
    REREQUEST_STATUS_CHOICES = (
        ('none', 'None'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    psa_username = models.CharField(max_length=100, null=True, blank=True)
    psa_password = models.CharField(max_length=100, null=True, blank=True)
    psa_status = models.CharField(max_length=30, choices=PSA_STATUS_CHOICES, default='issued')
    submission_id = models.CharField(max_length=100, null=True, blank=True)
    amount_deducted = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    approved_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    done = models.BooleanField(default=False, null=True, blank=True)
    request_again = models.BooleanField(default=False)
    rerequest_status = models.CharField(
        max_length=20,
        choices=REREQUEST_STATUS_CHOICES,
        default='none'
    )
    rerequest_requested_at = models.DateTimeField(null=True, blank=True)



    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    admin_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    state_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    district_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):

        if self.pk:
            old = CouponPurchase.objects.get(pk=self.pk)

            if old.status == "pending" and self.status == "approved":

                with transaction.atomic():

                    wallet = Wallet.objects.select_for_update().get(user=self.user)

                    total = Decimal(self.unit_price) * Decimal(self.quantity)

                    if wallet.balance < total:
                        raise ValueError("Insufficient wallet balance")
                    
                    from .services import create_wallet_transaction


                    # ? USE SERVICE (IMPORTANT)
                    create_wallet_transaction(
                        user=self.user,
                        amount=total,
                        txn_type='debit',
                        description=f"Coupon Purchase ({self.quantity})"
                    )

                    # Increase coupons
                    profile = self.user.profile
                    profile.coupons_available += self.quantity
                    profile.save(update_fields=["coupons_available"])

                    self.total_amount = total
                    self.approved_at = timezone.now()
                    self.done = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.quantity} coupons - {self.status}"
class CommissionTransaction(models.Model):
    TXN_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions_received')
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_generated'
    )

    coupon_request = models.ForeignKey(
        'CouponPurchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    level = models.CharField(max_length=20)  # 'Admin', 'State', 'District'
    txn_type = models.CharField(max_length=10, choices=TXN_CHOICES, default="credit")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} earned ₹{self.amount} ({self.level})"

        
class CommissionWithdrawRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')  # pending/approved/rejected
    created_at = models.DateTimeField(auto_now_add=True)

class CommissionWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='commission_wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} Commission Wallet ₹{self.balance}"

class PSAMaster(models.Model):
    STATUS_CHOICES = (
        ('issued', 'Issued'),
        ('started', 'Started'),
        ('partially_completed', 'Partially Completed'),
        ('fully_completed', 'Fully Completed'),
    )

    psa_login_id = models.CharField(max_length=150, unique=True)
    psa_password = models.CharField(max_length=150)
    
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.psa_login_id
