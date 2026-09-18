# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.conf import settings
# from .models import Wallet

# User = settings.AUTH_USER_MODEL


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_wallet(sender, instance, created, **kwargs):
#     if created:
#         Wallet.objects.create(user=instance)
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import User, UserProfile

# @receiver(post_save, sender=User)
# def create_profile(sender, instance, created, **kwargs):
#     if created and not hasattr(instance, 'profile'):
#         UserProfile.objects.create(user=instance, name=instance.username)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import CommissionWallet,WalletTransaction, Wallet, WalletRequest

User = get_user_model()

@receiver(post_save, sender=User)
def create_commission_wallet(sender, instance, created, **kwargs):
    if created:
        CommissionWallet.objects.get_or_create(user=instance)


@receiver(post_save, sender=WalletRequest)
def credit_wallet_on_approval(sender, instance, created, **kwargs):

    if not created and instance.status == 'approved':

        wallet, created_wallet = Wallet.objects.get_or_create(user=instance.user)

        # Check using WalletRequest link
        if not WalletTransaction.objects.filter(wallet_request=instance).exists():

            wallet.balance += instance.amount
            wallet.save()

            WalletTransaction.objects.create(
                user=instance.user,
                wallet_request=instance,
                amount=instance.amount,
                txn_type='credit',
                description="Admin Approved Wallet Add"
            )
            

