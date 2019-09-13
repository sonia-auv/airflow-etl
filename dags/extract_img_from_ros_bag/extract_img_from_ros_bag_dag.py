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

task_notify_start = SlackWebhookOperator(
    task_id="task_notify_start",
    http_conn_id='slack',
    webhook_token=slack_webhook_token,
    username='airflow',
    message=" :dolphin:[PROCESSING] DAG (extract_image_from_bag): Extract images from ROS bag",
    dag=dag,
)

task_detect_bag = BranchPythonOperator(
    task_id="task_detect_bag",
    python_callable=extract_img_from_ros_bag.bag_file_exists,
    op_kwargs={"bags_path": BAG_FOLDER},
    trigger_rule="all_success",
    provide_context=True,
    dag=dag,
)

task_bag_not_detected = PythonOperator(
    task_id="task_bag_not_detected",
    python_callable=extract_img_from_ros_bag.bag_not_detected,
    op_kwargs={"bags_path": BAG_FOLDER},
    provide_context=True,
    dag=dag,
)

task_notify_file_with_ext_failure = SlackWebhookOperator(
    task_id="task_notify_file_with_ext_failure",
    http_conn_id='slack',
    webhook_token=slack_webhook_token,
    username='airflow',
    message=":heavy_multiplication_x: [FAILURE] DAG (extract_image_from_ros_bag): No bag file detected in".format(
        BAG_FOLDER),
    provide_context=True,
    dag=dag,
)

task_extract_images_from_bag = DockerOperator(
    task_id="task_extract_images_from_bag",
    image="soniaauvets/ros-bag-extractor:1.0.0",
    force_pull=True,
    command="python cli.py --type image --topics {{ formated_topics }}",
    api_version="auto",
    docker_url='unix://var/run/docker.sock',
    volumes=['/usr/local/airflow/data/bags/:/home/sonia/bags',
             '/usr/local/airflow/data/images/:/home/sonia/images'],
    network_mode='bridge',
    provide_context=True,
    dag=dag,
)

task_notify_extraction_success = SlackWebhookOperator(
    task_id="task_notify_extraction_success",
    http_conn_id='slack',
    webhook_token=slack_webhook_token,
    username='airflow',
    message=":heavy_check_mark: [SUCCESS] DAG (extract_image_from_ros_bag): Images were successfully extracted from ROS bag",
    trigger_rule="all_success",
    provide_context=True,
    dag=dag,
)

task_notify_start.set_downstream(task_detect_bag)
task_detect_bag.set_downstream(task_bag_not_detected)
task_detect_bag.set_downstream(task_extract_images_from_bag)
task_bag_not_detected.set_downstream(task_notify_file_with_ext_failure)
task_extract_images_from_bag.set_downstream(task_notify_extraction_success)
