from django.shortcuts import redirect
from django.conf import settings

from .annual_kyc_services import annual_kyc_access_restricted, record_annual_kyc_access_restricted
from .models import CentreUserAccount


class CentreAnnualKYCMiddleware:
    """Central URL guard for annual KYC, leaving the existing reactivation flow independent."""

    # The centre's status page and every payment/OTP endpoint live below this
    # prefix. Keep the whole renewal flow reachable while annual access is
    # restricted, including when the application is mounted under /test/.
    annual_kyc_allowed_prefixes = (
        "/franchise-dashboard/annual-kyc/",
    )
    allowed_prefixes = (
        "/login/",
        "/custom_login",
        "/logout/",
        "/accounts/logout/",
        *annual_kyc_allowed_prefixes,
        "/franchise-dashboard/enquiries/",
        "/franchise-dashboard/profile/",
        "/centre-contact/",
        "/contact/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _path_without_script_prefix(request):
        path = request.path_info or request.path or ""
        script_prefix = str(getattr(settings, "FORCE_SCRIPT_NAME", "") or "").rstrip("/")
        if script_prefix and path.startswith(script_prefix + "/"):
            return path[len(script_prefix):] or "/"
        return path

    def __call__(self, request):
        path = self._path_without_script_prefix(request)
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
            and any(path.startswith(prefix) for prefix in self.annual_kyc_allowed_prefixes)
        ):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
        return response
