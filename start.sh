#!/usr/bin/env bash

RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
YELLOW="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

export AIRFLOW_DOCKER_IMAGE_NAME="soniaauvets/airflow-ros-tensorflow"
export AIRFLOW_DOCKER_IMAGE_TAG="1.1.3"

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
DOCKER_DIR="${CURRENT_DIR}/docker"


function error() {
    echo
    echo "${RED}${BOLD}ERROR${RESET}${BOLD} : $1${RESET}"
    echo
    exit 1
}

function collectArgs() {
    DAGS_DIR=$1

    if [[ ! -z $DAGS_DIR ]]; then
        AIRFLOW_DAG_DIR=${DAGS_DIR}
    else
        AIRFLOW_DAG_DIR=$PWD/dags
    fi
}

collectArgs $* || error "Error while defining airflow dags directory"

[ -f .env ] || error "'.env' file does not exist in current directory! ($(pwd))"

docker_status=

if [[ ! "$(docker -v)" ]]; then
     error "You must install docker to be able to use this script"
fi

echo "#########################################################################"
echo
echo " Generating '${AIRFLOW_DOCKER_IMAGE_NAME}' image using tag '${AIRFLOW_DOCKER_IMAGE_TAG}'"
docker pull ${AIRFLOW_DOCKER_IMAGE_NAME}:${AIRFLOW_DOCKER_IMAGE_TAG} ||error "Error pulling '${AIRLFLOW_DOCKER_IMAGE_NAME}'"


echo "#########################################################################"
echo
echo "Launching sonia-auv airflow docker containers"
AIRFLOW_DAG_DIR=${AIRFLOW_DAG_DIR} docker-compose -f ${DOCKER_DIR}/docker-compose.yml up -d|| error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"


echo "#########################################################################"
echo
echo "Airflow containers have ${GREEN}${BOLD}STARTED${GREEN}${BOLD}"
