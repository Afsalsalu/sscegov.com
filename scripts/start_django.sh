#!/bin/bash

#PROJECT_DIRECTORY="$HOME/sscegov.com//django";
#VENV_PATH="${PROJECT_DIRECTORY}/venv";
#APP_NAME="ssc.wsgi:application"


#source ${VENV_PATH}/bin/activate; 
#cd ${PROJECT_DIRECTORY};

#${VENV_PATH}/bin/gunicorn -b unix:${PROJECT_DIRECTORY}/gunicorn.sock ${APP_NAME}

#!/bin/bash

PROJECT_DIRECTORY="$HOME/sscegov.com/django"
VENV_PATH="${PROJECT_DIRECTORY}/venv"
APP_NAME="ssc.wsgi:application"
LOG_DIR="$HOME/sscegov.com/logs"

mkdir -p ${LOG_DIR}

source ${VENV_PATH}/bin/activate
cd ${PROJECT_DIRECTORY}

${VENV_PATH}/bin/gunicorn \
--workers 3 \
--bind unix:${PROJECT_DIRECTORY}/gunicorn.sock \
--log-level debug \
--access-logfile ${LOG_DIR}/gunicorn_access.log \
--error-logfile ${LOG_DIR}/gunicorn_error.log \
${APP_NAME}

