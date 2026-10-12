"""Safe, route-aware error responses for the web application."""

from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.urls import reverse


GENERAL_ERROR_MESSAGE = "Unable to complete this request right now. Please try again later."
NOT_FOUND_MESSAGE = "The requested item is not available or may have been removed."
FORBIDDEN_MESSAGE = "You do not have permission to access this page."


def _is_franchise_dashboard_request(request):
    path = (getattr(request, "path_info", None) or getattr(request, "path", "") or "").rstrip("/")
    return path == "/franchise-dashboard" or path.startswith("/franchise-dashboard/")


def _is_ajax_request(request):
    headers = getattr(request, "headers", {})
    return headers.get("X-Requested-With") == "XMLHttpRequest"


def _error_context(request, status_code, message):
    is_franchise = _is_franchise_dashboard_request(request)
    if is_franchise:
        try:
            dashboard_url = reverse("web:centre_dashboard")
            service_url = reverse("web:state_list")
        except Exception:
            dashboard_url = "/franchise-dashboard/dashboard/"
            service_url = "/franchise-dashboard/all-states/"
        return {
            "error_base_template": "web/franchise/base.html",
            "error_dashboard_url": dashboard_url,
            "error_dashboard_label": "Go to Dashboard",
            "franchise_service_url": service_url,
            "is_franchise_dashboard_error": True,
            "error_status_code": status_code,
            "error_message": message,
            "error_title": {
                403: "Access restricted",
                404: "Item not found",
                500: "Something went wrong",
            }.get(status_code, "Request unavailable"),
        }

    return {
        "error_base_template": "web/error_base.html",
        "error_dashboard_url": reverse("web:index"),
        "error_dashboard_label": "Go to Home",
        "is_franchise_dashboard_error": False,
        "error_status_code": status_code,
        "error_message": message,
        "error_title": {
            403: "Access restricted",
            404: "Page not found",
            500: "Something went wrong",
        }.get(status_code, "Request unavailable"),
    }


def render_error_response(request, status_code, message=None):
    """Render a safe HTML error page or JSON response without exception details."""
    messages = {
        403: FORBIDDEN_MESSAGE,
        404: NOT_FOUND_MESSAGE,
        500: GENERAL_ERROR_MESSAGE,
    }
    message = message or messages.get(status_code, GENERAL_ERROR_MESSAGE)
    context = _error_context(request, status_code, message)

    if context["is_franchise_dashboard_error"] and _is_ajax_request(request):
        return JsonResponse({"success": False, "message": message}, status=status_code)

    try:
        template = get_template(f"{status_code}.html")
        # Use a plain template context for error pages. This prevents a failing
        # application context processor or database lookup from replacing a
        # safe error response with another exception.
        html = template.render({"request": request, **context})
    except Exception:
        # Keep the response user-friendly even if a deployment has a bad
        # template/static configuration. The real failure is still visible in
        # the server's normal Django error logs.
        html = (
            "<!doctype html><html><head><title>Request unavailable</title></head>"
            "<body><main><h1>Request unavailable</h1>"
            f"<p>{message}</p></main></body></html>"
        )
    return HttpResponse(html, status=status_code)


def handler403(request, exception=None):
    return render_error_response(request, 403, FORBIDDEN_MESSAGE)


def handler404(request, exception=None):
    return render_error_response(request, 404, NOT_FOUND_MESSAGE)


def handler500(request):
    return render_error_response(request, 500, GENERAL_ERROR_MESSAGE)