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


DOCKER_DATA_FOLDER = "/usr/local/airflow/data/"
DOCKER_IMAGE_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "images")
DOCKER_JSON_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "json")


LABELBOX_API_URL = "https://api.labelbox.com/graphql"
LABELBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjamRrZzJiNXo5eWl3MDE1MDhwczRqOWU2Iiwib3JnYW5pemF0aW9uSWQiOiJjamRmODljNGxxdnNmMDEwMHBvdnFqeWppIiwiYXBpS2V5SWQiOiJjazEyMXdzbmswaGI5MDcyMWU3eHVxdnllIiwiaWF0IjoxNTY5NTg0MjA2LCJleHAiOjIyMDA3MzYyMDZ9.YESNVGf5d5U43uJCuOMPrAkt2jz_qV-hLtTiST5-Z8s"

slack_webhook_token = BaseHook.get_connection("slack").password

ontology_front = {
    "tools": [
        {
            "color": "Green",
            "tool": "rectangle",
            "name": "vetalas",
            "featureSchemaId": "d8c76233-7572-413f-9ace-fbb367243ebe",
            "schemaNodeId": "95ea4e48-501f-40ea-b947-0f8b57af93d6",
        },
        {
            "color": "Yellow",
            "tool": "rectangle",
            "name": "jiangshi",
            "featureSchemaId": "496bc308-db6d-491c-8ebb-539441109289",
            "schemaNodeId": "edb01a9f-e30e-410e-bd76-7724ddcc3973",
        },
        {
            "color": "Magenta",
            "tool": "rectangle",
            "name": "vampire",
            "featureSchemaId": "21de612e-2f45-4519-b37a-f4ae0630f4e2",
            "schemaNodeId": "7e9d81fe-b0b5-4cf9-9830-78451c17522a",
        },
        {
            "color": "Pink",
            "tool": "rectangle",
            "name": "draugr",
            "featureSchemaId": "7e342bdc-dd99-47ec-b6db-90a46c1f3534",
            "schemaNodeId": "f3175c8f-90fa-49f1-8981-02119a5ac554",
        },
        {
            "color": "Cornsilk",
            "tool": "rectangle",
            "name": "answag",
            "featureSchemaId": "27f61404-dd19-4928-8c2c-ebfcb58dae2f",
            "schemaNodeId": "72bdcfa4-8062-4878-a4b9-b7f69414c808",
        },
    ],
    "classifications": [],
}

ontology_bottom = {
    "tools": [
        {
            "color": "Red",
            "tool": "rectangle",
            "name": "bat",
            "featureSchemaId": "8432e791-c890-4a96-90cc-557f89912df6",
            "schemaNodeId": "d925ae8f-203f-41e5-a5c4-33f688ec0f7e",
        },
        {
            "color": "Blue",
            "tool": "rectangle",
            "name": "wolf",
            "featureSchemaId": "18c48c89-5c79-4273-ab1f-36d7f2e8cc29",
            "schemaNodeId": "4277c26b-5f12-43cd-a39e-8826dccf0e56",
        },
    ],
    "classifications": [],
}


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


def get_proper_ontology(json_file):
    ontology_name = file_ops.get_ontology_name_from_file(json_file)
    if ontology_name == "front":
        return ontology_front
    elif ontology_name == "bottom":
        return ontology_bottom


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

    get_labeling_image_interface_task = PythonOperator(
        task_id="task_get_labeling_image_interface_from_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.get_image_labeling_interface_id,
        provide_context=True,
        op_kwargs={"api_url": LABELBOX_API_URL, "api_key": LABELBOX_API_KEY},
        dag=dag,
    )

    configure_interface_for_project_task = PythonOperator(
        task_id="task_configure_labeling_interface_for_project_into_labelbox_" + str(index),
        python_callable=create_project_into_labelbox.configure_interface_for_project,
        provide_context=True,
        op_kwargs={
            "api_url": LABELBOX_API_URL,
            "api_key": LABELBOX_API_KEY,
            "ontology": get_proper_ontology(json_file),
            "index": index,
        },
        dag=dag,
    )

    complete_labelbox_project_setup_task = PythonOperator(
        task_id="task_complete_labelbox_project__" + str(index),
        python_callable=create_project_into_labelbox.complete_project_setup,
        provide_context=True,
        op_kwargs={"api_url": LABELBOX_API_URL, "api_key": LABELBOX_API_KEY, "index": index},
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

    start_task >> create_project_task >> create_project_dataset_task >> get_labeling_image_interface_task >> configure_interface_for_project_task >> complete_labelbox_project_setup_task >> end_task
    # create_project_task.set_upstream(start_task)

    # # create_project_dataset_task.set_downstream(create_project_dataset_task)
    # create_project_task.set_downstream(end_task)
    # create_dataset_task.set_downstream(end_task)
