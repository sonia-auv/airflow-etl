import os
from datetime import datetime
from airflow import DAG
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator

from prepare_model_and_data_for_training import prepare_model_and_data_for_training
from utils import file_ops, slack


BASE_AIRFLOW_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "data")
AIRFLOW_MODELS_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "models", "base")
AIRFLOW_MODELS_CSV = os.path.join(AIRFLOW_DATA_FOLDER, "models", "model_list.csv")
AIRFLOW_TRAINING_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "training")
AIRFLOW_TRAINING_INPUT_FOLDER = os.path.join(AIRFLOW_TRAINING_FOLDER, "input")
AIRFLOW_TF_RECORD_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "tfrecord")

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

tensorflow_model_zoo_markdown_url = Variable.get("tensorflow_model_zoo_markdown_url")
base_model = Variable.get("tensorflow_model_zoo_models").split(",")
video_feed_sources = Variable.get("video_feed_sources").split(",")


dag = DAG(
    "prepare_model_and_data_for_training",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


check_reference_file_exist = BranchPythonOperator(
    task_id="check_reference_model_list_exist",
    python_callable=prepare_model_and_data_for_training.reference_model_list_exist_or_create,
    op_kwargs={
        "base_model_csv": AIRFLOW_MODELS_CSV,
        "positive_downstream": "check_model_version_differences",
        "negative_downstream": "download_current_model_zoo_list",
    },
    dag=dag,
)

check_reference_model_list_exist_task = PythonOperator(
    task_id="check_reference_model_list_exist",
    python_callable=prepare_model_and_data_for_training.reference_model_list_exist_or_create,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": AIRFLOW_MODELS_CSV},
    provide_context=True,
    dag=dag,
)


check_model_list_difference = PythonOperator(
    task_id="check_model_version_differences",
    python_callable=prepare_model_and_data_for_training.check_reference_model_list_different,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": AIRFLOW_MODELS_CSV},
    dag=dag,
)


download_current_model_zoo_list = PythonOperator(
    task_id="download_current_model_zoo_list",
    python_callable=prepare_model_and_data_for_training.download_reference_model_list_as_csv,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": AIRFLOW_MODELS_CSV},
    dag=dag,
)


base_model_exist_or_download = PythonOperator(
    task_id="base_model_exist_or_download",
    python_callable=prepare_model_and_data_for_training.download_and_extract_base_model,
    op_kwargs={
        "base_model_csv": AIRFLOW_MODELS_CSV,
        "base_model_folder": AIRFLOW_MODELS_FOLDER,
        "base_model_list": base_model,
    },
    trigger_rule="all_done",
    dag=dag,
)

for video_source in video_feed_sources:

    check_labelmap_file_content_are_the_same = PythonOperator(
        task_id="check_labelmap_file_content_are_the_same_" + video_source,
        python_callable=prepare_model_and_data_for_training.compare_label_map_file,
        op_kwargs={"base_tf_record_folder": AIRFLOW_TF_RECORD_FOLDER, "video_source": video_source},
        dag=dag,
    )

    start_task >> check_reference_file_exist >> [
        download_current_model_zoo_list,
        check_model_list_difference,
    ] >> base_model_exist_or_download >> check_labelmap_file_content_are_the_same >> end_task
