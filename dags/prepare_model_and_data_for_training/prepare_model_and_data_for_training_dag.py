import os
from datetime import datetime

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator

from prepare_model_and_data_for_training import prepare_model_and_data_for_training
from utils import file_ops, slack
import json

BASE_AIRFLOW_FOLDER = "/home/airflow"
AIRFLOW_DATA_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "data")
AIRFLOW_JSON_FOLDER = os.path.join(BASE_AIRFLOW_FOLDER, "json")
AIRFLOW_MODELS_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "models", "base")
AIRFLOW_MODELS_CSV_FILE = os.path.join(AIRFLOW_DATA_FOLDER, "models", "model_list.csv")
AIRFLOW_TRAINING_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "training")
AIRFLOW_TRAINABLE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "trainable")
AIRFLOW_LABELBOX_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "labelbox")
AIRFLOW_LABEBOX_OUTPUT_DATA_FOLDER = os.path.join(AIRFLOW_LABELBOX_FOLDER, "output")
AIRFLOW_TF_RECORD_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "tfrecord")
TRAINING_ARCHIVING_PATH = os.path.join(AIRFLOW_DATA_FOLDER, "archive")
AIRFLOW_LOCAL_TRAINING_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "local_training")

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
project_struct = Variable.get("project_structure", deserialize_json=True)
gcp_base_bucket_url = f"gs://{Variable.get('bucket_name')}-training"
local_training = Variable.get("local_training")
epoch_count =  Variable.get("epoch_count")
batch_size =  Variable.get("batch_size")


def get_proper_model_config(model_name):
    model_config_variable = f"model_config_{model_name}"
    return Variable.get(model_config_variable)


def get_object_class_count():
    onthology_name = f"ontology"
    onthology = Variable.get(onthology_name, deserialize_json=True)
    return len(onthology["tools"])


dag = DAG(
    "5-prepare_model_and_data_for_training",
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
        "base_model_list": base_models,
    },
    trigger_rule="none_failed",
    dag=dag,
)

create_data_bucket_cmd = f"gsutil ls -b {gcp_base_bucket_url} || gsutil mb {gcp_base_bucket_url}"
create_data_bucket = BashOperator(
    task_id="create_data_bucket",
    bash_command=create_data_bucket_cmd,
    trigger_rule=TriggerRule.ALL_FAILED,
    dag=dag,
)

# clean_up_post_training_prep = PythonOperator(
#     task_id="clean_up_post_training_prep",
#     python_callable=prepare_model_and_data_for_training.clean_up_post_training_prep,
#     op_kwargs={
#         "folders": [
#             AIRFLOW_JSON_FOLDER,
#             AIRFLOW_LABELBOX_FOLDER,
#             AIRFLOW_TF_RECORD_FOLDER,
#             AIRFLOW_JSON_FOLDER,
#             AIRFLOW_TRAINING_FOLDER,
#         ]
#     },
#     trigger_rule=TriggerRule.ONE_SUCCESS,
#     dag=dag,
# )

upload_to_gcp_tasks = []
upload_local_tasks = []

