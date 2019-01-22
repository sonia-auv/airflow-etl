# VERSION 0.0.1
# AUTHOR: Martin Gauthier
# DESCRIPTION: Airflow and ROS container
# HIGHLY INSPIRED BY: https://github.com/puckel/docker-airflow

FROM osrf/ros:melodic-desktop-bionic
LABEL version="1.1.3"
LABEL maintainer="gauthiermartin86@gmail.com"
LABEL description="This image is an integration of Airflow and ROS"

# *********************************************
# Declaring environements variables

# Never prompts the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Define Airflow specific environements var
ENV AIRFLOW_HOME=/usr/local/airflow
ENV SLUGIFY_USES_TEXT_UNIDECODE=yes

# *********************************************
# Creating airflow logs folder
WORKDIR /tmp
COPY requirements.txt requirements.txt

## Installing Airflow
RUN set -ex \
    && buildDeps=' \
    python-dev \
    libkrb5-dev \
    libsasl2-dev \
    libssl-dev \
    libffi-dev \
    build-essential \
    libblas-dev \
    liblapack-dev \
    libpq-dev \
    git \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
    $buildDeps \
    python-pip \
    python-requests \
    apt-utils \
    curl \
    openssh-client \
    rsync \
    netcat \
    locales \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    && useradd -ms /bin/bash -d ${AIRFLOW_HOME} airflow \
    && pip install setuptools wheel \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/* \
    /usr/share/man \
    /usr/share/doc \
    /usr/share/doc-base

# Installing google cloud sdk
RUN export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" && \
    echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update -y && apt-get install google-cloud-sdk -y

# *********************************************
# Creating airflow logs folder
RUN mkdir ${AIRFLOW_HOME}/logs
RUN mkdir -p ${AIRFLOW_HOME}/.config/gcloud/

# *********************************************
#Copying our airflow config and setting ownership
COPY config/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg
# COPY config/webserver_config.py ${AIRFLOW_HOME}/webserver_config.py
RUN chown -R airflow: ${AIRFLOW_HOME}

# *********************************************
# Copying our docker entrypoint
COPY script/entrypoint.sh /entrypoint.sh

EXPOSE 8080 5555 8793

USER airflow
WORKDIR ${AIRFLOW_HOME}
ENTRYPOINT ["/entrypoint.sh"]
