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


BASE_AIRFLOW_FOLDER = "/home/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "data")
AIRFLOW_IMAGE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "images")
AIRFLOW_CSV_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "csv")
AIRFLOW_JSON_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "json")

GCP_STORAGE_BASE = "https://storage.googleapis.com/"

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

bucket_base_uri = f"gs://{bucket_name}/"
bucket_image_storage_url = f"{GCP_STORAGE_BASE}{bucket_name}/images/"


dag = DAG(
    "2-export_images_to_gcs_dataset", default_args=default_args, catchup=False, schedule_interval=None
)


create_data_bucket_cmd = f"gsutil ls -b {bucket_base_uri} || gsutil mb {bucket_base_uri}"
create_data_bucket = BashOperator(
    task_id="create_data_bucket", bash_command=create_data_bucket_cmd, dag=dag
)

set_data_bucket_acl_cmd = f"gsutil defacl ch -u AllUsers:R {bucket_base_uri}"
set_data_bucket_acl = BashOperator(
    task_id="set_data_bucket_acl",
    bash_command=set_data_bucket_acl_cmd,
    trigger_rule="all_success",
    dag=dag,
)

export_images_to_gcs_dataset_cmd = f"gsutil -m cp -r {AIRFLOW_IMAGE_FOLDER} {bucket_base_uri}"
export_images_to_gcs_dataset = BashOperator(
    task_id="export_images_to_gcs",
    bash_command=export_images_to_gcs_dataset_cmd,
    trigger_rule="all_success",
    dag=dag,
)

create_json = PythonOperator(
    task_id="create_json_export_file",
    python_callable=export_img_to_gcs_dataset.create_json,
    op_kwargs={
        "images_path": AIRFLOW_IMAGE_FOLDER,
        "gcs_images_path": bucket_image_storage_url,
        "json_path": AIRFLOW_JSON_FOLDER,
    },
    trigger_rule="all_success",
    dag=dag,
)

create_data_bucket >> set_data_bucket_acl
set_data_bucket_acl >> [export_images_to_gcs_dataset, create_json]
