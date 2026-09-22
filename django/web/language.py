"""Shared language configuration and user-language resolution helpers."""

import re
import unicodedata

from django.core.exceptions import ObjectDoesNotExist


# Native labels keep the selector understandable even before a translation
# catalog is available for the selected language.
SUPPORTED_LANGUAGES = (
    ("en", "English"),
    ("as", "অসমীয়া"),
    ("bn", "বাংলা"),
    ("brx", "बड़ो"),
    ("doi", "डोगरी"),
    ("gu", "ગુજરાતી"),
    ("hi", "हिन्दी"),
    ("kn", "ಕನ್ನಡ"),
    ("ks", "कॉशुर"),
    ("kok", "कोंकणी"),
    ("mai", "मैथिली"),
    ("ml", "മലയാളം"),
    ("mni", "ꯃꯤꯇꯩ ꯂꯣꯟ"),
    ("mr", "मराठी"),
    ("ne", "नेपाली"),
    ("or", "ଓଡ଼ିଆ"),
    ("pa", "ਪੰਜਾਬੀ"),
    ("sa", "संस्कृतम्"),
    ("sat", "ᱥᱟᱱᱛᱟᱲᱤ"),
    ("sd", "سنڌي"),
    ("ta", "தமிழ்"),
    ("te", "తెలుగు"),
    ("ur", "اردو"),
)
SUPPORTED_LANGUAGE_CODES = frozenset(code for code, _label in SUPPORTED_LANGUAGES)
DEFAULT_LANGUAGE = "en"
LANGUAGE_SESSION_KEY = "django_language"
LANGUAGE_FALLBACK_USER_KEY = "sscegov_language_fallback_user"


# CentreUserAccount.state stores the AddState slug in some records and the
# displayed AddState state_name in others. Normalisation lets both forms use
# the same mapping.
STATE_LANGUAGE_MAP = {
    "andhrapradesh": "te",
    "assam": "as",
    "bihar": "hi",
    "chhattisgarh": "hi",
    "chandigarh": "hi",
    "dadraandnagarhavelianddamananddiu": "gu",
    "delhi": "hi",
    "goa": "kok",
    "gujarat": "gu",
    "haryana": "hi",
    "himachalpradesh": "hi",
    "jammuandkashmir": "ks",
    "jharkhand": "hi",
    "karnataka": "kn",
    "kerala": "ml",
    "ladakh": "hi",
    "lakshadweep": "ml",
    "madhyapradesh": "hi",
    "maharashtra": "mr",
    "manipur": "mni",
    "odisha": "or",
    "puducherry": "ta",
    "punjab": "pa",
    "rajasthan": "hi",
    "sikkim": "ne",
    "tamilnadu": "ta",
    "telangana": "te",
    "tripura": "bn",
    "uttarpradesh": "hi",
    "uttarakhand": "hi",
    "westbengal": "bn",
    "andamanandnicobarislands": "hi",
    "default": "hi",
    "hindi": "hi",
    "hindispeaking": "hi",
}


def normalize_state(value):
    """Return a slug-like value for AddState names and stored state slugs."""
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def language_for_state(value):
    """Return the mapped language for a state slug/name, or English fallback."""
    return STATE_LANGUAGE_MAP.get(normalize_state(value), DEFAULT_LANGUAGE)


def franchise_default_language(user):
    """Resolve a centre user's automatic language from CentreUserAccount.state."""
    try:
        state_value = user.centre.state
    except (AttributeError, ObjectDoesNotExist):
        state_value = ""
    return language_for_state(state_value) if normalize_state(state_value) else DEFAULT_LANGUAGE


def user_language(user, session=None):
    """Return the persisted language, or the correct role/state default."""
    if not getattr(user, "is_authenticated", False):
        return DEFAULT_LANGUAGE

    saved_language = getattr(user, "preferred_language", None)
    if saved_language in SUPPORTED_LANGUAGE_CODES:
        return saved_language

    # This is only used when persistence is unavailable (for example, while
    # an older deployment has not yet applied the user-field migration). The
    # user id binding prevents a previous browser user's fallback from leaking
    # into another account.
    if saved_language is None and session is not None:
        fallback_user = session.get(LANGUAGE_FALLBACK_USER_KEY)
        fallback_language = session.get(LANGUAGE_SESSION_KEY)
        if fallback_user == user.pk and fallback_language in SUPPORTED_LANGUAGE_CODES:
            return fallback_language

    if getattr(user, "usertype", None) == "centre":
        return franchise_default_language(user)
    return DEFAULT_LANGUAGE


def is_dashboard_language_user(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "usertype", None) in {"Administrator", "HeadOffice", "centre"}
        )
    )
