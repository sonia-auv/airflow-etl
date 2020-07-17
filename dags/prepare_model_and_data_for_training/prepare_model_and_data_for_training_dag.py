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

AIRFLOW_ROOT_FOLDER = "/usr/local/airflow/"
DATA_FOLDER = os.path.join(AIRFLOW_ROOT_FOLDER, "data")
MODELS_FOLDER = os.path.join(DATA_FOLDER, "models", "base")
MODELS_CSV_FILE = os.path.join(DATA_FOLDER, "models", "model_list.csv")
TRAINING_FOLDER = os.path.join(DATA_FOLDER, "training")
LABELBOX_FOLDER = os.path.join(DATA_FOLDER, "labelbox")
LABELBOX_OUTPUT_FOLDER = os.path.join(LABELBOX_FOLDER, "output")
TF_RECORD_FOLDER = os.path.join(DATA_FOLDER, "tfrecord")
DVC_FOLDER = os.path.join(DATA_FOLDER, "dvc")
MODEL_REPO_FOLDER = os.path.join(DVC_FOLDER, "deep-detector-model")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": slack.task_fail_slack_alert,
    "retries": 2,
}


# Variables
tensorflow_model_zoo_markdown_url = Variable.get("tensorflow_model_zoo_markdown_url")
required_base_models = Variable.get("tensorflow_model_zoo_models").split(",")
video_feed_sources = Variable.get("video_feed_sources").split(",")

gcp_base_bucket_url = f"gs://{Variable.get('bucket_name')}-training"
gcp_base_dvc_bucket_url = f"gs://{Variable.get('bucket_name')}-dvc/"

model_repo_dvc_remote_name = BaseHook.get_connection("model_repo_dvc").host
model_repo_git_remote_url = BaseHook.get_connection("model_repo_git").host


upload_tasks = []


# DAG Specific Methods
def get_proper_model_config(video_source, model_name):
    model_config_variable = f"model_config_{video_source}_{model_name}"
    return Variable.get(model_config_variable)


def get_object_class_count(video_source):
    onthology_name = f"ontology_{video_source}"
    onthology = Variable.get(onthology_name, deserialize_json=True)
    return len(onthology["tools"])


dag = DAG(
    "5-prepare_model_and_data_for_training",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
)

start_task = DummyOperator(task_id="start_task", dag=dag)
join_task_1 = DummyOperator(task_id="join_task_1", dag=dag)
join_task_2 = DummyOperator(task_id="join_task_2", dag=dag)
join_task_3 = DummyOperator(task_id="join_task_3", dag=dag)
join_task_4 = DummyOperator(task_id="join_task_4", dag=dag)
join_task_5 = DummyOperator(task_id="join_task_5", dag=dag)

validate_reference_model_list_exist_or_create = BranchPythonOperator(
    task_id="validate_reference_model_list_exist",
    python_callable=prepare_model_and_data_for_training.validate_reference_model_list_exist_or_create,
    op_kwargs={
        "base_model_csv": MODELS_CSV_FILE,
        "positive_downstream": "validate_base_model_exist_or_download",
        "negative_downstream": "download_reference_model_list_as_csv",
    },
    dag=dag,
)

download_reference_model_list_as_csv = PythonOperator(
    task_id="download_reference_model_list_as_csv",
    python_callable=prepare_model_and_data_for_training.download_reference_model_list_as_csv,
    op_kwargs={"url": tensorflow_model_zoo_markdown_url, "base_model_csv": MODELS_CSV_FILE},
    dag=dag,
)


validate_base_model_exist_or_download = PythonOperator(
    task_id="validate_base_model_exist_or_download",
    python_callable=prepare_model_and_data_for_training.download_and_extract_base_model,
    op_kwargs={
        "base_model_csv": MODELS_CSV_FILE,
        "base_model_folder": MODELS_FOLDER,
        "required_base_models": required_base_models,
    },
    trigger_rule="none_failed",
    dag=dag,
)

validate_requested_model_exist_in_model_zoo_list = PythonOperator(
    task_id="validate_requested_model_exist_in_model_zoo_list",
    python_callable=prepare_model_and_data_for_training.validate_requested_model_exist_in_model_zoo_list,
    op_kwargs={"base_models_csv": MODELS_CSV_FILE, "required_base_models": required_base_models,},
    dag=dag,
)

validate_deep_detector_model_repo_exist_or_clone = BashOperator(
    task_id="validate_deep_detector_model_repo_exist_or_clone",
    bash_command="[ -d '{{params.model_repo_folder}}' ] || git clone -v {{params.model_repo_url}} {{params.model_repo_folder}}",
    params={"model_repo_folder": MODEL_REPO_FOLDER, "model_repo_url": model_repo_git_remote_url,},
    provide_context=True,
    dag=dag,
)

