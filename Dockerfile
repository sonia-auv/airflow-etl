#FROM tensorflow/tensorflow:1.15.2-gpu-py3
FROM tensorflow/tensorflow:1.15.2-gpu-py3

ARG BUILD_DATE
ARG BUILD_ENV
ARG VERSION
ARG SONIA_USER=sonia
ARG SONIA_UID=1000
ARG BASE_LIB_NAME=apache-airflow
ARG DOCKER_GROUP_ID=1000

LABEL maintainer="club.sonia@etsmtl.net"
LABEL description="A docker image of Apache-Airflow an ETL orchestration plateform with additional GPU Support"
LABEL net.etsmtl.sonia-auv.base_lib.build-date=${BUILD_DATE}
LABEL net.etsmtl.sonia-auv.base_lib.version=${VERSION}
LABEL net.etsmtl.sonia-auv.base_lib.name=${BASE_LIB_NAME}


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
ENV TENSORFLOW_OBJECT_DETECTION_HOME=/usr/local/tensorflow/models
ENV TENSORFLOW_OBJECT_DETECTION_RESEARCH=${TENSORFLOW_OBJECT_DETECTION_HOME}/research/
ENV TENSORFLOW_OBJECT_DETECTION_SLIM=${TENSORFLOW_OBJECT_DETECTION_RESEARCH}/slim/
ENV PYTHONPATH=${PYTHONPATH}:${TENSORFLOW_OBJECT_DETECTION_RESEARCH}:${TENSORFLOW_OBJECT_DETECTION_SLIM}
ENV TF_CPP_MIN_LOG_LEVEL 3


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

# Intalling tensorflow object detection framework
RUN apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
    gpg-agent \
    python3-cairocffi \
    protobuf-compiler \
    python3-pil \
    python3-lxml \
    python3-tk \
    && mkdir -p ${TENSORFLOW_OBJECT_DETECTION_HOME} \
    && chown -R airflow: ${TENSORFLOW_OBJECT_DETECTION_HOME} \
    && git clone https://github.com/tensorflow/models.git ${TENSORFLOW_OBJECT_DETECTION_HOME} \
    && (cd ${TENSORFLOW_OBJECT_DETECTION_RESEARCH} && protoc object_detection/protos/*.proto --python_out=.) \
    && cp ${TENSORFLOW_OBJECT_DETECTION_RESEARCH}/object_detection/packages/tf1/setup.py ${TENSORFLOW_OBJECT_DETECTION_RESEARCH} \
    && python ${TENSORFLOW_OBJECT_DETECTION_RESEARCH}/setup.py install \
    && python ${TENSORFLOW_OBJECT_DETECTION_RESEARCH}/object_detection/builders/model_builder_tf1_test.py \
    && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/* \
    /usr/share/man \
    /usr/share/doc \
    /usr/share/doc-base

# Creating airflow logs folder
# Creating SSH folder and adding github to know host
RUN mkdir -p ${AIRFLOW_HOME}/logs \
    && mkdir ${AIRFLOW_HOME}/.ssh/ \
    && ssh-keyscan -H github.com >> ${AIRFLOW_HOME}/.ssh/known_hosts

# ********************************************
# Setting Git
COPY config/.gitconfig ${AIRFLOW_HOME}/.gitconfig
COPY config/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg
COPY config/variables.json ${AIRFLOW_HOME}/variables.json

RUN chown -R airflow: ${AIRFLOW_HOME}

# Copying our docker entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh

EXPOSE 8080

USER airflow
WORKDIR ${AIRFLOW_HOME}
ENTRYPOINT ["/entrypoint.sh"]
