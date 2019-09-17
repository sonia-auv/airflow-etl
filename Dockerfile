# AUTHOR: Martin Gauthier
# DESCRIPTION: Airflow and ROS container
# HIGHLY INSPIRED BY: https://github.com/puckel/docker-airflow

FROM python:3.7-slim-stretch
LABEL maintainer="gauthiermartin86@gmail.com"
LABEL description="This image is an integration of Airflow and ROS"

# *********************************************
# Declaring environements variables

# Never prompts the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Airflow
ARG DOCKER_GROUP_ID=999
ENV AIRFLOW_HOME=/usr/local/airflow


# Define en_US.
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8
ENV LC_MESSAGES en_US.UTF-8

# *********************************************

# Installing google cloud sdk

RUN set -ex \
    && buildDeps=' \
    freetds-dev \
    libkrb5-dev \
    libsasl2-dev \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    git \
    lsb-release \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
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
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    && addgroup --gid ${DOCKER_GROUP_ID} docker \
    && useradd -ms /bin/bash -d ${AIRFLOW_HOME} -G docker airflow \
    && pip install -U pip setuptools wheel \
    && export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update -y && apt-get install google-cloud-sdk -y \
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

# *********************************************
# Creating airflow logs folder
RUN mkdir -p ${AIRFLOW_HOME}/logs
RUN mkdir -p ${AIRFLOW_HOME}/.config/gcloud/

# *********************************************
#Copying our airflow config and setting ownership
COPY config/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg
RUN chown -R airflow: ${AIRFLOW_HOME}

# Copying our docker entrypoint
COPY script/entrypoint.sh /entrypoint.sh

EXPOSE 8080
# 5555 8793

USER airflow
WORKDIR ${AIRFLOW_HOME}
ENTRYPOINT ["/entrypoint.sh"]
