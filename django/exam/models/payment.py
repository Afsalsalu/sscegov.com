# exam/models/payment.py

from django.db import models

from exam.constants import PaymentStatus

from .user_registration import UserRegistration


class Payment(models.Model):
    user_registration = models.ForeignKey(UserRegistration, on_delete=models.CASCADE)
    amount = models.FloatField(default=2.0)  # Set amount to 2 INR
    status = models.CharField(
        max_length=254, choices=PaymentStatus.CHOICES, default=PaymentStatus.PENDING
    )
    provider_order_id = models.CharField(max_length=40)
    payment_id = models.CharField(max_length=36)
    signature_id = models.CharField(max_length=128)
    is_certificate_payment = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user_registration.name} - {self.amount} - {self.status}"
