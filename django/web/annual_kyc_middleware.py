from django.shortcuts import redirect

from .annual_kyc_services import annual_kyc_access_restricted, record_annual_kyc_access_restricted
from .models import CentreUserAccount


class CentreAnnualKYCMiddleware:
    """Central URL guard for annual KYC, leaving the existing reactivation flow independent."""

    allowed_prefixes = (
        "/login/",
        "/custom_login",
        "/logout/",
        "/accounts/logout/",
        "/franchise-dashboard/annual-kyc/",
        "/franchise-dashboard/enquiries/",
        "/franchise-dashboard/profile/",
        "/centre-contact/",
        "/contact/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or ""
        is_allowed = any(path.startswith(prefix) for prefix in self.allowed_prefixes)
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and getattr(user, "usertype", None) == "centre"
            and not is_allowed
        ):
            try:
                centre = user.centre
            except CentreUserAccount.DoesNotExist:
                centre = None
            # Inactivity/manual reactivation remains a separate priority flow.
            if centre and centre.is_active and annual_kyc_access_restricted(centre):
                record_annual_kyc_access_restricted(centre, actor=user)
                response = redirect("web:annual_kyc")
                response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response["Pragma"] = "no-cache"
                return response

        response = self.get_response(request)
        if (
            user
            and user.is_authenticated
            and getattr(user, "usertype", None) == "centre"
            and path.startswith("/franchise-dashboard/annual-kyc/")
        ):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
        return response
