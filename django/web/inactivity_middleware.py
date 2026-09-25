from django.shortcuts import redirect

from .models import CentreUserAccount


class CentreInactivityMiddleware:
    """Keep inactivity-disabled centres inside the reactivation workflow."""

    allowed_prefixes = (
        "/login/",
        "/logout/",
        "/accounts/logout/",
        "/franchise-dashboard/reactivation/",
        "/franchise-dashboard/enquiries/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path_info
        is_allowed = any(prefix in path for prefix in self.allowed_prefixes)
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
            if centre and (centre.inactive_due_to_inactivity or centre.manual_disabled):
                response = redirect("web:centre_reactivation")
                response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response["Pragma"] = "no-cache"
                return response

        response = self.get_response(request)
        if (
            user
            and user.is_authenticated
            and getattr(user, "usertype", None) == "centre"
            and "/franchise-dashboard/reactivation/" in path
        ):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
        return response
