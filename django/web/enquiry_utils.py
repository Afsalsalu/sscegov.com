from .whatsapp_utils import get_support_whatsapp_url


def get_permitted_franchise_services(user):
    """Return active services belonging to the authenticated centre's state."""
    from .models import StateService
    from .whatsapp_utils import resolve_user_state

    state = resolve_user_state(user)
    if not state:
        return StateService.objects.none()
    return StateService.objects.filter(state=state, is_active=True).order_by(
        "service_name", "pk"
    )


__all__ = ["get_permitted_franchise_services", "get_support_whatsapp_url"]
