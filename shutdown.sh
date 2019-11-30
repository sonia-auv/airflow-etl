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
#   $ chmod u+x shutdown.sh && ./shutdown.sh
#
# Options:
#   -h, --help      output program instructions
#   -v, --version   output program version
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
PROGRAM="shutdown"

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

e_airflow_container_shutting_down(){
    echo "#########################################################################"
    echo
    echo "Shutting down sonia-auv aiflow docker containers"
}

e_airflow_container_shutted_down(){
    echo "#########################################################################"
    echo
    echo "Airflow containers have ${RED}${BOLD}STOPPED${RED}${BOLD}"
}

# ------------------------------------------------------------------------------
# | MAIN FUNCTIONS                                                             |
# ------------------------------------------------------------------------------

help() {

cat <<EOT

------------------------------------------------------------------------------
Shutdown - DESCRIPTION
------------------------------------------------------------------------------

Usage: ./shutdown.sh
Example: ./shutdown.sh


Options:
    -h, --help      output program instructions
    -v, --version   output program version
    -e, --env       set build environment variable (e.g: dev, prod)

EOT

}

shutdown() {
   e_airflow_container_shutting_down
   IRFLOW_DAG_DIR=${AIRFLOW_DAG_DIR} HOST_ROOT_FOLDER=${CURRENT_DIR} docker-compose -f ${DOCKER_DIR}/docker-compose.yml down || e_error "Error while shutting down sonia-auv airflow docker containers"
    e_airflow_container_shutted_down
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
    else
        shutdown
    fi

}

# Initialize
main $*
