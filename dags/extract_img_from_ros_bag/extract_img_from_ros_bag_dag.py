"""
 This DAG will handle images extraction from multiple ROS bag
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable

from extract_img_from_ros_bag import extract_img_from_ros_bag
from utils import file_ops

DATASET_NAME = Variable.get("Dataset")
BAG_FOLDER = "/usr/local/airflow/data/Bags/"
IMAGE_FOLDER = "/usr/local/airflow/data/Images/"

BAG_LOCATION = BAG_FOLDER + DATASET_NAME
IMAGE_LOCATION = IMAGE_FOLDER + DATASET_NAME
ROS_IMAGE_TOPICS = [
    "/provider_vision/Front_GigE/compressed",
    "/provider_vision/Bottom_GigE/compressed",
]


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

    logging.info("Sensing for folder changes")

    task_notify_start = SlackAPIPostOperator(
        task_id="task_notify_start",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=" :dolphin:[PROCESSING] DAG (extract_image_from_bag): Extract images from ROS bag",
        dag=dag,
    )

    task_sense_new_file = FileSensor(
        task_id="task_sense_new_file",
        filepath=BAG_LOCATION,
        fs_conn_id="fs_default",
        dag=dag,
        timeout=20,
    )

    task_detect_file_type_match = BranchPythonOperator(
        task_id="task_detect_file_type_match",
        python_callable=extract_img_from_ros_bag.dir_contains_bag_file,
        op_kwargs={"bag_folder": BAG_LOCATION},
        trigger_rule="all_success",
        dag=dag,
    )

    task_notify_file_with_ext_failure = SlackAPIPostOperator(
        task_id="task_notify_file_with_ext_failure",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=":heavy_multiplication_x: [FAILURE] DAG (extract_image_from_ros_bag): Detected file did not match bag extension type ",
        dag=dag,
    )

    task_extract_image = PythonOperator(
        task_id="task_extract_image",
        provide_context=False,
        python_callable=extract_img_from_ros_bag.extract_images_from_bag,
        op_kwargs={
            "bag_folder": BAG_LOCATION,
            "topics": ROS_IMAGE_TOPICS,
            "output_dir": IMAGE_LOCATION,
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

    task_notify_start.set_downstream(task_sense_new_file)
    task_sense_new_file.set_downstream(task_detect_file_type_match)
    task_detect_file_type_match.set_downstream(task_notify_file_with_ext_failure)
    task_detect_file_type_match.set_downstream(task_extract_image)
    task_extract_image.set_downstream(task_notify_extraction_success)
