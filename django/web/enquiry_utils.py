import re
from urllib.parse import urlencode

from django.conf import settings


def get_support_whatsapp_url():
    """Return a safe wa.me URL for a configured international support number."""
    raw_number = (getattr(settings, "SUPPORT_WHATSAPP_NUMBER", "") or "").strip()
    if not raw_number or not re.fullmatch(r"\+?[0-9\s().-]+", raw_number):
        return ""

    number = re.sub(r"\D", "", raw_number)
    if not 8 <= len(number) <= 15:
        return ""

    text = urlencode({"text": "Hello, I need support with my franchise account."})
    return f"https://wa.me/{number}?{text}"
