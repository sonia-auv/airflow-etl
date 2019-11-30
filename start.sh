#!/usr/bin/env bash

# -- ABOUT THIS PROGRAM: ------------------------------------------------------
#
# Author:       Martin Gauthier
# Version:      1.0.0
# Description:  A simple shell script to launch our Airflow services
# Source:       https://github.com/sonia-auv/docker-ros-airflow/start.sh
#
# -- INSTRUCTIONS: ------------------------------------------------------------
#
# Execute:
#   $ chmod u+x start.sh && ./start.sh --env dev
#
# Options:
#   -h, --help      output program instructions
#   -v, --version   output program version
#   -e, --env       set build environment variable (e.g: dev, prod)
#
# ------------------------------------------------------------------------------
# | VARIABLES                                                                  |
# ------------------------------------------------------------------------------

RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
YELLOW="$(tput setaf 3)"
ORANGE='\033[0;33m'
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

VERSION="1.0.0"
PROGRAM="start"

export AIRFLOW_DOCKER_IMAGE_NAME="soniaauvets/airflow-ros-tensorflow"
export AIRFLOW_DOCKER_IMAGE_TAG="$(cat VERSION)"
AIRFLOW_DAG_DIR=$PWD/dags

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
DOCKER_DIR="${CURRENT_DIR}/docker"

# ------------------------------------------------------------------------------
# | UTILS                                                                      |
# ------------------------------------------------------------------------------

# Header logging
e_info() {
    echo "${YELLOW}[INFO]:${RESET}" "$@"
}

# Success logging
e_success() {
    echo "${GREEN}✔${RESET}" "$@"
}

# Error logging
e_error() {
    echo "${RED}[ERROR]:${RESET}" "$@"
    exit 1
}

# Warning logging
e_warning() {
    printf "${ORANGE}![WARNING]:${RESET}" "$@"
}

e_airflow_container_starting() {
    echo "#########################################################################"
    echo
    e_success "Launching sonia-auv airflow docker containers"
}

e_airflow_container_started() {
    echo "#########################################################################"
    echo
    e_success "Airflow containers have ${GREEN}${BOLD}STARTED${GREEN}${BOLD}"
}

e_airflow_image_pulling() {
    echo "#########################################################################"
    echo
    e_success "Pulling image '${AIRFLOW_DOCKER_IMAGE_NAME}' using tag '${AIRFLOW_DOCKER_IMAGE_TAG}'"
}

# ------------------------------------------------------------------------------
# | MAIN FUNCTIONS                                                             |
# ------------------------------------------------------------------------------

context(){
    e_info "Build context:${BUILD_ENV}"
}

help() {

cat <<EOT

------------------------------------------------------------------------------
Start - DESCRIPTION
------------------------------------------------------------------------------

Usage: ./start.sh
Example: ./start.sh


Options:
    -h, --help      output program instructions
    -v, --version   output program version
    -e, --env       set build environment variable (e.g: dev, prod)

EOT

}

parseArgs() {
    BUILD_ENV=${1}
    if [[ -z ${BUILD_ENV} ]]; then
        e_error "BUILD_ENV argument must be defined on calling ! i.e : ./start.sh [BUILD_ENV]"
    elif [[ "${BUILD_ENV}" -ne "dev" || "${BUILD_ENV}" -ne "prod" ]]; then
        e_error "BUILD_ENV argument value must be dev or prod"
    fi
}

requiredFolderExist() {
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

start(){
    parseArgs $*
    context
    requiredFolderExist || e_error "Error while creating folder required by airflow on localhost"
    if [[ ${BUILD_ENV} == 'prod' ]]; then
        start_prod || e_error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"
    else
        start_dev || e_error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"
    fi

    e_airflow_container_started
}

start_dev() {
    e_airflow_container_starting
    AIRFLOW_DAG_DIR=${AIRFLOW_DAG_DIR} HOST_ROOT_FOLDER=${CURRENT_DIR}  docker-compose -f ${DOCKER_DIR}/docker-compose.yml -f ${DOCKER_DIR}/docker-compose-local.yml up -d || e_error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"
}

start_prod() {
    e_airflow_image_pulling
    docker pull ${AIRFLOW_DOCKER_IMAGE_NAME}:${AIRFLOW_DOCKER_IMAGE_TAG} ||e_error "Error pulling '${AIRLFLOW_DOCKER_IMAGE_NAME}'"

    e_airflow_container_starting
    AIRFLOW_DAG_DIR=${AIRFLOW_DAG_DIR} HOST_ROOT_FOLDER=${CURRENT_DIR}  docker-compose -f ${DOCKER_DIR}/docker-compose.yml -f ${DOCKER_DIR}/docker-compose-prod.yml up -d|| e_error "Error while starting '${AIRFLOW_DOCKER_IMAGE_NAME}'"
}

version() {
    echo "$PROGRAM: v$VERSION"
}

# ------------------------------------------------------------------------------
# | INITIALIZE SCRIPT                                                          |
# ------------------------------------------------------------------------------

main() {

    if [[ "${1}" == "-h" || "${1}" == "--help" ]]; then
        help ${1}
    elif [[ "${1}" == "-v" || "${1}" == "--version" ]]; then
        version ${1}
    elif [[ "${1}" == "-e" || "${1}" == "--env" ]]; then
        start ${2}
    else
        e_error "You must provide an build enviroment using the -e or --env flag"
    fi

}

# Initialize
main $*
