"""
 This DAG will handle images extraction from multiple ROS bag
"""

import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable

from extract_img_from_ros_bag import extract_img_from_ros_bag
from utils import file_ops

ROOT_FOLDER = "/usr/local/airflow/data/"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "schedule_interval": None,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

with DAG("extract_image_from_ros_bag", catchup=False, default_args=default_args) as dag:

    # Get Admin variables
    bags_folder = Variable.get("BagsFolder")
    images_folder = Variable.get("ImagesFolder")
    dataset = Variable.get("Dataset")

    # Extract topics list
    topics_string = Variable.get("Topics")
    topics = topics_string.split(",")

    # Build folder paths
    bags_path = os.path.join(ROOT_FOLDER, bags_folder)
    images_path = os.path.join(ROOT_FOLDER, images_folder)
    bag_path = os.path.join(bags_path, dataset) + ".bag"

    task_notify_start = SlackAPIPostOperator(
        task_id="task_notify_start",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=" :dolphin:[PROCESSING] DAG (extract_image_from_bag): Extract images from ROS bag",
        dag=dag,
    )

    task_detect_bag = BranchPythonOperator(
        task_id="task_detect_bag",
        python_callable=extract_img_from_ros_bag.bag_file_exists,
        op_kwargs={"bags_path": bags_path, "dataset": dataset},
        trigger_rule="all_success",
        dag=dag,
    )

    task_bag_not_detected = PythonOperator(
        task_id="task_bag_not_detected",
        python_callable=extract_img_from_ros_bag.bag_not_detected,
        op_kwargs={"bags_path": bags_path, "dataset": dataset},
        dag=dag,
    )

    task_notify_file_with_ext_failure = SlackAPIPostOperator(
        task_id="task_notify_file_with_ext_failure",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=":heavy_multiplication_x: [FAILURE] DAG (extract_image_from_ros_bag): The bag file {} was not detected".format(bag_path),
        dag=dag,
    )

    task_extract_images_from_bag = PythonOperator(
        task_id="task_extract_images_from_bag",
        provide_context=False,
        python_callable=extract_img_from_ros_bag.extract_images_from_bag,
        op_kwargs={
            "bags_path": bags_path,
            "images_path": images_path,
            "dataset": dataset,
            "topics": topics,
        },
        trigger_rule="all_success",
        dag=dag,
    )
    task_notify_extraction_success = SlackAPIPostOperator(
        task_id="task_notify_extraction_success",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=":heavy_check_mark: [SUCCESS] DAG (extract_image_from_ros_bag): Images were successfully extracted from ROS bag",
        trigger_rule="all_success",
        dag=dag,
    )

    task_notify_start.set_downstream(task_detect_bag)
    task_detect_bag.set_downstream(task_bag_not_detected)
    task_detect_bag.set_downstream(task_extract_images_from_bag)
    task_bag_not_detected.set_downstream(task_notify_file_with_ext_failure)
    task_extract_images_from_bag.set_downstream(task_notify_extraction_success)
