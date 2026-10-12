from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.urls import reverse

from .language import SUPPORTED_LANGUAGES, user_language
from .enquiry_utils import get_permitted_franchise_services
from .models import AddState, StateService
from .whatsapp_utils import get_support_whatsapp_url


def franchise_service_navigation(request):
    """Resolve the shared franchise Service link from the logged-in centre."""
    service_url = reverse("web:state_list")
    support_whatsapp_url = None
    user = getattr(request, "user", None)
    service_page_names = {"state_list", "state_detail", "service_detail"}
    resolver_match = getattr(request, "resolver_match", None)
    service_context = bool(
        resolver_match and resolver_match.url_name in service_page_names
    )
    support_services = StateService.objects.none()
    support_service_id = None

    if not getattr(user, "is_authenticated", False) or getattr(user, "usertype", None) != "centre":
        return {
            "franchise_service_url": service_url,
            "support_whatsapp_url": support_whatsapp_url,
            "franchise_support_service_context": False,
            "franchise_support_services": support_services,
            "franchise_support_service_id": support_service_id,
        }

    try:
        centre_account = user.centre
    except (AttributeError, ObjectDoesNotExist):
        return {
            "franchise_service_url": service_url,
            "support_whatsapp_url": get_support_whatsapp_url(user),
            "franchise_support_service_context": service_context,
            "franchise_support_services": support_services,
            "franchise_support_service_id": support_service_id,
        }

    support_whatsapp_url = get_support_whatsapp_url(user)

    state_value = (centre_account.state or "").strip()
    if not state_value:
        return {
            "franchise_service_url": service_url,
            "support_whatsapp_url": support_whatsapp_url,
            "franchise_support_service_context": service_context,
            "franchise_support_services": support_services,
            "franchise_support_service_id": support_service_id,
        }

    state = AddState.objects.filter(
        Q(slug__iexact=state_value) | Q(state_name__iexact=state_value)
    ).first()
    if state:
        service_url = reverse("web:state_detail", kwargs={"slug": state.slug})

    if service_context:
        support_services = get_permitted_franchise_services(user)
        if resolver_match.url_name == "service_detail":
            try:
                requested_service_id = int(resolver_match.kwargs.get("pk"))
            except (TypeError, ValueError):
                requested_service_id = None
            if requested_service_id and support_services.filter(
                pk=requested_service_id
            ).exists():
                support_service_id = requested_service_id

    return {
        "franchise_service_url": service_url,
        "support_whatsapp_url": support_whatsapp_url,
        "franchise_support_service_context": service_context,
        "franchise_support_services": support_services,
        "franchise_support_service_id": support_service_id,
    }


def language_preferences(request):
    user = getattr(request, "user", None)
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "current_language": user_language(user, getattr(request, "session", None)),
        "language_switch_url": reverse("web:set_language"),
    }
