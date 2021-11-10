"""
 This DAG will handle images extraction from multiple ROS bag
"""

import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from docker.types import Mount

from extract_img_from_ros_bag import extract_img_from_ros_bag
from utils import file_ops
from utils import slack


HOST_ROOT_FOLDER = os.environ["HOST_ROOT_FOLDER"]
BASE_DATA_FOLDER = "/data/"
BASE_AIRFLOW_FOLDER = "/home/airflow"
BAG_FOLDER = BASE_AIRFLOW_FOLDER + BASE_DATA_FOLDER + "bags"
HOST_DIR_BAG_FOLDER = HOST_ROOT_FOLDER + BASE_DATA_FOLDER + "bags"
HOST_DIR_IMAGE_FOLDER = HOST_ROOT_FOLDER + BASE_DATA_FOLDER + "images"

BAG_EXTENSION = ".bag"
TOPICS = ["/camera_array/front/image_raw/compressed", "/camera_array/bottom/image_raw/compressed"]

slack_webhook_token = BaseHook.get_connection("slack").password


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "schedule_interval": "None",
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": slack.task_fail_slack_alert,
    "retries": 0,
}

with DAG(
    "1-extract_image_from_ros_bag", default_args=default_args, catchup=False, schedule_interval=None,
) as dag:

    formated_topics = " ".join(TOPICS)

    detect_bag = PythonOperator(
        task_id="detect_bag",
        python_callable=extract_img_from_ros_bag.bag_file_exists,
        op_kwargs={"bag_path": BAG_FOLDER},
        trigger_rule="all_success",
        dag=dag,
    )

    extract_image_command = f"python cli.py --media image --topics {formated_topics}"

    extract_images_from_bag = DockerOperator(
        task_id="extract_images_from_bag",
        image="soniaauvets/ros-bag-extractor:1.1.7",
        force_pull=True,
        auto_remove=True,
        command=extract_image_command,
        api_version="1.37",
        docker_url="unix://var/run/docker.sock",
        mounts=[
            Mount(source=HOST_DIR_BAG_FOLDER, target="/home/sonia/bags", type="bind"),
            Mount(source=HOST_DIR_IMAGE_FOLDER, target="/home/sonia/images", type="bind"),
        ],
        network_mode="bridge",
        trigger_rule="all_success",
        dag=dag,
    )

    remove_bag_after_extract = BashOperator(
        task_id="remove_bag_after_extract",
        bash_command=f"rm -rf {BAG_FOLDER}/*",
        trigger_rule="all_success",
        dag=dag,
    )

    detect_bag >> extract_images_from_bag >> remove_bag_after_extract
