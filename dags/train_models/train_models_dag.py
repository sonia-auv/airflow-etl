import os
import json
from datetime import datetime
from glob import glob

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

from train_models import train_models
from utils import file_ops, slack

AIRFLOW_BASE_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(AIRFLOW_BASE_FOLDER, "data")
AIRFLOW_TRAINABLE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "trainable")

TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER = os.environ[
    "TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER"
]

GCP_ZONE = Variable.get("gcp_zone")

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


tpu_supported_models = Variable.get("tpu_training_supported_models").split(",")
# distributed_training = Variable.get("distributed_training")

dag = DAG("6-train_model", default_args=default_args, catchup=False, schedule_interval=None)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


package_tensorflow_libs_cmd = f"cd {TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER} && object_detection/dataset_tools/create_pycocotools_package.sh /tmp/pycocotools && python setup.py sdist && (cd slim && python setup.py sdist)"

package_tensorflow_libs_with_dependencies = BashOperator(
    task_id="package_tensorflow_libs_with_dependencies",
    bash_command=package_tensorflow_libs_cmd,
    dag=dag,
)

for json_file in glob(f"{AIRFLOW_TRAINABLE_FOLDER}/*.json"):

    training_name = file_ops.get_filename(json_file, with_extension=False)
    now = datetime.now().strftime("%Y%m%dT%H%M")
    training_name_with_date = f"{training_name}_{now}"
    gcp_url = train_models.get_gcp_training_data_url(json_file)

    cd_obj_detect_api_cmd = f"cd {TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER}"
    job_dir = gcp_url + "/"
    packages = "dist/object_detection-0.1.tar.gz,slim/dist/slim-0.1.tar.gz,/tmp/pycocotools/pycocotools-2.0.tar.gz"
    module_name = "object_detection.model_main"
    runtime_version = "1.13"
    scale_tier = "BASIC_GPU"
    region = GCP_ZONE
    model_dir = gcp_url + "/train_data/"
    pipeline_config_path = f"{gcp_url}/pipeline.config"
    checkpoint_dir = gcp_url + "/eval_data/"

    training_task_name = f"train_{training_name}_{now}"
    eval_task_name = f"eval_{training_name}_{now}"

    train_model_on_basic_gpu_cmd = f"{cd_obj_detect_api_cmd} && gcloud ai-platform jobs submit training {training_task_name} --job-dir={job_dir} --packages {packages} --module-name {module_name} --runtime-version {runtime_version} --scale-tier {scale_tier} --region {region} -- --model_dir={model_dir} --pipeline_config_path={pipeline_config_path}"

    train_model_on_basic_gpu = BashOperator(
        task_id="train_model_" + training_name + "_on_basic_gpu",
        bash_command=train_model_on_basic_gpu_cmd,
        dag=dag,
    )

    delay_train_log_task = BashOperator(
        task_id="delay_train_log_" + training_name, bash_command="sleep 30s", dag=dag
    )

    display_train_model_logs_cmd = "gcloud ai-platform jobs stream-logs {training_task_name}"
    display_train_model_logs = BashOperator(
        task_id="display_train_model_logs_" + training_task_name,
        bash_command=display_train_model_logs_cmd,
        dag=dag,
    )

    delay_eval_task = BashOperator(
        task_id="delay_eval_" + training_name, bash_command="sleep 6m", dag=dag
    )

    eval_model_on_basic_gpu_cmd = f"{cd_obj_detect_api_cmd} && gcloud ai-platform jobs submit training {eval_task_name} --job-dir={job_dir} --packages {packages} --module-name {module_name} --runtime-version {runtime_version} --scale-tier {scale_tier} --region {region} -- --model_dir={model_dir} --pipeline_config_path={pipeline_config_path} --checkpoint_dir={checkpoint_dir}"

    eval_model_on_basic_gpu = BashOperator(
        task_id="eval_model_" + training_name + "_on_basic_gpu",
        bash_command=eval_model_on_basic_gpu_cmd,
        dag=dag,
    )

    delay_eval_log_task = BashOperator(
        task_id="delay_eval_log_" + training_name, bash_command="sleep 30s", dag=dag
    )

    display_eval_model_logs_cmd = "gcloud ai-platform jobs stream-logs {training_task_name}"
    display_eval_model_logs = BashOperator(
        task_id="display_eval_model_logs_" + eval_task_name,
        bash_command=display_eval_model_logs_cmd,
        dag=dag,
    )

    download_trained_model_cmd = ""
    download_trained_model = BashOperator(
        task_id="download_trained_model" + training_name,
        bash_command=download_trained_model_cmd,
        dag=dag,
    )

    export_frozen_graph_cmd = "python object_detection/export_inference_graph.py --input_type image_tensor --pipeline_config_path {downloaded_model_pipeline_config_path} --trained_checkpoint_prefix {trained_checkpoint_prefix} --output_directory {frozen_graph_export_directory}"

    generate_model_frozen_graph_cmd = "{cd_obj_detect_api_cmd} && {export_frozen_graph_cmd} "
    generate_model_frozen_graph = BashOperator(
        task_id="generate_model_frozen_graphl" + training_name,
        bash_command=generate_model_frozen_graph_cmd,
        dag=dag,
    )

    tensorboard_cmd = f"tensorboard --logdir {model_dir}:{checkpoint_dir}"
    notify_slack_channel_with_tensorboard_cmd = slack.task_notify_training_in_progress(
        dag=dag, training_name=training_name, tensorboard_cmd=tensorboard_cmd
    )

    # TODO: Create frozen_graph post training ---
    # TODO: Handle tpu training ---
    # TODO: Extract model name from training_name
    # TODO: Compare tpu_supported_models list content with model_name
    # TODO: Change checkpoint save frequency

    # TODO: Handle distributed training ---
    # TODO: Define model config.yaml
    # TODO: Export model to git or docker image for deploy ?
    start_task >> package_tensorflow_libs_with_dependencies
    package_tensorflow_libs_with_dependencies >> train_model_on_basic_gpu
    train_model_on_basic_gpu >> [delay_train_log_task, delay_eval_task]
    delay_train_log_task >> display_train_model_logs >> notify_slack_channel_with_tensorboard_cmd
    delay_eval_task >> eval_model_on_basic_gpu >> delay_eval_log_task >> display_eval_model_logs >> notify_slack_channel_with_tensorboard_cmd
    notify_slack_channel_with_tensorboard_cmd >> end_task
