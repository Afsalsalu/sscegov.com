from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import activate
from django.views.decorators.http import require_POST

from .language import (
    LANGUAGE_FALLBACK_USER_KEY,
    LANGUAGE_SESSION_KEY,
    SUPPORTED_LANGUAGE_CODES,
    is_dashboard_language_user,
)


def _default_dashboard_url(user):
    if getattr(user, "is_superuser", False) or getattr(user, "usertype", None) == "Administrator":
        return "web:admin_dashboard"
    if getattr(user, "usertype", None) == "HeadOffice":
        return "web:headoffice_dashboard"
    return "web:centre_dashboard"


def _safe_next_url(request):
    next_url = (request.POST.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse(_default_dashboard_url(request.user))


@login_required
@require_POST
def set_language(request):
    """Persist a supported language and return to a safe local dashboard page."""
    if not is_dashboard_language_user(request.user):
        return HttpResponseForbidden("Language selection is not available for this account.")

    language = (request.POST.get("language") or "").strip()
    if language not in SUPPORTED_LANGUAGE_CODES:
        return HttpResponseBadRequest("Unsupported language.")

    try:
        request.user.preferred_language = language
        request.user.save(update_fields=("preferred_language",))
        request.session.pop(LANGUAGE_FALLBACK_USER_KEY, None)
        request.session.pop(LANGUAGE_SESSION_KEY, None)
    except (AttributeError, DatabaseError):
        # Keep the preference usable if this code is briefly deployed before
        # its user-field migration. Bind the fallback to this user.
        request.session[LANGUAGE_FALLBACK_USER_KEY] = request.user.pk
        request.session[LANGUAGE_SESSION_KEY] = language

    request.session.modified = True
    activate(language)
    request.LANGUAGE_CODE = language
    return redirect(_safe_next_url(request))