validate_deep_detector_dvc_remote_credential_present_or_add = BashOperator(
    task_id="validate_deep_detector_dvc_remote_credential_present_or_add",
    bash_command="\
        [ -s '{{params.model_repo_folder}}/.dvc/config' ] || cd {{params.model_repo_folder}} && \
        dvc init && \
        dvc remote add {{params.model_repo_dvc_remote_name}} {{params.dvc_remote_url}} --default && \
        cat {{params.model_repo_folder}}/.dvc/config",
    params={
        "model_repo_folder": MODEL_REPO_FOLDER,
        "model_repo_dvc_remote_name": model_repo_dvc_remote_name,
        "dvc_remote_url": gcp_base_dvc_bucket_url,
    },
    dag=dag,
)

# This task is declared before since it will be added after dynamic tasks
create_training_data_bucket = BashOperator(
    task_id="create_training_data_bucket",
    bash_command="gsutil ls -b {{params.gcp_base_bucket_url}} || gsutil mb {{params.gcp_base_bucket_url}}",
    provide_context=True,
    params={"gcp_base_bucket_url": gcp_base_bucket_url},
    dag=dag,
)

# This task is declared before since it will be added after dynamic tasks
create_dvc_data_bucket = BashOperator(
    task_id="create_dvc_data_bucket",
    bash_command="gsutil ls -b {{params.gcp_base_dvc_bucket_url}} || gsutil mb {{params.gcp_base_dvc_bucket_url}}",
    provide_context=True,
    params={"gcp_base_dvc_bucket_url": gcp_base_dvc_bucket_url},
    dag=dag,
)


# This task is declared before since it will be added after dynamic tasks
upload_data_to_dvc_repo_and_git = BashOperator(
    task_id=f"upload_data_to_dvc_repo_and_git",
    bash_command="cd {{params.model_repo_folder}} && \
                          git push && \
                          dvc push",
    params={"model_repo_folder": MODEL_REPO_FOLDER},
    dag=dag,
)


# Add sleep duration list to delay task (dvc lock file)
sleeps = [item * 20 for item in range(1, len(video_feed_sources) * len(required_base_models))]

