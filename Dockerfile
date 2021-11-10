FROM tensorflow/tensorflow:1.15.2-gpu-py3

ARG BUILD_DATE
ARG BUILD_ENV
ARG VERSION
ARG SONIA_USER=airflow
ARG SONIA_UID=1000
ARG BASE_LIB_NAME=apache-airflow
ARG DOCKER_GROUP_ID=999

LABEL maintainer="club.sonia@etsmtl.net"
LABEL description="A docker image of Apache-Airflow an ETL orchestration plateform with additional GPU Support"
LABEL net.etsmtl.sonia-auv.base_lib.build-date=${BUILD_DATE}
LABEL net.etsmtl.sonia-auv.base_lib.version=${VERSION}
LABEL net.etsmtl.sonia-auv.base_lib.name=${BASE_LIB_NAME}


# Never prompts the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive

# Making sure language variable are set
ENV LANGUAGE=C.UTF-8 LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    LC_CTYPE=C.UTF-8 LC_MESSAGES=C.UTF-8

ENV AIRFLOW_HOME=/home/${SONIA_USER}
ENV TENSORFLOW_OBJECT_DETECTION_HOME=/home/${SONIA_USER}/tensorflow/models
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
    python-minimal \
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
    && addgroup --gid ${DOCKER_GROUP_ID} docker \
    && useradd -ms /bin/bash -G docker ${SONIA_USER} \
    && pip install -U  pip setuptools wheel \
    && export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update -y && apt-get install google-cloud-sdk   -y \
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
    python3-sqlalchemy \
    python3-cairocffi \
    protobuf-compiler \
    python3-pil \
    python3-tk \
    python3-opencv \
    && pip install opencv-python \
    && mkdir -p ${TENSORFLOW_OBJECT_DETECTION_HOME} \
    && chown -R airflow: ${TENSORFLOW_OBJECT_DETECTION_HOME} \
    && git clone https://github.com/tensorflow/models.git ${TENSORFLOW_OBJECT_DETECTION_HOME} \
    && (cd ${TENSORFLOW_OBJECT_DETECTION_RESEARCH} && protoc object_detection/protos/*.proto --python_out=.) \
    && (cd ${TENSORFLOW_OBJECT_DETECTION_RESEARCH} && cp object_detection/packages/tf1/setup.py ./) \
    && (cd ${TENSORFLOW_OBJECT_DETECTION_RESEARCH} && python -m pip install .) \
    && python ${TENSORFLOW_OBJECT_DETECTION_RESEARCH}/object_detection/builders/model_builder_tf1_test.py \
    && chmod +x ${TENSORFLOW_OBJECT_DETECTION_RESEARCH}/object_detection/dataset_tools/create_pycocotools_package.sh \
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

USER ${SONIA_USER}
WORKDIR ${AIRFLOW_HOME}
ENTRYPOINT ["/entrypoint.sh"]
