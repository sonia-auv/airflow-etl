import os
from datetime import datetime
from airflow import DAG
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator

from prepare_model_and_data_for_training import prepare_model_and_data_for_training
from utils import file_ops, slack


DOCKER_DATA_FOLDER = "/usr/local/airflow/data/"
BASE_MODELS_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "model", "base")
BASE_MODELS_CSV = os.path.join(DOCKER_DATA_FOLDER, "model", "model_list.csv")
BASE_TRAINING_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "training")
BASE_TRAINING_INPUT_FOLDER = os.path.join(BASE_TRAINING_FOLDER, "input")
DOCKER_TF_RECORD_FOLDER = os.path.join(DOCKER_DATA_FOLDER, "tfrecord")

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

tensorflow_model_zoo_markdown_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/object_detection/g3doc/detection_model_zoo.md"  # TODO: Extract to variables

base_model = [
    "faster_rcnn_inception_resnet_v2_atrous_coco_2018_01_28",
    "faster_rcnn_inception_resnet_v2_atrous_lowproposals_coco_2018_01_28",
]  # TODO: Extract to variables

dag = DAG("prepare_model_and_data_for_training", default_args=default_args, catchup=False)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


check_reference_file_exist = BranchPythonOperator(
    task_id="check_reference_model_list_exist",
    python_callable=prepare_model_and_data_for_training.reference_model_list_exist_or_create,
    op_kwargs={
        "base_model_csv": BASE_MODELS_CSV,
        "positive_downstream": "check_model_version_differences",
        "negative_downstream": "download_current_model_zoo_list",
    },
    dag=dag,
)


download_current_model_zoo_list = PythonOperator(
    task_id="download_current_model_zoo_list",
    python_callable=prepare_model_and_data_for_training.download_reference_model_list_as_csv,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": BASE_MODELS_CSV},
    dag=dag,
)


check_model_list_difference = BranchPythonOperator(
    task_id="check_model_version_differences",
    python_callable=prepare_model_and_data_for_training.download_reference_model_list_as_csv,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": BASE_MODELS_CSV},
    dag=dag,
)

check_reference_model_list_exist_task = PythonOperator(
    task_id="check_reference_model_list_exist",
    python_callable=prepare_model_and_data_for_training.reference_model_list_exist_or_create,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": BASE_MODELS_LIST_CSV},
    provide_context=True,
    dag=dag,
)

base_model_exist_or_download = PythonOperator(
    task_id="base_model_exist_or_download",
    python_callable=prepare_model_and_data_for_training.download_and_extract_base_model,
    op_kwargs={
        "base_model_csv": BASE_MODELS_CSV,
        "base_model_folder": BASE_MODELS_FOLDER,
        "base_model_list": base_model,
    },
    trigger_rule="all_done",
    dag=dag,
)


start_task >> check_reference_file_exist >> [
    download_current_model_zoo_list,
    check_model_list_difference,
] >> base_model_exist_or_download >> end_task
