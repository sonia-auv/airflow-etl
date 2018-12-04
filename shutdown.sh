#!/usr/bin/env bash

RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
YELLOW="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

export AIRFLOW_DOCKER_IMAGE_NAME="sonia-auv/airflow"
export AIRFLOW_DOCKER_IMAGE_TAG="local"

function error() {
    echo
    echo "${RED}${BOLD}ERROR${RESET}${BOLD} : $1${RESET}"
    echo
    exit 1
}

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
DOCKER_DIR="${CURRENT_DIR}/docker"

echo "#########################################################################"
echo
echo "Shutting down sonia-auv aiflow docker containers"

docker-compose -f ${DOCKER_DIR}/docker-compose.yml down || error "Error while shutting down sonia-auv airflow docker containers"


echo "#########################################################################"
echo
echo "Airflow containers have ${RED}${BOLD}STOPPED${RED}${BOLD}"
