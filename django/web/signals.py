from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Register, UserActivityLog

# Function to get the client's IP address
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Signal receiver function to log user login
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip_address = get_client_ip(request)
    UserActivityLog.objects.create(user=user, ip_address=ip_address)

# Signal receiver function to send user credentials upon registration
@receiver(post_save, sender=Register)
def send_user_credentials(sender, instance, created, **kwargs):
    if created:
        # Send email with username and password
        send_mail(
            "Your Registration Details",
            f"Username: {instance.username}\nPassword: {instance.password}",
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=False,
        )
