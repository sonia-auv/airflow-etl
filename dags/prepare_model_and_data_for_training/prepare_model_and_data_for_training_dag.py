import os
from datetime import datetime

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator

from prepare_model_and_data_for_training import prepare_model_and_data_for_training
from utils import file_ops, slack

AIRFLOW_BASE_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(AIRFLOW_BASE_FOLDER, "data")
AIRFLOW_JSON_FOLDER = os.path.join(AIRFLOW_BASE_FOLDER, "json")
AIRFLOW_MODELS_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "models", "base")
AIRFLOW_MODELS_CSV_FILE = os.path.join(AIRFLOW_DATA_FOLDER, "models", "model_list.csv")
AIRFLOW_TRAINING_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "training")
AIRFLOW_TRAINABLE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "trainable")
AIRFLOW_LABELBOX_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "labelbox")
AIRFLOW_LABEBOX_OUTPUT_DATA_FOLDER = os.path.join(AIRFLOW_LABELBOX_FOLDER, "output")
AIRFLOW_TF_RECORD_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "tfrecord")
AIRFLOW_VCS_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "vcs")
AIRFLOW_MODEL_REPO_FOLDER = os.path.join(AIRFLOW_VCS_FOLDER, "deep-detector-model")

DEEP_DETECTOR_MODEL_REPO_URL = "git@github.com:sonia-auv/deep-detector-model.git"

# TODO: Remove after updating
TRAINING_ARCHIVING_PATH = os.path.join(AIRFLOW_DATA_FOLDER, "archive")

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
required_base_models = Variable.get("tensorflow_model_zoo_models").split(",")
video_feed_sources = Variable.get("video_feed_sources").split(",")
gcp_base_bucket_url = f"gs://{Variable.get('bucket_name')}-training/"


# DAG Specific Methods
def get_proper_model_config(video_source, model_name):
    model_config_variable = f"model_config_{video_source}_{model_name}"
    return Variable.get(model_config_variable)


def get_object_class_count(video_source):
    onthology_name = f"ontology_{video_source}"
    onthology = Variable.get(onthology_name, deserialize_json=True)
    return len(onthology["tools"])


dag = DAG(
    "prepare_model_and_data_for_training",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
)

start_task = DummyOperator(task_id="start_task", dag=dag)
join_task = DummyOperator(task_id="join_task", dag=dag)


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
        "required_base_models": required_base_models,
    },
    trigger_rule="none_failed",
    dag=dag,
)

validate_requested_model_exist_in_model_zoo_list = PythonOperator(
    task_id="validate_requested_model_exist_in_model_zoo_list",
    python_callable=prepare_model_and_data_for_training.validate_requested_model_exist_in_model_zoo_list,
    op_kwargs={
        "base_models_csv": AIRFLOW_MODELS_CSV_FILE,
        "required_base_models": required_base_models,
    },
    dag=dag,
)

validate_deep_detector_model_repo_exist_or_clone = BashOperator(
    task_id="validate_deep_detector_model_repo_exist_or_clone",
    bash_command="[ -d '{{params.model_repo_folder}}' ] || git clone {{params.model_repo_url}} {{params.repo_folder}}",
    params={
        "model_repo_folder": AIRFLOW_MODEL_REPO_FOLDER,
        "repo_url": DEEP_DETECTOR_MODEL_REPO_URL,
    },
    provide_context=True,
    dag=dag,
)

create_data_bucket_cmd = f"gsutil ls -b {gcp_base_bucket_url} || gsutil mb {gcp_base_bucket_url}"
create_data_bucket = BashOperator(
    task_id="create_data_bucket",
    bash_command=create_data_bucket_cmd,
    provide_context=True,
    dag=dag,
)

upload_tasks = []

