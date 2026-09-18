from django.utils.translation import gettext_lazy as _


class PaymentStatus:
    SUCCESS = "Success"
    FAILURE = "Failure"
    PENDING = "Pending"

    CHOICES = [
        (SUCCESS, _("Success")),
        (FAILURE, _("Failure")),
        (PENDING, _("Pending")),
    ]
