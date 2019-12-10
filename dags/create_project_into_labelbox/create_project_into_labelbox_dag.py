"""
 This DAG will handle project creation into labelbox
"""
import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator

from create_project_into_labelbox import create_project_into_labelbox
from utils import file_ops, slack


BASE_AIRFLOW_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "data")
AIRFLOW_IMAGE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "images")
AIRFLOW_JSON_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "json")

labelbox_api_url = BaseHook.get_connection("labelbox").host
labelbox_api_key = BaseHook.get_connection("labelbox").password
slack_webhook_token = BaseHook.get_connection("slack").password


bucket_name = Variable.get("bucket_name")
ontology_front = Variable.get("ontology_front")
ontology_bottom = Variable.get("ontology_bottom")

json_files = file_ops.get_files_in_directory(AIRFLOW_JSON_FOLDER, "*.json")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "schedule_interval" : None,
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": slack.task_fail_slack_alert,
    "retries": 0,
}


def get_proper_ontology(json_file):
    ontology_name = file_ops.get_ontology_name_from_file(json_file)
    if ontology_name == "front":
        return ontology_front
    elif ontology_name == "bottom":
        return ontology_bottom


dag = DAG("create_project_into_labelbox", default_args=default_args, catchup=False)


start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)

for index, json_file in enumerate(json_files):
    create_project_task = PythonOperator(
        task_id="task_create_project_into_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.create_project,
        provide_context=True,
        op_kwargs={
            "api_url": labelbox_api_url,
            "api_key": labelbox_api_key,
            "project_name": file_ops.get_filename(json_file, with_extension=False),
        },
        dag=dag,
    )

    create_project_dataset_task = PythonOperator(
        task_id="task_create_dataset_into_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.create_dataset,
        provide_context=True,
        op_kwargs={
            "api_url": labelbox_api_url,
            "api_key": labelbox_api_key,
            "project_name": file_ops.get_filename(json_file, with_extension=False),
            "dataset_name": file_ops.get_filename(json_file, with_extension=False),
        },
        dag=dag,
    )

    get_labeling_image_interface_task = PythonOperator(
        task_id="task_get_labeling_image_interface_from_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.get_image_labeling_interface_id,
        provide_context=True,
        op_kwargs={"api_url": labelbox_api_url, "api_key": labelbox_api_key},
        dag=dag,
    )

    configure_interface_for_project_task = PythonOperator(
        task_id="task_configure_labeling_interface_for_project_into_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.configure_interface_for_project,
        provide_context=True,
        op_kwargs={
            "api_url": labelbox_api_url,
            "api_key": labelbox_api_key,
            "ontology": get_proper_ontology(json_file),
            "index": index,
        },
        dag=dag,
    )

    complete_labelbox_project_setup_task = PythonOperator(
        task_id="task_complete_labelbox_project__" + str(index),
        python_callable=create_project_into_labelbox.complete_project_setup,
        provide_context=True,
        op_kwargs={"api_url": labelbox_api_url, "api_key": labelbox_api_key, "index": index},
        dag=dag,
    )

    bulk_import_dataset_task = PythonOperator(
        task_id="bulk_import_data_into_dataset_" + str(index),
        python_callable=create_project_into_labelbox.create_data_rows,
        provide_context=True,
        op_kwargs={
            "api_url": labelbox_api_url,
            "api_key": labelbox_api_key,
            "index": index,
            "json_file": json_file,
        },
        dag=dag,
    )

    start_task >> create_project_task >> create_project_dataset_task >> get_labeling_image_interface_task >> configure_interface_for_project_task >> complete_labelbox_project_setup_task >> bulk_import_dataset_task >> end_task
