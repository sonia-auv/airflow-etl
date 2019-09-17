"""
 This DAG will handle images extraction from multiple ROS bag
"""

import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator

from extract_img_from_ros_bag import extract_img_from_ros_bag
from utils import file_ops
from utils import slack

ROOT_FOLDER = "/usr/local/airflow/data/"
BAG_FOLDER = os.path.join(ROOT_FOLDER, "bags")
IMAGE_FOLDER = os.path.join(ROOT_FOLDER, "images")
TOPICS = ["/provider_vision/Front_GigE/compressed",
          "/provider_vision/Bottom_GigE/compressed"]

slack_webhook_token = BaseHook.get_connection('slack').password
formated_topics = " ".join(TOPICS)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "schedule_interval": None,
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": slack.task_fail_slack_alert,
    "retries": 0,
}

dag = DAG("extract_image_from_ros_bag",
          catchup=False, default_args=default_args)

task_notify_start = slack.dag_notify_start_slack_alert(dag=dag)

task_detect_bag = PythonOperator(
    task_id="task_detect_bag",
    python_callable=extract_img_from_ros_bag.bag_file_exists,
    op_kwargs={"bag_path": BAG_FOLDER},
    trigger_rule="all_success",
    dag=dag,
)

extract_image_command = f"python cli.py --media image --topics {formated_topics}"

task_extract_images_from_bag = DockerOperator(
    task_id="task_extract_images_from_bag",
    image="soniaauvets/ros-bag-extractor:1.0.4",
    force_pull=False,
    command=extract_image_command,
    api_version="1.37",
    docker_url='unix://var/run/docker.sock',
    volumes=['/home/parallels/Projects/docker-ros-airflow/data/bags:/home/sonia/bags',
             '/home/parallels/Projects/docker-ros-airflow/data/images/:/home/sonia/images',
             ],
    network_mode='bridge',
    provide_context=True,
    trigger_rule="all_success",
    dag=dag,
)

task_notify_extraction_success = slack.dag_notify_success_slack_alert(dag=dag)

task_notify_start >> task_detect_bag >> task_extract_images_from_bag >> task_notify_extraction_success
