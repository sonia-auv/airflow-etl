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

from train_models_eGPU import train_models_eGPU
from utils import file_ops #, slack

AIRFLOW_BASE_FOLDER = "/home/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(AIRFLOW_BASE_FOLDER, "data")
AIRFLOW_TRAINABLE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "trainable")
AIRFLOW_LOCAL_TRAINING_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "local_training")

TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER = os.environ[
    "TENSORFLOW_OBJECT_DETECTION_RESEARCH"
]

#GCP_ZONE = Variable.get("gcp_zone")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
   # "on_failure_callback": slack.task_fail_slack_alert,
    "retries": 0,
}

tpu_supported_models = Variable.get("tpu_training_supported_models").split(",")
# distributed_training = Variable.get("distributed_training")

dag = DAG("7-train_models_eGPU", concurrency=1, default_args=default_args, catchup=False, schedule_interval=None)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


package_tensorflow_libs_cmd = f"cd {TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER} && object_detection/dataset_tools/create_pycocotools_package.sh /tmp/pycocotools && python setup.py sdist && (cd slim && python setup.py sdist)"

package_tensorflow_libs_with_dependencies = BashOperator(
    task_id="package_tensorflow_libs_with_dependencies",
    bash_command=package_tensorflow_libs_cmd,
    dag=dag,
)


for file in os.listdir(f"{AIRFLOW_LOCAL_TRAINING_FOLDER}"):

    if file == ".gitignore":
        continue
    
    training_name = file

    cd_obj_detect_api_cmd = f"cd {TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER}"
    job_dir = AIRFLOW_LOCAL_TRAINING_FOLDER + "/" + training_name
    packages = "dist/object_detection-0.1.tar.gz,slim/dist/slim-0.1.tar.gz,/tmp/pycocotools/pycocotools-2.0.tar.gz"
    module_name = "object_detection.model_main_tf2"
    model_dir = job_dir + "/train_data/"
    pipeline_config_path = f"{job_dir}/pipeline.config"
    checkpoint_dir = job_dir + "/eval_data/"
    frozen_dir = model_dir + "/frozen_path/"

    training_task_name = f"train_{training_name}"
    eval_task_name = f"eval_{training_name}"

    train_model_on_local_gpu_cmd = f"{cd_obj_detect_api_cmd} && python3 -m {module_name} --job-dir={job_dir} --package-path {packages} --model_dir={model_dir} --pipeline_config_path={pipeline_config_path} --alsologtostderr"
    #python3 -m object_detection.model_main_tf2 --job-dir=/home/airflow/data/local_training/simulateur2022_test_ssd_mobilenet_v2_fpnlite_640x640_20220417T151027 --package-path dist/object_detection-0.1.tar.gz,slim/dist/slim-0.1.tar.gz,/tmp/pycocotools/pycocotools-2.0.tar.gz --model_dir=/home/airflow/data/local_training/simulateur2022_test_ssd_mobilenet_v2_fpnlite_640x640_20220417T151027/train_data/ --pipeline_config_path=/home/airflow/data/local_training/simulateur2022_test_ssd_mobilenet_v2_fpnlite_640x640_20220417T151027/pipeline.config --alsologtostderr 
    #train_model_on_local_gpu_cmd = f"{cd_obj_detect_api_cmd} && gcloud ai-platform local train --module-name {module_name} --job-dir={job_dir} --package-path {packages} -- --model_dir={model_dir} --pipeline_config_path={pipeline_config_path}"

    train_model_on_local_gpu = BashOperator(
        task_id="train_model_" + training_name + "_on_local_gpu",
        bash_command=train_model_on_local_gpu_cmd,
        dag=dag,
    )

    delay_train_log_task = BashOperator(
        task_id="delay_train_log_" + training_name, bash_command="sleep 30s", dag=dag
    )

    delay_eval_task = BashOperator(
        task_id="delay_eval_" + training_name, bash_command="sleep 6m", dag=dag
    )

    eval_model_on_local_gpu_cmd = f"{cd_obj_detect_api_cmd} && python3 -m {module_name} --job-dir={job_dir} --package-path {packages} --model_dir={model_dir} --pipeline_config_path={pipeline_config_path} --checkpoint_dir={model_dir} --eval_training_data=True"

    eval_model_on_local_gpu = BashOperator(
        task_id="eval_model_" + training_name + "_on_local_gpu",
        bash_command=eval_model_on_local_gpu_cmd,
        dag=dag,
    )

    delay_eval_log_task = BashOperator(
        task_id="delay_eval_log_" + training_name, bash_command="sleep 30s", dag=dag
    )

    download_trained_model_cmd = ""
    download_trained_model = BashOperator(
        task_id="download_trained_model" + training_name,
        bash_command=download_trained_model_cmd,
        dag=dag,
    )

    export_frozen_graph_cmd = f"python object_detection/exporter_main_v2.py --input_type image_tensor --pipeline_config_path {pipeline_config_path} --trained_checkpoint_dir {model_dir} --output_directory {frozen_dir}"

    generate_model_frozen_graph_cmd = f"{cd_obj_detect_api_cmd} && {export_frozen_graph_cmd} "
    generate_model_frozen_graph = BashOperator(
        task_id="generate_model_frozen_graphl" + training_name,
        bash_command=generate_model_frozen_graph_cmd,
        dag=dag,
    )
    
    tensorboard_cmd = f"tensorboard --logdir {model_dir}:{checkpoint_dir}"
    #notify_slack_channel_with_tensorboard_cmd = slack.task_notify_training_in_progress(
    #    dag=dag, training_name=training_name, tensorboard_cmd=tensorboard_cmd
    #)

    # TODO: Create frozen_graph post training ---
    # TODO: Extract model name from training_name
    # TODO: Change checkpoint save frequency

    # TODO: Handle distributed training ---
    # TODO: Define model config.yaml
    # TODO: Export model to git or docker image for deploy ?
    start_task >> package_tensorflow_libs_with_dependencies
    package_tensorflow_libs_with_dependencies >> train_model_on_local_gpu
    train_model_on_local_gpu >> generate_model_frozen_graph >> [delay_train_log_task, delay_eval_task]
   # delay_train_log_task >> notify_slack_channel_with_tensorboard_cmd
   # delay_eval_task >> eval_model_on_local_gpu >> delay_eval_log_task >> notify_slack_channel_with_tensorboard_cmd
 #   notify_slack_channel_with_tensorboard_cmd >> end_task
