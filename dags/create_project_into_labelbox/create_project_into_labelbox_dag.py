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
# LABELBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjamRrZzJiNXo5eWl3MDE1MDhwczRqOWU2Iiwib3JnYW5pemF0aW9uSWQiOiJjamRmODljNGxxdnNmMDEwMHBvdnFqeWppIiwiYXBpS2V5SWQiOiJjazEyMXdzbmswaGI5MDcyMWU3eHVxdnllIiwiaWF0IjoxNTY5NTg0MjA2LCJleHAiOjIyMDA3MzYyMDZ9.YESNVGf5d5U43uJCuOMPrAkt2jz_qV-hLtTiST5-Z8s"
LABELBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjamRmODljc2JxbW9hMDEzMDg2cGM0eTFnIiwib3JnYW5pemF0aW9uSWQiOiJjamRmODljNGxxdnNmMDEwMHBvdnFqeWppIiwiYXBpS2V5SWQiOiJjazJuZzR3aGNnMWM1MDk0NHIyNXljM2R6IiwiaWF0IjoxNTczMDU0NjcxLCJleHAiOjIyMDQyMDY2NzF9.l9flIjZaSmXHomMrR7BHmIYeFoN8Q3t9Q0Lfka6_tq8"

slack_webhook_token = BaseHook.get_connection("slack").password
bucket_name = Variable.get("bucket_name")

ontology_front = {
    "tools": [
        {"color": "Green", "tool": "rectangle", "name": "vetalas"},
        {"color": "Yellow", "tool": "rectangle", "name": "jiangshi"},
        {"color": "Magenta", "tool": "rectangle", "name": "vampire"},
        {"color": "Pink", "tool": "rectangle", "name": "draugr"},
        {"color": "Cornsilk", "tool": "rectangle", "name": "answag"},
    ],
    "classifications": [],
}

ontology_bottom = {
    "tools": [
        {"color": "Red", "tool": "rectangle", "name": "bat"},
        {"color": "Blue", "tool": "rectangle", "name": "wolf"},
    ],
    "classifications": [],
}

# org_user = {
#     "users": [
#         {"email": "club.sonia@etsmtl.net", "name": "Club Etudiant SONIA", "role": "Admin"},
#         {"email": " camille.sauvain.1@etsmtl.net", "name": "Camille Sauvain", "role": "Admin"},
#         {"email": "gauthiermartin86@gmail.com", "name": "Martin Gauthier", "role": "Admin"},
#         {
#             "email": "marc-antoine.couture.1@ens.etsmtl.ca",
#             "name": "Marc-Antoine Couture",
#             "role": "Team Manager",
#         },
#     ]
# }


output_location = f"https://{bucket_name}/"

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

    bulk_import_dataset_task = PythonOperator(
        task_id="bulk_import_data_into_dataset_" + str(index),
        python_callable=create_project_into_labelbox.create_data_rows,
        provide_context=True,
        op_kwargs={
            "api_url": LABELBOX_API_URL,
            "api_key": LABELBOX_API_KEY,
            "index": index,
            "json_file": json_file,
        },
        dag=dag,
    )

    start_task >> create_project_task >> create_project_dataset_task >> get_labeling_image_interface_task >> configure_interface_for_project_task >> complete_labelbox_project_setup_task >> bulk_import_dataset_task >> end_task
