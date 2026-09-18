#!/bin/bash

PROJECT_DIRECTORY="$HOME/sscegov.com/django/samatwa_pan"
PYENV_ENV="$HOME/.pyenv/versions/pancard-env"
APP_NAME="samatwa_pan.wsgi:application"

cd ${PROJECT_DIRECTORY}

${PYENV_ENV}/bin/gunicorn \
--workers 3 \
--bind unix:${PROJECT_DIRECTORY}/gunicorn.sock \
--umask 0000 \
${APP_NAME}
