"""
 This DAG will upload image to google cloud storage dataset
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator
from airflow.operators.slack_operator import SlackAPIPostOperator

from export_img_to_gcs_dataset import export_img_to_gcs_dataset
from utils import slack

DOCKER_ROOT_FOLDER = "/usr/local/airflow/data/"
IMAGE_FOLDER = os.path.join(DOCKER_ROOT_FOLDER, "images")
CSV_FOLDER = os.path.join(DOCKER_ROOT_FOLDER, "csv")
JSON_FOLDER = os.path.join(DOCKER_ROOT_FOLDER, "json")

slack_webhook_token = BaseHook.get_connection("slack").password
bucket_name = Variable.get("bucket_name")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": slack.task_fail_slack_alert,
    "retries": 0,
}


dag = DAG("export_images_to_gcs_dataset", catchup=False, default_args=default_args)

input_image_location = IMAGE_FOLDER
input_json_location = JSON_FOLDER
output_location = f"gs://{bucket_name}/"

create_data_bucket_cmd = f"gsutil ls -b {output_location} || gsutil mb {output_location}"
create_data_bucket = BashOperator(
    task_id="create_data_bucket", bash_command=create_data_bucket_cmd, provide_context=True, dag=dag
)

set_data_bucket_acl_cmd = f"gsutil -m acl set -a public-read {output_location}"
set_data_bucket_acl = BashOperator(
    task_id="set_data_bucket_acl",
    bash_command=set_data_bucket_acl_cmd,
    provide_context=True,
    trigger_rule="all_success",
    dag=dag,
)

export_images_to_gcs_dataset_cmd = f"gsutil -m cp -r {input_image_location} {output_location}"
export_images_to_gcs_dataset = BashOperator(
    task_id="export_images_to_gcs",
    bash_command=export_images_to_gcs_dataset_cmd,
    provide_context=True,
    trigger_rule="all_success",
    dag=dag,
)

create_json = PythonOperator(
    task_id="create_json_export_file",
    python_callable=export_img_to_gcs_dataset.create_json,
    op_kwargs={
        "images_path": IMAGE_FOLDER,
        "gcs_images_path": output_location,
        "json_path": JSON_FOLDER,
    },
    trigger_rule="all_success",
    dag=dag,
)

export_json_to_gcs_dataset_cmd = f"gsutil -m cp -r {input_json_location} {output_location}"
export_json_to_gcs_dataset = BashOperator(
    task_id="export_json_to_gcs",
    bash_command=export_json_to_gcs_dataset_cmd,
    provide_context=True,
    trigger_rule="all_success",
    dag=dag,
)

notify_upload_success = slack.dag_notify_success_slack_alert(dag=dag)

create_data_bucket >> set_data_bucket_acl
set_data_bucket_acl >> export_images_to_gcs_dataset >> notify_upload_success
set_data_bucket_acl >> create_json >> export_json_to_gcs_dataset >> notify_upload_success
