"""
 This DAG will handle project creation into labelbox
"""
import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator

from create_project_into_labelbox import create_project_into_labelbox
from create_project_into_labelbox import test_labelbox_2
from utils import file_ops, slack


DOCKER_DATA_FOLDER = "/usr/local/airflow/data/"
DOCKER_IMAGE_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "images")
DOCKER_JSON_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "json")


LABELBOX_API_URL = "https://api.labelbox.com/graphql"
# LABELBOX_API_KEY = os.environ["LABELBOX_API_KEY"]
LABELBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjamRrZzJiNXo5eWl3MDE1MDhwczRqOWU2Iiwib3JnYW5pemF0aW9uSWQiOiJjamRmODljNGxxdnNmMDEwMHBvdnFqeWppIiwiYXBpS2V5SWQiOiJjazEyMXdzbmswaGI5MDcyMWU3eHVxdnllIiwiaWF0IjoxNTY5NTg0MjA2LCJleHAiOjIyMDA3MzYyMDZ9.YESNVGf5d5U43uJCuOMPrAkt2jz_qV-hLtTiST5-Z8s"

slack_webhook_token = BaseHook.get_connection("slack").password

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


dag = DAG("create_project_into_labelbox", default_args=default_args, catchup=False)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)

json_files = file_ops.get_files_in_directory(DOCKER_JSON_FOLDER, "*.json")

for index, json_file in enumerate(json_files):
    print(json_file)
    create_project_task = PythonOperator(
        task_id="task_create_project_into_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.create_project,
        provide_context=True,
        op_kwargs={
            "api_url": LABELBOX_API_URL,
            "api_key": LABELBOX_API_KEY,
            "project_name": file_ops.get_filename(json_file, with_extension=False),
        },
        dag=dag,
    )

    create_project_dataset_task = PythonOperator(
        task_id="task_create_dataset_into_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.create_dataset,
        provide_context=True,
        op_kwargs={
            "api_url": LABELBOX_API_URL,
            "api_key": LABELBOX_API_KEY,
            "project_name": file_ops.get_filename(json_file, with_extension=False),
            "dataset_name": file_ops.get_filename(json_file, with_extension=False),
        },
        dag=dag,
    )

    # create_dataset_task = PythonOperator(
    #     task_id="task_create_data_into_project" + str(index),
    #     python_callable=create_project_into_labelbox.create_dataset,
    #     op_kwargs={
    #         "api_key": LABELBOX_API_KEY,
    #         "project_name": file_ops.get_filename(json_file, with_extension=False),
    #         "dataset_name": file_ops.get_filename(json_file, with_extension=False),
    #     },
    #     dag=dag,
    # )

    start_task >> create_project_task >> create_project_dataset_task >> end_task
    # create_project_task.set_upstream(start_task)

    # # create_project_dataset_task.set_downstream(create_project_dataset_task)
    # create_project_task.set_downstream(end_task)
    # create_dataset_task.set_downstream(end_task)
