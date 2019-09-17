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

with DAG("extract_image_from_ros_bag", catchup=False, default_args=default_args) as dag:

    formated_topics = " ".join(TOPICS)

    detect_bag = PythonOperator(
        task_id="detect_bag",
        python_callable=extract_img_from_ros_bag.bag_file_exists,
        op_kwargs={"bag_path": BAG_FOLDER},
        trigger_rule="all_success",
        dag=dag,
    )

    bag_filename_syntax_matches_format = PythonOperator(
        task_id="bag_filename_syntax_matches_format",
        python_callable=extract_img_from_ros_bag.bag_filename_syntax_valid,
        op_kwargs={"bag_path": BAG_FOLDER},
        trigger_rule="all_success",
        dag=dag,
    )

    extract_image_command = f"python cli.py --media image --topics {formated_topics}"

    extract_images_from_bag = DockerOperator(
        task_id="extract_images_from_bag",
        image="soniaauvets/ros-bag-extractor:1.1.6",
        force_pull=True,
        auto_remove=True,
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

    notify_extraction_success = slack.dag_notify_success_slack_alert(dag=dag)

    detect_bag >> bag_filename_syntax_matches_format >> extract_images_from_bag >> notify_extraction_success
