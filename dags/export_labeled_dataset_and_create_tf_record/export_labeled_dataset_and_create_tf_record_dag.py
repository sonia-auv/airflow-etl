import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator


from export_labeled_dataset_and_create_tf_record import export_labeled_dataset_and_create_tf_record

from .lb.exporters import voc_exporter as voc_ex

from utils import file_ops, slack

DOCKER_DATA_FOLDER = "/usr/local/airflow/data/"
DOCKER_LABELBOX_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "labelbox")
DOCKER_IMAGE_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "images")
TF_RECORD_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "tfrecords")

CURRENT_DAG_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "export_labeled_dataset_and_create_tf_record")

LABELBOX_API_URL = "https://api.labelbox.com/graphql"
LABELBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjamRmODljc2JxbW9hMDEzMDg2cGM0eTFnIiwib3JnYW5pemF0aW9uSWQiOiJjamRmODljNGxxdnNmMDEwMHBvdnFqeWppIiwiYXBpS2V5SWQiOiJjazJkamVueW5sNjB6MDk0NGZnNWxjdjRpIiwiaWF0IjoxNTcyNDU1NTAzLCJleHAiOjIyMDM2MDc1MDN9.ENXBSGEAa7fTkMn0aMKBnTDdM4LxIqCnsmmquPY0Co8"

slack_webhook_token = BaseHook.get_connection("slack").password

export_project_name = ["Buoy_robosub_2019", "vampire_charlie"]

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

dag = DAG("import_labeled_dataset_and_create_tf_record", default_args=default_args, catchup=False)


for index, project_name in enumerate(export_project_name):

    generate_project_label_extract_from_task = PythonOperator(
        task_id="generate_project_label_extract_from_" + project_name,
        python_callable=export_labeled_dataset_and_create_tf_record.generate_project_labels,
        # provide_context=True,
        op_kwargs={
            "api_url": LABELBOX_API_URL,
            "api_key": LABELBOX_API_KEY,
            "project_name": project_name,
        },
        dag=dag,
    )

    fetch_labels_from_project_task = PythonOperator(
        task_id="fetch_labels_from_project_" + project_name,
        python_callable=export_labeled_dataset_and_create_tf_record.fetch_project_labels,
        # provide_context=True,
        op_kwargs={
            "api_url": LABELBOX_API_URL,
            "api_key": LABELBOX_API_KEY,
            "project_name": project_name,
            "output_folder": DOCKER_LABELBOX_FOLDER,
        },
        dag=dag,
    )

    voc_dir = os.path.join(TF_RECORD_FOLDER, project_name)
    image_dir = os.path.join(DOCKER_IMAGE_FOLDER, project_name)

    image_input_dir = os.path.join(TF_RECORD_FOLDER, project_name, "input")
    labeled_data = os.path.join(DOCKER_LABELBOX_FOLDER, project_name, project_name + ".json")
    annotations_output_dir = os.path.join(TF_RECORD_FOLDER, project_name, "annotations")
    image_output_dir = os.path.join(TF_RECORD_FOLDER, project_name, "output")

    export_json_content_to_voc = PythonOperator(
        task_id="export_json_content_to_voc_" + project_name,
        python_callable=voc_ex.from_json,
        op_kwargs={
            "image_input_dir": image_input_dir,
            "labeled_data": labeled_data,
            "annotations_output_dir": annotations_output_dir,
            "image_output_dir": image_output_dir,
        },
        dag=dag,
    )

    tf_record_path = os.path.join(TF_RECORD_FOLDER, project_name)
    label_map_path = os.path.join(TF_RECORD_FOLDER, project_name + ".pbtxt")
    trainval_path = os.path.join(TF_RECORD_FOLDER, project_name + ".txt")

    create_trainval_file = PythonOperator(
        task_id="create_trainval_" + project_name,
        python_callable=create_tf_record_from_labaled_data.generate_trainval_file,
        op_kwargs={"annotation_dir": annotations_output_dir, "output_file": trainval_path},
        dag=dag,
    )

    # TODO: Extract from create_tf_record.py
    # command = "python /usr/local/airflow/dags/create_tf_record_from_labaled_data/create_tf_record.py --annotation_dir={voc_dir} --image_dir={img_dir} --label_map_file={label_map_path} --trainval_file={trainval_path} --output_dir={tf_dir}".format(
    #     voc_dir=voc_path,
    #     img_dir=train_img_path,
    #     tf_dir=tf_record_path,
    #     label_map_path=label_map_path,
    #     trainval_path=trainval_path,
    # )

    generate_project_label_extract_from_task >> fetch_labels_from_project_task >> export_json_content_to_voc >> create_trainval_file
