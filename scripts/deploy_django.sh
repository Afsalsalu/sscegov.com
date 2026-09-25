#!/usr/bin/env bash
set -Eeuo pipefail

# Run this script on the application server from the repository checkout.
PROJECT_DIRECTORY="${PROJECT_DIRECTORY:-${HOME}/sscegov.com}"
DJANGO_DIRECTORY="${DJANGO_DIRECTORY:-${PROJECT_DIRECTORY}/django}"
VENV_PATH="${VENV_PATH:-${DJANGO_DIRECTORY}/venv}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
APP_SERVICE="${APP_SERVICE:-sscegov-gunicorn.service}"

if [[ ! -d "${PROJECT_DIRECTORY}/.git" ]]; then
    echo "Deployment directory is not a Git checkout: ${PROJECT_DIRECTORY}" >&2
    exit 1
fi
if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
    echo "Django virtualenv Python was not found: ${VENV_PATH}/bin/python" >&2
    exit 1
fi

git -C "${PROJECT_DIRECTORY}" fetch --prune origin "${DEPLOY_BRANCH}"
git -C "${PROJECT_DIRECTORY}" pull --ff-only origin "${DEPLOY_BRANCH}"

cd "${DJANGO_DIRECTORY}"
source "${VENV_PATH}/bin/activate"

python manage.py check
python manage.py migrate --noinput
python manage.py migrate --check
python manage.py collectstatic --noinput

# Fail the deployment if the language source/template/static files did not
# arrive together. This catches stale partial deployments before restart.
test -f web/language.py
test -f templates/web/includes/language_switcher.html
test -f static/web/css/language-switcher.css
test -f assets/web/css/language-switcher.css
grep -q 'data-language-switcher' templates/web/includes/language_switcher.html
grep -q 'onchange="this.form.submit()"' templates/web/includes/language_switcher.html

python manage.py shell -c '
from django.conf import settings
from web.language import SUPPORTED_LANGUAGES
from web.models import AddState

assert settings.USE_I18N is True
assert len(SUPPORTED_LANGUAGES) == 23
assert tuple(settings.LANGUAGES) == tuple(SUPPORTED_LANGUAGES)
assert "django.middleware.locale.LocaleMiddleware" in settings.MIDDLEWARE
assert "web.language_middleware.UserLanguageMiddleware" in settings.MIDDLEWARE
assert {code for code, _label in SUPPORTED_LANGUAGES} >= {"en", "hi", "ml", "ta", "ur"}
assert AddState.objects.filter(slug="kerala").exists(), "Required Kerala state row is missing"
print(f"Verified {len(SUPPORTED_LANGUAGES)} dashboard languages and Kerala state configuration.")
'

if command -v systemctl >/dev/null 2>&1 && systemctl cat "${APP_SERVICE}" >/dev/null 2>&1; then
    sudo -n systemctl restart "${APP_SERVICE}"
    sudo -n systemctl is-active --quiet "${APP_SERVICE}"
elif command -v systemctl >/dev/null 2>&1 && systemctl --user cat "${APP_SERVICE}" >/dev/null 2>&1; then
    systemctl --user restart "${APP_SERVICE}"
    systemctl --user is-active --quiet "${APP_SERVICE}"
else
    echo "Application service ${APP_SERVICE} is not installed." >&2
    echo "Install deploy/sscegov-gunicorn.service once, then rerun this deployment." >&2
    exit 1
fi

echo "Deployed $(git -C "${PROJECT_DIRECTORY}" rev-parse --short HEAD) and restarted ${APP_SERVICE}."
