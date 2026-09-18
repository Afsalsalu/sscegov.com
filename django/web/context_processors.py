from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.urls import reverse

from .models import AddState


def franchise_service_navigation(request):
    """Resolve the shared franchise Service link from the logged-in centre."""
    service_url = reverse("web:state_list")
    user = getattr(request, "user", None)

    if not getattr(user, "is_authenticated", False) or getattr(user, "usertype", None) != "centre":
        return {"franchise_service_url": service_url}

    try:
        centre_account = user.centre
    except (AttributeError, ObjectDoesNotExist):
        return {"franchise_service_url": service_url}

    state_value = (centre_account.state or "").strip()
    if not state_value:
        return {"franchise_service_url": service_url}

    state = AddState.objects.filter(
        Q(slug__iexact=state_value) | Q(state_name__iexact=state_value)
    ).first()
    if state:
        service_url = reverse("web:state_detail", kwargs={"slug": state.slug})

    return {"franchise_service_url": service_url}
