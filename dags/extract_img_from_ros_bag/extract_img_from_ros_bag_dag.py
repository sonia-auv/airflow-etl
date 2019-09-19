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

HOST_ROOT_FOLDER = os.environ['HOST_DIR']
DATA_FOLDER = "/data/"
DOCKER_ROOT_FOLDER = "/usr/local/airflow"
DOCKER_BAG_FOLDER = os.path.join(DOCKER_ROOT_FOLDER, DATA_FOLDER, "bags")
DOCKER_IMAGE_FOLDER = os.path.join(DOCKER_ROOT_FOLDER, DATA_FOLDER, "images")
HOST_DIR_BAG_FOLDER = os.path.join(HOST_ROOT_FOLDER, DATA_FOLDER, "bags")
HOST_DIR_IMAGE_FOLDER = os.path.join(HOST_ROOT_FOLDER, DATA_FOLDER, "images")
BAG_EXTENSION = ".bag"
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


def create_subdag(bag_path, index, default_args):
    dag = DAG(f"extract_image_from_ros_bag_{index}",
              catchup=False, default_args=default_args)

    extract_image_command = f"python cli.py --media image --topics {formated_topics}"
    bag_filename = file_ops.get_filename(bag_path)

    extract_images_from_bag = DockerOperator(
        task_id="extract_images_from_bag",
        image="soniaauvets/ros-bag-extractor:1.1.6",
        force_pull=True,
        auto_remove=True,
        command=extract_image_command,
        api_version="1.37",
        docker_url='unix://var/run/docker.sock',
        volumes=[
            f"{HOST_DIR_BAG_FOLDER}/{bag_filename}:/home/sonia/bags/{bag_filename}",
            f"{HOST_DIR_IMAGE_FOLDER}:/home/sonia/images",
        ],
        network_mode='bridge',
        provide_context=True,
        trigger_rule="all_success",
        dag=dag,
    )


with DAG("extract_image_from_ros_bag", catchup=False, default_args=default_args) as dag:

    formated_topics = " ".join(TOPICS)

    dynamic_task_list = []

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

    bags_path = file_ops.get_files_in_directory(
        BAG_FOLDER, BAG_EXTENSION)

    for index, image_path in enumerate(bags_path):
        sub_dag = create_subdag(image_path, index)

        task_list.append(sub_dag)

    notify_extraction_success = slack.dag_notify_success_slack_alert(dag=dag)

    detect_bag >> bag_filename_syntax_matches_format >> dynamic_task_list >> notify_extraction_success
