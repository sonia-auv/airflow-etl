#!/usr/bin/env bash

RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
YELLOW="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

export AIRFLOW_DOCKER_IMAGE_NAME="sonia-auv/airflow"
export AIRFLOW_DOCKER_IMAGE_TAG="local"

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
DOCKER_DIR="${CURRENT_DIR}/docker"


function error() {
    echo
    echo "${RED}${BOLD}ERROR${RESET}${BOLD} : $1${RESET}"
    echo
    exit 1
}

function collectArgs() {
    DAGS_DIR = $1

    if [-f ${DAGS_DIR}]; then
        AIRFLOW_DAG_DIR=DAG_DIR
    else
        AIRFLOW_DAG_DIR=${CURRENT_DIR}/dags
    fi

}


if [! -f .env]; then
    error "'.env' file does not exist in current directory! ($(pwd))"
fi

echo "#########################################################################"
echo
echo " Generating '${AIRFLOW_DOCKER_IMAGE_NAME}' image using tag '${AIRFLOW_DOCKER_IMAGE_TAG}'"
docker build . -t ${AIRFLOW_DOCKER_IMAGE_NAME}:${AIRFLOW_DOCKER_IMAGE_TAG} ||error "Error building '${AIRLFLOW_DOCKER_IMAGE_NAME}'"

echo "#########################################################################"
echo
echo "Launching sonia-auv airflow docker containers"
AIRFLOW_DAGS_DIR=${AIRLFLOW_DAGS_DIR} docker-compose -f ${DOCKER_DIR}/docker-compose.yml up -d || error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"


echo "#########################################################################"
echo
echo "Airflow containers have ${GREEN}${BOLD}STARTED${GREEN}${BOLD}"
