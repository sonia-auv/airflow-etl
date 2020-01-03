import os
from datetime import datetime

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator

from prepare_model_and_data_for_training import prepare_model_and_data_for_training
from utils import file_ops, slack

BASE_AIRFLOW_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "data")
AIRFLOW_MODELS_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "models", "base")
AIRFLOW_MODELS_CSV_FILE = os.path.join(AIRFLOW_DATA_FOLDER, "models", "model_list.csv")
AIRFLOW_TRAINING_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "training")
AIRFLOW_LABEBOX_OUTPUT_DATA_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "labelbox", "output")
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

# Variables
tensorflow_model_zoo_markdown_url = Variable.get("tensorflow_model_zoo_markdown_url")
base_models = Variable.get("tensorflow_model_zoo_models").split(",")
video_feed_sources = Variable.get("video_feed_sources").split(",")


def get_proper_model_config(model_name):
    model_config_variable = f"model_config_{model_name}"
    return Variable.get(model_config_variable)


dag = DAG(
    "prepare_model_and_data_for_training",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


validate_reference_model_list_exist_or_create = BranchPythonOperator(
    task_id="validate_reference_model_list_exist",
    python_callable=prepare_model_and_data_for_training.validate_reference_model_list_exist_or_create,
    op_kwargs={
        "base_model_csv": AIRFLOW_MODELS_CSV_FILE,
        "positive_downstream": "validate_base_model_exist_or_download",
        "negative_downstream": "download_reference_model_list_as_csv",
    },
    dag=dag,
)

download_reference_model_list_as_csv = PythonOperator(
    task_id="download_reference_model_list_as_csv",
    python_callable=prepare_model_and_data_for_training.download_reference_model_list_as_csv,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": AIRFLOW_MODELS_CSV_FILE},
    dag=dag,
)


validate_base_model_exist_or_download = PythonOperator(
    task_id="validate_base_model_exist_or_download",
    python_callable=prepare_model_and_data_for_training.download_and_extract_base_model,
    op_kwargs={
        "base_model_csv": AIRFLOW_MODELS_CSV_FILE,
        "base_model_folder": AIRFLOW_MODELS_FOLDER,
        "base_model_list": base_models,
    },
    dag=dag,
)


for video_source in video_feed_sources:
    check_labelmap_file_content_are_the_same = PythonOperator(
        task_id="check_labelmap_file_content_are_the_same_" + video_source,
        python_callable=prepare_model_and_data_for_training.compare_label_map_file,
        op_kwargs={"base_tf_record_folder": AIRFLOW_TF_RECORD_FOLDER, "video_source": video_source},
        dag=dag,
    )
    for base_model in base_models:

        create_training_folder_tree = PythonOperator(
            task_id="create_training_folder_tree_" + video_source + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.create_training_folder,
            provide_context=True,
            op_kwargs={
                "training_data_folder": AIRFLOW_TRAINING_FOLDER,
                "tf_record_folder": AIRFLOW_TF_RECORD_FOLDER,
                "video_source": video_source,
                "execution_date": "{{ts_nodash}}",
                "base_model": base_model,
            },
            dag=dag,
        )

        copy_labelbox_output_data_to_training_folder = PythonOperator(
            task_id="copy_labelbox_output_data_to_training_folder_"
            + video_source
            + "_"
            + base_model,
            python_callable=prepare_model_and_data_for_training.copy_labelbox_output_data_to_training,
            provide_context=True,
            op_kwargs={
                "labelbox_output_data_folder": AIRFLOW_LABEBOX_OUTPUT_DATA_FOLDER,
                "tf_record_folder": AIRFLOW_TF_RECORD_FOLDER,
                "video_source": video_source,
                "base_model": base_model,
            },
            dag=dag,
        )

        copy_base_model_to_training_folder = PythonOperator(
            task_id="copy_base_model_to_training_folder_" + video_source + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.copy_base_model_to_training_folder,
            provide_context=True,
            op_kwargs={
                "base_model_csv": AIRFLOW_MODELS_CSV_FILE,
                "base_model_folder": AIRFLOW_MODELS_FOLDER,
                "video_source": video_source,
                "base_model": base_model,
            },
            dag=dag,
        )

        genereate_model_config_into_training_folder = PythonOperator(
            task_id="genereate_model_config_into_training_folder_"
            + video_source
            + "_"
            + base_model,
            python_callable=prepare_model_and_data_for_training.generate_model_config,
            provide_context=True,
            op_kwargs={
                "video_source": video_source,
                "base_model": base_model,
                "model_config_template": get_proper_model_config(base_model),
            },
            dag=dag,
        )

        start_task >> validate_reference_model_list_exist_or_create >> [
            validate_base_model_exist_or_download,
            download_reference_model_list_as_csv,
        ]
        download_reference_model_list_as_csv >> validate_base_model_exist_or_download
        validate_base_model_exist_or_download >> check_labelmap_file_content_are_the_same >> create_training_folder_tree
        create_training_folder_tree >> copy_labelbox_output_data_to_training_folder >> copy_base_model_to_training_folder >> genereate_model_config_into_training_folder >> end_task

        # TODO: Remove config file from input_data / model
        # TODO: Add templated model config file
        # TODO: Edit value in templated model config file
        # TODO: Create archive of training folder
        # TODO: Delete all annotations, images, and upload training training folder to GCP