for video_source in video_feed_sources:
    check_labelmap_file_content_are_the_same = PythonOperator(
        task_id=f"check_labelmap_file_content_are_the_same_" + video_source,
        python_callable=prepare_model_and_data_for_training.compare_label_map_file,
        op_kwargs={"base_tf_record_folder": AIRFLOW_TF_RECORD_FOLDER, "video_source": video_source},
        dag=dag,
    )
    for base_model in required_base_models:

        validate_model_presence_in_model_repo_or_create = PythonOperator(
            task_id=f"validate_model_{base_model}_present_in_model_repo_or_create",
            python_callable=prepare_model_and_data_for_training.validate_model_presence_in_model_repo_or_create,
            op_kwargs={"model_repo_folder": AIRFLOW_MODEL_REPO_FOLDER, "base_model": base_model},
            dag=dag,
        )

        create_training_folder_tree = PythonOperator(
            task_id="create_training_folder_tree_" + video_source + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.create_training_folder,
            provide_context=True,
            op_kwargs={
                "base_training_folder": AIRFLOW_TRAINING_FOLDER,
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
                "airflow_base_folder": AIRFLOW_DATA_FOLDER,
                "gcp_base_bucket_url": gcp_base_bucket_url,
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
                "airflow_base_folder": AIRFLOW_DATA_FOLDER,
                "gcp_base_bucket_url": gcp_base_bucket_url,
            },
            dag=dag,
        )

        genereate_model_config = PythonOperator(
            task_id="genereate_model_config_" + video_source + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.generate_model_config,
            provide_context=True,
            op_kwargs={
                "video_source": video_source,
                "base_model": base_model,
                "model_config_template": get_proper_model_config(video_source, base_model),
                "num_classes": get_object_class_count(video_source),
            },
            dag=dag,
        )

        archiving_training_folder = PythonOperator(
            task_id="archiving_training_folder_" + video_source + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.archiving_training_folder,
            provide_context=True,
            op_kwargs={
                "training_archiving_path": TRAINING_ARCHIVING_PATH,
                "video_source": video_source,
                "base_model": base_model,
            },
            dag=dag,
        )

        remove_raw_images_and_annotations_from_training_folder = PythonOperator(
            task_id="remove_raw_images_and_annotations_from_training_folder_"
            + video_source
            + "_"
            + base_model,
            python_callable=prepare_model_and_data_for_training.remove_raw_images_and_annotations_from_training_folder,
            provide_context=True,
            op_kwargs={
                "video_source": video_source,
                "base_model": base_model,
                "gcp_base_bucket_url": gcp_base_bucket_url,
                "airflow_trainable_folder": AIRFLOW_TRAINABLE_FOLDER,
            },
            dag=dag,
        )

        upload_training_folder_to_gcp_bucket = BashOperator(
            task_id="upload_training_folder_to_gcp_bucket_" + video_source + "_" + base_model,
            bash_command="{{{{ ti.xcom_pull(key='gcp_copy_cmd',task_ids='remove_raw_images_and_annotations_from_training_folder_{}_{}')}}}}".format(
                video_source, base_model
            ),
            provide_context=True,
            dag=dag,
            task_concurrency=1,
        )

        # To fix parallelism error with gsutil
        upload_tasks.append(upload_training_folder_to_gcp_bucket)

        start_task >> validate_reference_model_list_exist_or_create >> [
            validate_base_model_exist_or_download,
            download_reference_model_list_as_csv,
        ]
        download_reference_model_list_as_csv >> validate_base_model_exist_or_download >> validate_requested_model_exist_in_model_zoo_list
        validate_requested_model_exist_in_model_zoo_list >> validate_deep_detector_model_repo_exist_or_clone >> check_labelmap_file_content_are_the_same
        check_labelmap_file_content_are_the_same >> validate_model_presence_in_model_repo_or_create >> create_training_folder_tree
        create_training_folder_tree >> copy_labelbox_output_data_to_training_folder >> copy_base_model_to_training_folder
        copy_base_model_to_training_folder >> genereate_model_config >> archiving_training_folder
        archiving_training_folder >> remove_raw_images_and_annotations_from_training_folder >> join_task

        # To fix parallelism error with gsutil
        for index, task in enumerate(upload_tasks):
            if index == 0:
                join_task >> create_data_bucket
                create_data_bucket >> task
            else:
                upload_tasks[index - 1] >> task

# upload_tasks[-1] >> clean_up_post_training_prep
