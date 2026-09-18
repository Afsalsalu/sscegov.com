from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
import random
import string



from .models import (
    User,
    State,
    District,
    UserProfile,
    Wallet,
    WalletTransaction,
    CommissionWallet,
    CommissionTransaction,
    WalletRequest,
    CommissionWithdrawRequest,
    CouponPurchase,
    RoleRegistrationCharge,
    RoleCouponPrice,
    PSAMaster
)

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = (
        'username',
        'email',
        'role',
        'mobile',
        'is_email_verified',
        'status',
        'created_by',
    )

    list_filter = ('role', 'status', 'is_email_verified')
    search_fields = ('username', 'email', 'mobile')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {
            'fields': ('role', 'mobile', 'status', 'is_email_verified', 'created_by')
        }),
    )

admin.site.register(RoleRegistrationCharge)

@admin.register(RoleCouponPrice)
class RoleCouponPriceAdmin(admin.ModelAdmin):
    list_display = ("role", "price")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = ('user', 'state', 'is_approved', 'created_at')
    list_filter = ('state', 'is_approved')
    search_fields = ('user__username', 'user__email')

    def save_model(self, request, obj, form, change):

        if obj.is_approved and not obj.user.is_active:

            user = obj.user

            # Login ID format: SSC + mobile
            login_userid = f"SSC{user.mobile}"
            login_password = f"SSC{user.mobile}"

            # DO NOT change username
            user.set_password(login_password)
            user.is_active = True
            user.must_change_password = True
            user.save()

            send_mail(
                subject="Your Account Approved - Login Details",
                message=f"""
Congratulations!

Your account has been approved.

Login User ID: {login_userid}
Password: {login_password}

Please login and change your password after first login.

Thank You.
""",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )

        super().save_model(request, obj, form, change)

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)
    search_fields = ('name',)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'txn_type', 'created_at')
    list_filter = ('txn_type', 'created_at')
    search_fields = ('user__username',)

@admin.register(CommissionWallet)
class CommissionWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

@admin.register(CommissionTransaction)
class CommissionTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_user', 'amount', 'level', 'created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('user__username', 'from_user__username')

@admin.register(WalletRequest)
class WalletRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username',)

@admin.register(CommissionWithdrawRequest)
class CommissionWithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username',)

@admin.register(CouponPurchase)
class CouponPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'quantity',
        'total_amount',
        'status',
        'psa_status',
        'submission_id',
        'amount_deducted',
        'done',
        'created_at'
    )

    list_filter = ('status', 'psa_status', 'amount_deducted', 'done')
    search_fields = ('user__username',)

@admin.register(PSAMaster)
class PSAMasterAdmin(admin.ModelAdmin):
    list_display = ('psa_login_id', 'balance', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('psa_login_id',)
