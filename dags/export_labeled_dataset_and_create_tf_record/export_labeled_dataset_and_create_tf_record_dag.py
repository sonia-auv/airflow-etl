import json
import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

from export_labeled_dataset_and_create_tf_record import export_labeled_dataset_and_create_tf_record
from utils import file_ops, slack

HOST_ROOT_FOLDER = os.environ["HOST_ROOT_FOLDER"]
HOST_DATA_FOLDER = HOST_ROOT_FOLDER + "/data/"
HOST_LABELBOX_FOLDER = HOST_DATA_FOLDER + "labelbox/"
HOST_LABELBOX_INPUT_FOLDER = HOST_LABELBOX_FOLDER + "input/"
HOST_LABELBOX_OUTPUT_FOLDER = HOST_LABELBOX_FOLDER + "/output/"


BASE_AIRFLOW_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "data")

AIRFLOW_CURRENT_DAG_FOLDER = os.path.dirname(os.path.realpath(__file__))
AIRFLOW_LABELBOX_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "labelbox")
AIRFLOW_LABELBOX_OUTPUT_FOLDER = os.path.join(AIRFLOW_LABELBOX_FOLDER, "output")
AIRFLOW_TF_RECORD_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "tfrecord")


labelbox_api_url = BaseHook.get_connection("labelbox").host
labelbox_api_key = BaseHook.get_connection("labelbox").password
slack_webhook_token = BaseHook.get_connection("slack").password

ontology_front = json.loads(Variable.get("ontology_front"))
ontology_bottom = json.loads(Variable.get("ontology_bottom"))

export_project_name = Variable.get("labelbox_export_project_list").split(",")

front_cam_object_list = [tool["name"] for tool in ontology_front["tools"]]

bottom_cam_object_list = [tool["name"] for tool in ontology_bottom["tools"]]

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


def get_proper_label_list(project_name):
    project_name_split = project_name.split("_")[0]

    if project_name_split == "front":
        return front_cam_object_list
    elif project_name_split == "bottom":
        return bottom_cam_object_list
    else:
        raise ValueError("Possible values are front or bottom")


for index, project_name in enumerate(export_project_name):

    generate_project_label_extract_from_task = PythonOperator(
        task_id="generate_project_label_extract_from_" + project_name,
        python_callable=export_labeled_dataset_and_create_tf_record.generate_project_labels,
        op_kwargs={
            "api_url": labelbox_api_url,
            "api_key": labelbox_api_key,
            "project_name": project_name,
        },
        trigger_rule="all_success",
        dag=dag,
    )

    fetch_labels_from_project_task = PythonOperator(
        task_id="fetch_labels_from_project_" + project_name,
        python_callable=export_labeled_dataset_and_create_tf_record.fetch_project_labels,
        op_kwargs={
            "api_url": labelbox_api_url,
            "api_key": labelbox_api_key,
            "project_name": project_name,
            "output_folder": AIRFLOW_LABELBOX_FOLDER,
        },
        trigger_rule="all_success",
        dag=dag,
    )

    input_folder = HOST_LABELBOX_INPUT_FOLDER + project_name
    output_folder = HOST_LABELBOX_OUTPUT_FOLDER + project_name

    extract_labeled_data_from_labelbox = DockerOperator(
        task_id="extract_labeled_data_from_labelbox_" + project_name,
        image="soniaauvets/labelbox-exporter:1.0.0",
        force_pull=True,
        auto_remove=True,
        command=f"python main.py /input/{project_name}.json /output",
        api_version="1.37",
        docker_url="unix://var/run/docker.sock",
        volumes=[f"{input_folder}:/input", f"{output_folder}:/output"],
        network_mode="bridge",
        provide_context=True,
        trigger_rule="all_success",
        dag=dag,
    )

    voc_annotation_extract_dir = os.path.join(AIRFLOW_LABELBOX_OUTPUT_FOLDER, project_name)
    voc_image_extract_dir = os.path.join(AIRFLOW_LABELBOX_OUTPUT_FOLDER, project_name, "images")

    # TODO:Validate voc data (Image + draw bbox)
    trainval_dir = os.path.join(AIRFLOW_TF_RECORD_FOLDER, project_name)
    labelmap_dir = os.path.join(AIRFLOW_TF_RECORD_FOLDER, project_name)

    create_trainval_file = PythonOperator(
        task_id="create_trainval_" + project_name,
        python_callable=export_labeled_dataset_and_create_tf_record.generate_trainval_file,
        op_kwargs={
            "annotation_dir": voc_annotation_extract_dir,
            "output_dir": trainval_dir,
            "output_file": f"trainval_{project_name}",
        },
        trigger_rule="all_success",
        dag=dag,
    )

    create_labelmap_file = PythonOperator(
        task_id="create_labelmap_" + project_name,
        python_callable=export_labeled_dataset_and_create_tf_record.generate_labelmap_file,
        op_kwargs={
            "labels": get_proper_label_list(project_name),
            "output_dir": trainval_dir,
            "output_file": f"label_map_{project_name}",
        },
        trigger_rule="all_success",
        dag=dag,
    )

    trainval_file = os.path.join(trainval_dir, f"trainval_{project_name}")
    labelmap_file = os.path.join(trainval_dir, f"label_map_{project_name}")
    tfrecord_output_dir = os.path.join(AIRFLOW_TF_RECORD_FOLDER, project_name)

    create_tf_record_command = f"python {AIRFLOW_CURRENT_DAG_FOLDER}/create_tf_record.py --annotation_dir={voc_annotation_extract_dir} --image_dir={voc_image_extract_dir} --label_map_file={labelmap_file}.pbtxt --trainval_file={trainval_file}.txt --output_dir={tfrecord_output_dir}"

    create_tf_record = BashOperator(
        task_id="create_tf_record_" + project_name, bash_command=create_tf_record_command, dag=dag
    )

    generate_project_label_extract_from_task >> fetch_labels_from_project_task >> extract_labeled_data_from_labelbox >> create_trainval_file >> create_labelmap_file >> create_tf_record
