#!/usr/bin/env bash

RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
YELLOW="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

export AIRFLOW_DOCKER_IMAGE_NAME="soniaauvets/airflow-ros-tensorflow"
export AIRFLOW_DOCKER_IMAGE_TAG="$(cat VERSION)"

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
DOCKER_DIR="${CURRENT_DIR}/docker"


function error() {
    echo
    echo "${RED}${BOLD}ERROR${RESET}${BOLD} : $1${RESET}"
    echo
    exit 1
}

function collectArgs() {
    BUILD_ENV=$1
    DAGS_DIR=$2

    if [[ -z ${BUILD_ENV} ]]; then
        error "BUILD_ENV argument must be defined on calling ! i.e : ./start.sh [BUILD_ENV]"
    elif [[ "${BUILD_ENV}" -ne "dev" || "${BUILD_ENV}" -ne "prod" ]]; then
        error "BUILD_ENV argument value must be dev or prod"
    fi

    if [[ ! -z $DAGS_DIR ]]; then
        AIRFLOW_DAG_DIR=${DAGS_DIR}
    else
        AIRFLOW_DAG_DIR=$PWD/dags
    fi
}

function checkRequiredFolderExist() {
    declare -a List=(
                 "${CURRENT_DIR}/dags"
                 "${CURRENT_DIR}/data"
                 "${CURRENT_DIR}/logs"
                 "${CURRENT_DIR}/plugins"
                )

    for folder_path in "${List[@]}"
    do
        if [ ! -d ${folder_path} ]; then
            mkdir ${folder_path}
            echo "${folder_path}....${GREEN}${BOLD}CREATED!${GREEN}${BOLD}${RESET}"
        else
            echo "${folder_path}....${GREEN}${BOLD}FOUND!${GREEN}${BOLD}${RESET}"
        fi

    done
}

collectArgs $* || error "Error while defining airflow dags directory"

[ -f .env ] || error "'.env' file does not exist in current directory! ($(pwd))"

docker_status=

if [[ ! "$(docker -v)" ]]; then
     error "You must install docker to be able to use this script"
fi


echo "#########################################################################"
echo
echo
echo "Build context:${BUILD_ENV}"
echo
echo

echo "#########################################################################"
echo
echo "Validating presence of airflow required folder and creating missing folders"
echo
checkRequiredFolderExist ||error "Error while creating folder required by airflow on localhost"
echo
echo

echo ${BUILD_ENV}
if [[ ${BUILD_ENV} == 'prod' ]]; then
    echo "#########################################################################"
    echo
    echo "Generating '${AIRFLOW_DOCKER_IMAGE_NAME}' image using tag '${AIRFLOW_DOCKER_IMAGE_TAG}'"
    docker pull ${AIRFLOW_DOCKER_IMAGE_NAME}:${AIRFLOW_DOCKER_IMAGE_TAG} ||error "Error pulling '${AIRLFLOW_DOCKER_IMAGE_NAME}'"

    echo "#########################################################################"
    echo
    echo "Launching sonia-auv airflow docker containers"
    echo ${CURRENT_DIR}
    AIRFLOW_DAG_DIR=${AIRFLOW_DAG_DIR} HOST_ROOT_FOLDER=${CURRENT_DIR}  docker-compose -f ${DOCKER_DIR}/docker-compose.yml up  -f ${DOCKER_DIR}/docker-compose-prod.yml -d|| error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"
else
    echo "#########################################################################"
    echo
    echo "Launching sonia-auv airflow docker containers"
    echo ${CURRENT_DIR}
    AIRFLOW_DAG_DIR=${AIRFLOW_DAG_DIR} HOST_ROOT_FOLDER=${CURRENT_DIR}  docker-compose -f ${DOCKER_DIR}/docker-compose.yml -f ${DOCKER_DIR}/docker-compose-local.yml up -d|| error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"
fi
echo "#########################################################################"
echo
echo "Airflow containers have ${GREEN}${BOLD}STARTED${GREEN}${BOLD}"
