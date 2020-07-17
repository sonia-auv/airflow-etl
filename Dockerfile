# AUTHOR: Martin Gauthier
# DESCRIPTION: Airflow container image
# HIGHLY INSPIRED BY: https://github.com/puckel/docker-airflow
FROM tensorflow/tensorflow:1.15.2-gpu-py3

ARG BUILD_DATE
ARG BUILD_ENV
ARG VERSION
ARG SONIA_USER=sonia
ARG SONIA_UID=50000
ARG BASE_LIB_NAME=apache-airflow
ARG DOCKER_GROUP_ID=999

LABEL maintainer="club.sonia@etsmtl.net"
LABEL description="A docker image of Airflow an ETL orchestration plateform with GPU Support"
LABEL net.etsmtl.sonia-auv.base_lib.build-date=${BUILD_DATE}
LABEL net.etsmtl.sonia-auv.base_lib.version=${VERSION}
LABEL net.etsmtl.sonia-auv.base_lib.name=${BASE_LIB_NAME}

# Declaring environements variables
# Never prompts the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Define en_US.
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8
ENV LC_MESSAGES en_US.UTF-8

ENV AIRFLOW_HOME=/usr/local/airflow

# Tensorflow object detection
ARG PROTOC_VERSION=3.10.1
ARG PROTOC_ZIP=protoc-${PROTOC_VERSION}-linux-x86_64.zip
ARG TENSORFLOW_OBJ_DETECTION_VERSION=1.13.0
ARG TENSORFLOW_OBJECT_DETECTION_LIB_PATH=${AIRFLOW_HOME}/models-${TENSORFLOW_OBJ_DETECTION_VERSION}/research/
ARG TENSORFLOW_OBJECT_DETECTION_SLIM_PATH=${AIRFLOW_HOME}/models-${TENSORFLOW_OBJ_DETECTION_VERSION}/research/slim

ENV PROTOC_VERSION=${PROTOC_VERSION}
ENV TENSORFLOW_OBJECT_DETECTION_VERSION=${TENSORFLOW_OBJ_DETECTION_VERSION}
ENV TENSORFLOW_OBJECT_DETECTION_BASE_FOLDER=${AIRFLOW_HOME}/models-${TENSORFLOW_OBJECT_DETECTION_VERSION}
ENV TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER=${AIRFLOW_HOME}/models-${TENSORFLOW_OBJECT_DETECTION_VERSION}/research/

RUN set -ex \
    && buildDeps=' \
    freetds-dev \
    libkrb5-dev \
    libsasl2-dev \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    unzip \
    wget \
    lsb-release \
    gnupg2 \
    software-properties-common \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
    $buildDeps \
    freetds-bin \
    build-essential \
    default-libmysqlclient-dev \
    apt-utils \
    curl \
    rsync \
    netcat \
    locales \
    git \
    ssh-client\
    ca-certificates \
    apt-transport-https \
    libglib2.0-0 \
    libsm6 \
    libfontconfig1 \
    libxrender1 \
    libxext6 \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    && addgroup --gid ${DOCKER_GROUP_ID} docker \
    && useradd -ms /bin/bash -d ${AIRFLOW_HOME} -G docker airflow \
    && pip install -U pip setuptools wheel \
    && apt-get purge --auto-remove -yqq $buildDeps \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/* \
    /usr/share/man \
    /usr/share/doc \
    /usr/share/doc-base

# Installing Airflow and other pythons requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Installing protobuf (Binary serialization) required for tfrecord creation
RUN set -ex \
    && buildDeps=' \
    unzip \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
    $buildDeps \
    && curl -OL https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/${PROTOC_ZIP} \
    && unzip -o ${PROTOC_ZIP} -d /usr/local bin/protoc \
    && unzip -o ${PROTOC_ZIP} -d /usr/local 'include/*' \
    && rm -f ${PROTOC_ZIP}\
    && apt-get purge --auto-remove -yqq $buildDeps\
    && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/* \
    /usr/share/man \
    /usr/share/doc \
    /usr/share/doc-base

# Intalling tensorflow object detection framework
RUN set -ex \
    && buildDeps=' \
    wget \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
    $buildDeps \
    && wget -q -c https://github.com/tensorflow/models/archive/v${TENSORFLOW_OBJECT_DETECTION_VERSION}.tar.gz -O - | tar -xz -C ${AIRFLOW_HOME} \
    && cd ${AIRFLOW_HOME}/models-${TENSORFLOW_OBJECT_DETECTION_VERSION}/research/ \
    && chmod +x object_detection/dataset_tools/create_pycocotools_package.sh \
    && protoc object_detection/protos/*.proto --python_out=. \
    && apt-get purge --auto-remove -yqq $buildDeps\
    && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/* \
    /usr/share/man \
    /usr/share/doc \
    /usr/share/doc-base

# Add tensorflow object detection to python path
ENV PYTHONPATH=${PYTHONPATH}:${TENSORFLOW_OBJECT_DETECTION_LIB_PATH}:${TENSORFLOW_OBJECT_DETECTION_SLIM_PATH}


# Creating airflow logs folder
RUN mkdir -p ${AIRFLOW_HOME}/logs
RUN mkdir -p ${AIRFLOW_HOME}/.config/gcloud/

# Creating SSH folder and adding github to know host
RUN mkdir ${AIRFLOW_HOME}/.ssh/ \
    && ssh-keyscan -H github.com >> ${AIRFLOW_HOME}/.ssh/known_hosts

# ********************************************
# Setting Git
COPY config/.gitconfig ${AIRFLOW_HOME}/.gitconfig

#Copying our airflow config and setting ownership
COPY config/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg
COPY config/variables.json ${AIRFLOW_HOME}/variables.json
RUN chown -R airflow: ${AIRFLOW_HOME}

# Copying our docker entrypoint
COPY script/entrypoint.sh /entrypoint.sh

EXPOSE 8080

USER airflow
WORKDIR ${AIRFLOW_HOME}
ENTRYPOINT ["/entrypoint.sh"]