for project in project_struct:
    check_labelmap_file_content_are_the_same = PythonOperator(
        task_id="check_labelmap_file_content_are_the_same_" + project,
        python_callable=prepare_model_and_data_for_training.compare_label_map_file,
        op_kwargs={"base_tf_record_folder": AIRFLOW_TF_RECORD_FOLDER, "datasets": project_struct[project]},
        dag=dag,
    )
    for base_model in base_models:

        create_training_folder_tree = PythonOperator(
            task_id="create_training_folder_tree_" + project + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.create_training_folder,
            provide_context=True,
            op_kwargs={
                "base_training_folder": AIRFLOW_TRAINING_FOLDER,
                "tf_record_folder": AIRFLOW_TF_RECORD_FOLDER,
                "project_name": project,
                "datasets": project_struct[project],
                "execution_date": "{{ts_nodash}}",
                "base_model": base_model,
            },
            dag=dag,
        )

        copy_labelbox_output_data_to_training_folder = PythonOperator(
            task_id="copy_labelbox_output_data_to_training_folder_"
            + project
            + "_"
            + base_model,
            python_callable=prepare_model_and_data_for_training.copy_labelbox_output_data_to_training,
            provide_context=True,
            op_kwargs={
                "labelbox_output_data_folder": AIRFLOW_LABEBOX_OUTPUT_DATA_FOLDER,
                "tf_record_folder": AIRFLOW_TF_RECORD_FOLDER,
                "project_name": project,
                "datasets": project_struct[project],
                "base_model": base_model,
                "airflow_base_folder": AIRFLOW_DATA_FOLDER,
                "airflow_training_folder": AIRFLOW_TRAINING_FOLDER,
                "gcp_base_bucket_url": gcp_base_bucket_url,
                "local_training_path": AIRFLOW_LOCAL_TRAINING_FOLDER,
                "local_training": local_training,
            },
            dag=dag,
        )

        copy_base_model_to_training_folder = PythonOperator(
            task_id="copy_base_model_to_training_folder_" + project + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.copy_base_model_to_training_folder,
            provide_context=True,
            op_kwargs={
                "base_model_csv": AIRFLOW_MODELS_CSV_FILE,
                "base_model_folder": AIRFLOW_MODELS_FOLDER,
                "project_name": project,
                "base_model": base_model,
                "airflow_base_folder": AIRFLOW_DATA_FOLDER,
                "airflow_training_folder": AIRFLOW_TRAINING_FOLDER,
                "local_training_folder": AIRFLOW_LOCAL_TRAINING_FOLDER,
                "gcp_base_bucket_url": gcp_base_bucket_url,
                "local_training": local_training,
            },
            dag=dag,
        )

        genereate_model_config = PythonOperator(
            task_id="genereate_model_config_" + project + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.generate_model_config,
            provide_context=True,
            op_kwargs={
                "project_name": project,
                "base_model": base_model,
                "model_config_template": get_proper_model_config(base_model),
                "num_classes": get_object_class_count(),
                "local_training": local_training,
                "epoch_count": epoch_count,
                "batch_size": batch_size,
            },
            dag=dag,
        )

        archiving_training_folder = PythonOperator(
            task_id="archiving_training_folder_" + project + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.archiving_training_folder,
            provide_context=True,
            op_kwargs={
                "training_archiving_path": TRAINING_ARCHIVING_PATH,
                "project_name": project,
                "base_model": base_model,
            },
            dag=dag,
        )

        remove_raw_images_and_annotations_from_training_folder = PythonOperator(
            task_id="remove_raw_images_and_annotations_from_training_folder_"
            + project
            + "_"
            + base_model,
            python_callable=prepare_model_and_data_for_training.remove_raw_images_and_annotations_from_training_folder,
            provide_context=True,
            op_kwargs={
                "project_name": project,
                "base_model": base_model,
                "gcp_base_bucket_url": gcp_base_bucket_url,
                "airflow_trainable_folder": AIRFLOW_TRAINABLE_FOLDER,
                "local_training": local_training,
                "local_training_folder": AIRFLOW_LOCAL_TRAINING_FOLDER,
            },
            dag=dag,
        )

        check_local_training_condition = PythonOperator(
            task_id="check_local_training_condition_id_" + project + "_" + base_model,
            python_callable=prepare_model_and_data_for_training.check_local_training_condition,
            provide_context=True,
            op_kwargs={
                "local_training": local_training,
            },
            dag=dag,
        )

        upload_training_folder_to_local_training = BashOperator(
            task_id="upload_training_folder_to_local_training_" + project + "_" + base_model,
            bash_command="{{{{ ti.xcom_pull(key='local_copy_cmd',task_ids='remove_raw_images_and_annotations_from_training_folder_{}_{}')}}}}".format(
                project, base_model
            ),
            trigger_rule=TriggerRule.ALL_SUCCESS,
            dag=dag,
            task_concurrency=1,
        )

        upload_training_folder_to_gcp_bucket = BashOperator(
            task_id="upload_training_folder_to_gcp_bucket_" + project + "_" + base_model,
            bash_command="{{{{ ti.xcom_pull(key='gcp_copy_cmd',task_ids='remove_raw_images_and_annotations_from_training_folder_{}_{}')}}}}".format(
                project, base_model
            ),
            dag=dag,
            task_concurrency=1,
        )

        # To fix parallelism error with gsutil
        upload_to_gcp_tasks.append(upload_training_folder_to_gcp_bucket)
        upload_local_tasks.append(upload_training_folder_to_local_training)

        start_task >> validate_reference_model_list_exist_or_create >> [
            validate_base_model_exist_or_download,
            download_reference_model_list_as_csv,
        ]
        download_reference_model_list_as_csv >> validate_base_model_exist_or_download
        validate_base_model_exist_or_download >> check_labelmap_file_content_are_the_same >> create_training_folder_tree
        create_training_folder_tree >> copy_labelbox_output_data_to_training_folder >> copy_base_model_to_training_folder
        copy_base_model_to_training_folder >> genereate_model_config >> archiving_training_folder
        archiving_training_folder >> remove_raw_images_and_annotations_from_training_folder >> join_task
        check_local_training_condition.set_upstream(join_task)

        # To fix parallelism error with gsutil
        for index, task in enumerate(upload_to_gcp_tasks):
            if index == 0:
                check_local_training_condition >> create_data_bucket
                create_data_bucket >> task
            else:
                upload_to_gcp_tasks[index - 1] >> task
        
        for index, task in enumerate(upload_local_tasks):
            if index == 0:
                check_local_training_condition >> task
            else:
                upload_local_tasks[index - 1] >> task

# clean_up_post_training_prep.set_upstream(upload_to_gcp_tasks[-1])
# clean_up_post_training_prep.set_upstream(upload_local_tasks[-1])