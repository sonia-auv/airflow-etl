"""
 This DAG will upload image to google cloud storage dataset
"""

import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable


ROOT_FOLDER = "/usr/local/airflow/data/"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}


with DAG("export_images_to_gcs_dataset", catchup=False, default_args=default_args) as dag:

    logging.info("Starting images export to google cloud storage")

    images_folder = Variable.get("ImagesFolder")
    images_path = os.path.join(ROOT_FOLDER, images_folder)
    storage_name = Variable.get("StorageName")
    dataset = Variable.get("Dataset")
    notify_slack = Variable.get("NotifySlack")

    input_location = os.path.join(images_folder, dataset)
    output_location = "gs://" + os.path.join(storage_name, dataset)

    task_notify_start = SlackAPIPostOperator(
        task_id="task_notify_start",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=" :dolphin:[PROCESSING] DAG (export_img_to_gcs_dataset): Exporting image to GCP dataset folder",
        dag=dag,
    )

    command = "gsutil -m cp -r {src_folder} {dest_bucket}".format(
        src_folder=input_location, dest_bucket=output_location
    )
    task_export_images_to_gcs_dataset = BashOperator(
        task_id="task_export_images_to_gcs_dataset", bash_command=command, dag=dag
    )

    command = "rm -rf  {src_folder}".format(src_folder=input_location)

    task_delete_input_files_from_local_storage = BashOperator(
        task_id="task_delete_input_files_from_local_storage", 
        bash_command=command,
        trigger_rule="all_success",
        dag=dag
    )

    task_notify_export_success = SlackAPIPostOperator(
        task_id="task_notify_export_to_gcs_success",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=":heavy_check_mark: [SUCCESS] DAG (export_img_to_gcs_dataset): Images were exported to google cloud storage",
        trigger_rule="all_success",
        dag=dag,
    )

    task_notify_export_failure = SlackAPIPostOperator(
        task_id="task_notify_export_to_gcs_failure",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=":heavy_multiplication_x: [FAILURE] DAG (export_img_to_gcs_dataset): There was an error while exporting image to google cloud storage",
        trigger_rule="one_failed",
        dag=dag,
    )

    if (notify_slack == "True"):
        task_notify_start.set_downstream(task_export_images_to_gcs_dataset)

    task_export_images_to_gcs_dataset.set_downstream(task_delete_input_files_from_local_storage)

    if (notify_slack == "True"):
        task_delete_input_files_from_local_storage.set_downstream(task_notify_export_success)
        task_export_images_to_gcs_dataset.set_downstream(task_notify_export_failure)