for idx1, video_source in enumerate(video_feed_sources):
    validate_labelmap_file_content_are_the_same = PythonOperator(
        task_id=f"check_labelmap_file_content_are_the_same_" + video_source,
        python_callable=prepare_model_and_data_for_training.compare_label_map_file,
        op_kwargs={"base_tf_record_folder": TF_RECORD_FOLDER, "video_source": video_source},
        dag=dag,
    )
    for idx2, base_model in enumerate(required_base_models):

        sleep_duration = sleeps[idx1 + idx2]
        execution_date = "{{ts_nodash}}"

        model_folder = f"{video_source}_{base_model}"
        model_folder_with_ts = f"{model_folder}_{execution_date}"

        model_training_folder = f"{TRAINING_FOLDER}/{model_folder_with_ts}"
        model_training_images_folder = f"{model_training_folder}/data/images"
        model_training_tf_records_folder = f"{model_training_folder}/data/tf_records"
        model_training_base_model_folder = f"{model_training_folder}/model/base"

        model_repo_folder = f"{MODEL_REPO_FOLDER}/{model_folder}"
        model_repo_images_folder = f"{model_repo_folder}/data/images"
        model_repo_annotations_folder = f"{model_repo_folder}/data/annotations/xmls"
        model_repo_tf_records_folder = f"{model_repo_folder}/data/tf_records"
        model_repo_base_model_folder = f"{model_repo_folder}/model/base"

        model_config_training_epoch_count = Variable.get(
            f"model_config_{video_source}_{base_model}_training_epoch_count"
        )
        model_config_training_batch_size = Variable.get(
            f"model_config_{video_source}_{base_model}_training_batch_size"
        )

        validate_model_presence_in_model_repo_or_create = PythonOperator(
            task_id=f"validate_model_{video_source}_{base_model}_present_in_model_repo_or_create",
            python_callable=prepare_model_and_data_for_training.validate_model_presence_in_model_repo_or_create,
            op_kwargs={"model_repo_folder": model_repo_folder},
            dag=dag,
        )

        create_training_folder = PythonOperator(
            task_id=f"create_training_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.create_training_folder,
            op_kwargs={"model_training_folder": model_training_folder},
            dag=dag,
        )

        copy_labelbox_output_images_to_training_folder = PythonOperator(
            task_id=f"copy_labelbox_output_images_to_training_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_labelbox_output_images_to_training_folder,
            op_kwargs={
                "labelbox_output_folder": LABELBOX_OUTPUT_FOLDER,
                "model_training_images_folder": model_training_images_folder,
                "video_source": video_source,
            },
            dag=dag,
        )

        copy_labelbox_output_images_to_model_repo_folder = PythonOperator(
            task_id=f"copy_labelbox_output_images_to_model_repo_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_labelbox_output_images_to_model_repo_folder,
            op_kwargs={
                "labelbox_output_folder": LABELBOX_OUTPUT_FOLDER,
                "model_repo_images_folder": model_repo_images_folder,
                "video_source": video_source,
            },
            dag=dag,
        )

        add_images_to_repo_through_dvc = BashOperator(
            task_id=f"add_images_to_repo_through_dvc_{video_source}_{base_model}",
            bash_command="sleep {{params.sleep_duration}} && \
                          cd {{params.model_repo_folder}} && \
                          dvc add data/images/* && \
                          git add data/images/.gitignore data/images/*.dvc && \
                          git commit -m 'Add images to {{params.model_folder}}'",
            provide_context=True,
            params={
                "model_repo_folder": model_repo_folder,
                "model_folder": model_folder,
                "sleep_duration": sleep_duration,
            },
            dag=dag,
        )

        copy_labelbox_output_annotations_to_model_repo_folder = PythonOperator(
            task_id=f"copy_labelbox_output_annotations_to_model_repo_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_labelbox_output_annotations_to_model_repo_folder,
            op_kwargs={
                "labelbox_output_folder": LABELBOX_OUTPUT_FOLDER,
                "model_repo_annotations_folder": model_repo_annotations_folder,
                "video_source": video_source,
            },
            dag=dag,
        )

        add_annotations_to_repo_through_dvc = BashOperator(
            task_id=f"add_annotations_to_repo_through_dvc_{video_source}_{base_model}",
            bash_command="sleep {{params.sleep_duration}} && \
                          cd {{params.model_repo_folder}} && \
                          dvc add data/annotations/xmls/* && \
                          git add data/annotations/xmls/.gitignore data/annotations/xmls/*.dvc && \
                          git commit -m 'Add annotations to {{params.model_folder}}'",
            provide_context=True,
            params={
                "model_repo_folder": model_repo_folder,
                "model_folder": model_folder,
                "sleep_duration": sleep_duration,
            },
            dag=dag,
        )

        copy_tf_records_to_training_folder = PythonOperator(
            task_id=f"copy_tf_records_to_training_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_tf_records_to_training_folder,
            op_kwargs={
                "tf_records_folder": TF_RECORD_FOLDER,
                "model_training_tf_records_folder": model_training_tf_records_folder,
                "video_source": video_source,
            },
            dag=dag,
        )

        copy_tf_records_to_model_repo_folder = PythonOperator(
            task_id=f"copy_tf_records_to_model_repo_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_tf_records_to_model_repo,
            op_kwargs={
                "tf_records_folder": TF_RECORD_FOLDER,
                "model_repo_tf_records_folder": model_repo_tf_records_folder,
                "video_source": video_source,
            },
            dag=dag,
        )

        add_tf_records_to_repo_through_dvc = BashOperator(
            task_id=f"add_tf_records_to_repo_through_dvc_{video_source}_{base_model}",
            bash_command="sleep {{params.sleep_duration}} && \
                          cd {{params.model_repo_folder}} && \
                          dvc add data/tf_records/train/* && \
                          dvc add data/tf_records/val/* && \
                          git add data/tf_records/train/.gitignore data/tf_records/train/*.dvc && \
                          git add data/tf_records/val/.gitignore data/tf_records/val/*.dvc && \
                          git add data/tf_records/trainval.txt data/tf_records/labelmap.pbtxt &&\
                          git commit -m 'Add tf-records to {{params.model_folder}}'",
            provide_context=True,
            params={
                "model_repo_folder": model_repo_folder,
                "model_folder": model_folder,
                "sleep_duration": sleep_duration,
            },
            dag=dag,
        )

        copy_base_model_to_training_folder = PythonOperator(
            task_id=f"copy_base_model_to_training_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_base_model_to_training_folder,
            op_kwargs={
                "base_model": base_model,
                "base_model_csv": MODELS_CSV_FILE,
                "base_model_folder": MODELS_FOLDER,
                "model_training_base_model_folder": model_training_base_model_folder,
            },
            dag=dag,
        )

        copy_base_model_to_model_repo_folder = PythonOperator(
            task_id=f"copy_base_model_to_model_repo_folder_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.copy_base_model_to_model_repo_folder,
            op_kwargs={
                "base_model": base_model,
                "base_model_csv": MODELS_CSV_FILE,
                "base_model_folder": MODELS_FOLDER,
                "model_repo_base_model_folder": model_repo_base_model_folder,
            },
            dag=dag,
        )

        add_base_model_to_repo_through_dvc = BashOperator(
            task_id=f"add_base_model_to_repo_through_dvc_{video_source}_{base_model}",
            bash_command="sleep {{params.sleep_duration}} && \
                          cd {{params.model_repo_folder}} && \
                          dvc add model/base/* && \
                          git add model/base/.gitignore model/base/*.dvc && \
                          git commit -m 'Add base model file to {{params.model_folder}}'",
            provide_context=True,
            params={
                "model_repo_folder": model_repo_folder,
                "model_folder": model_folder,
                "sleep_duration": sleep_duration,
            },
            dag=dag,
        )

        genereate_model_config_file_to_training_and_model_repo = PythonOperator(
            task_id=f"genereate_model_config_file_to_training_and_model_repo_{video_source}_{base_model}",
            python_callable=prepare_model_and_data_for_training.generate_model_config,
            op_kwargs={
                "model_training_folder": model_training_folder,
                "model_repo_folder": model_repo_folder,
                "model_folder_ts": model_folder_with_ts,
                "model_config_template": get_proper_model_config(video_source, base_model),
                "num_classes": get_object_class_count(video_source),
                "bucket_url": gcp_base_bucket_url,
                "training_batch_size": model_config_training_batch_size,
                "training_epoch_count": model_config_training_epoch_count,
            },
            dag=dag,
        )

        add_model_config_to_repo_through_git = BashOperator(
            task_id=f"add_model_config_to_repo_through_git_{video_source}_{base_model}",
            bash_command="sleep {{params.sleep_duration }} && \
                          cd {{params.model_repo_folder}} && \
                          git add pipeline.config  && \
                          git commit -m 'Add model config to {{params.model_folder}}'",
            provide_context=True,
            params={
                "model_repo_folder": model_repo_folder,
                "model_folder": model_folder,
                "sleep_duration": sleep_duration * 1.5,
            },
            dag=dag,
        )
        upload_training_folder_to_gcp_bucket = BashOperator(
            task_id=f"upload_training_folder_to_gcp_bucket_{video_source}_{base_model}",
            bash_command="gsutil -m cp -r {{params.model_training_folder}}_{{ts_nodash}}  {{params.bucket_url}}_{{ts_nodash}}",
            provide_context=True,
            params={
                "model_training_folder": f"{TRAINING_FOLDER}/{model_folder}",
                "bucket_url": f"{gcp_base_bucket_url}/{model_folder}",
            },
            dag=dag,
        )

        start_task >> validate_reference_model_list_exist_or_create >> [
            validate_base_model_exist_or_download,
            download_reference_model_list_as_csv,
        ]
        download_reference_model_list_as_csv >> validate_base_model_exist_or_download >> validate_requested_model_exist_in_model_zoo_list
        validate_requested_model_exist_in_model_zoo_list >> validate_deep_detector_model_repo_exist_or_clone >> validate_deep_detector_dvc_remote_credential_present_or_add >> validate_labelmap_file_content_are_the_same

        validate_labelmap_file_content_are_the_same >> validate_model_presence_in_model_repo_or_create >> create_training_folder >> copy_labelbox_output_images_to_training_folder >> copy_labelbox_output_images_to_model_repo_folder >> add_images_to_repo_through_dvc >> join_task_1 >> copy_labelbox_output_annotations_to_model_repo_folder >> add_annotations_to_repo_through_dvc >> join_task_2 >> copy_tf_records_to_training_folder >> copy_tf_records_to_model_repo_folder >> add_tf_records_to_repo_through_dvc >> join_task_3 >> copy_base_model_to_training_folder >> copy_base_model_to_model_repo_folder >> add_base_model_to_repo_through_dvc >> join_task_4 >> genereate_model_config_file_to_training_and_model_repo >> add_model_config_to_repo_through_git >> join_task_5

        upload_tasks.append(upload_training_folder_to_gcp_bucket)


# To fix parallelism error with gsutil
if len(set(upload_tasks)) == len(required_base_models) * 2:
    for index, task in enumerate(upload_tasks):
        if index == 0:
            join_task_5 >> create_training_data_bucket >> create_dvc_data_bucket >> task
        else:
            upload_tasks[index - 1] >> task

    upload_tasks[-1] >> upload_data_to_dvc_repo_and_git
else:
    raise ValueError("There is a duplicate entry in the tensorflow_model_zoo_models variable")
