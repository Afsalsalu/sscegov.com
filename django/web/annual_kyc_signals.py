from django.db.models.signals import post_save
from django.dispatch import receiver

from .annual_kyc_services import ensure_annual_kyc_status
from .models import CentreUserAccount


@receiver(post_save, sender=CentreUserAccount)
def create_annual_kyc_cycle(sender, instance, **kwargs):
    if instance.user_id:
        ensure_annual_kyc_status(instance)
