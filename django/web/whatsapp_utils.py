"""State-aware WhatsApp support resolution and number validation."""

import re
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from .language import normalize_state


SUPPORT_MESSAGE = "Hello, I need support with my franchise account."
_NUMBER_INPUT_RE = re.compile(r"\+?[0-9\s().-]+")


def normalize_whatsapp_number(value):
    """Return an Indian WhatsApp number as country-code-prefixed digits only."""
    if value is None or not str(value).strip():
        return ""

    raw_number = str(value).strip()
    if not _NUMBER_INPUT_RE.fullmatch(raw_number):
        raise ValidationError(
            "Enter a WhatsApp number using digits and optional +, spaces, dots, parentheses, or dashes."
        )

    digits = re.sub(r"\D", "", raw_number)
    if not 8 <= len(digits) <= 15:
        raise ValidationError("WhatsApp numbers must contain 8 to 15 digits.")
    if not digits.startswith("91"):
        raise ValidationError("Include India's country code 91 in the WhatsApp number.")
    return digits


def build_whatsapp_url(number):
    """Build a WhatsApp URL only after validating the configured number."""
    try:
        normalized_number = normalize_whatsapp_number(number)
    except ValidationError:
        return ""
    if not normalized_number:
        return ""
    return "https://wa.me/{}?{}".format(
        normalized_number,
        urlencode({"text": SUPPORT_MESSAGE}),
    )


def resolve_state(value):
    """Resolve an AddState by either its slug or normalized display name."""
    from .models import AddState

    normalized_value = normalize_state(value)
    if not normalized_value:
        return None

    for state in AddState.objects.all().only(
        "id", "state_name", "slug", "whatsapp_number", "whatsapp_enabled"
    ):
        if normalized_value in {
            normalize_state(state.slug),
            normalize_state(state.state_name),
        }:
            return state
    return None


def resolve_user_state(user):
    """Resolve state exclusively from the authenticated user's centre account."""
    try:
        centre = user.centre
        return resolve_state(getattr(centre, "state", ""))
    except (AttributeError, ObjectDoesNotExist):
        return None


def configured_state_number(state):
    if not state or not state.whatsapp_enabled:
        return ""
    return build_whatsapp_url(state.whatsapp_number)


def get_state_support_url(user):
    """Return the user's state URL, falling back to Kerala when necessary."""
    state = resolve_user_state(user)
    state_url = configured_state_number(state)
    if state_url:
        return state_url

    kerala = resolve_state("kerala")
    return configured_state_number(kerala)


def get_support_whatsapp_url(user=None):
    """Return state-aware support URL, retaining legacy settings-only support."""
    if user is None:
        return build_whatsapp_url(getattr(settings, "SUPPORT_WHATSAPP_NUMBER", ""))
    return get_state_support_url(user)
