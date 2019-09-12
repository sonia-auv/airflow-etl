
"""
 This DAG will handle project creation into labelbox
"""

import logging

from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator

from create_project_into_labelbox import create_dataset, create_project, complete_project_setup, configure_interface_for_project, get_image_labeling_interface_id

ROOT_FOLDER = "/usr/local/airflow/data/"
IMAGE_FOLDER = os.path.join(ROOT_FOLDER, "images")
LABELBOX_API_URL = "https://api.labelbox.com/graphql"
LABELBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjamRrZzJiNXo5eWl3MDE1MDhwczRqOWU2Iiwib3JnYW5pemF0aW9uSWQiOiJjamRmODljNGxxdnNmMDEwMHBvdnFqeWppIiwiYXBpS2V5SWQiOiJjazBncWN4NXM1cWszMDk0NHNmdXV5NjE2IiwiaWF0IjoxNTY4Mjk1MDEzLCJleHAiOjIxOTk0NDcwMTN9.WJzExnJM4lTO3tvWQ867etmDKZWxbJTSW3nix0SKp5o"

slack_webhook_token = BaseHook.get_connection('slack').password
project_name = 'test'

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}


dag = DAG('create_project_into_labelbox', default_args=default_args,
          catchup=False)


task_notify_start = SlackWebhookOperator(
    task_id="task_notify_start",
    http_conn_id='slack',
    webhook_token=slack_webhook_token,
    username='airflow',
    message=" :dolphin:[PROCESSING] DAG (create_project_into_labelbox): Creating project throught labelbox API",
    dag=dag,
)

create_project_into_labelbox = PythonOperator(
    task_id="task_create_project_into_labelbox",
    python_callable=create_project,
    op_kwargs={
        url: LABELBOX_API_URL,
        key: LABELBOX_API_KEY,
        name: project_name
    },
    provide_context=True
)


task_notify_start >> create_project_into_labelbox
