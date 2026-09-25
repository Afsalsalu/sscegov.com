#!/usr/bin/env bash
set -Eeuo pipefail

# Canonical Gunicorn entrypoint for the main Django application.
# Override these values only when the deployment layout differs.
PROJECT_DIRECTORY="${PROJECT_DIRECTORY:-${HOME}/sscegov.com/django}"
VENV_PATH="${VENV_PATH:-${PROJECT_DIRECTORY}/venv}"
GUNICORN_BIND="${GUNICORN_BIND:-unix:${PROJECT_DIRECTORY}/gunicorn.sock}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_UMASK="${GUNICORN_UMASK:-0000}"

cd "${PROJECT_DIRECTORY}"
exec "${VENV_PATH}/bin/gunicorn" \
    --chdir "${PROJECT_DIRECTORY}" \
    --workers "${GUNICORN_WORKERS}" \
    --bind "${GUNICORN_BIND}" \
    --umask "${GUNICORN_UMASK}" \
    --access-logfile - \
    --error-logfile - \
    ssc.wsgi:application

