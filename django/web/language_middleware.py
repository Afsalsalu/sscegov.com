from django.utils import translation

from .language import user_language


class UserLanguageMiddleware:
    """Apply each authenticated user's persisted/default language per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            language = user_language(user, getattr(request, "session", None))
            translation.activate(language)
            request.LANGUAGE_CODE = language
        return self.get_response(request)
