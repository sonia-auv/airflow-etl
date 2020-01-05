import os
from datetime import datetime

from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

from utils import file_ops, slack

AIRFLOW_BASE_FOLDER = "/usr/local/airflow/"
AIRFLOW_DATA_FOLDER = os.path.join(AIRFLOW_BASE_FOLDER, "data")
AIRFLOW_TRAINABLE_FOLDER = os.path.join(AIRFLOW_DATA_FOLDER, "trainable")

TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER = os.environ[
    "TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER"
]

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

dag = DAG("train_model", default_args=default_args, catchup=False, schedule_interval=None)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


package_tensorflow_libs_cmd = f"cd {TENSORFLOW_OBJECT_DETECTION_RESEARCH_FOLDER} && object_detection/dataset_tools/create_pycocotools_package.sh /tmp/pycocotools && python setup.py sdist && (cd slim && python setup.py sdist)"

package_tensorflow_libs_with_dependencies = BashOperator(
    task_id="package_tensorflow_libs_with_dependencies",
    bash_command=package_tensorflow_libs_cmd,
    dag=dag,
)

start_task >> package_tensorflow_libs_with_dependencies >> end_task


# gcloud ai-platform jobs submit training $1_`date +%s` --job-dir=gs://sonia-test/training/$1/model/ --packages dist/object_detection-0.1.tar.gz,slim/dist/slim-0.1.tar.gz,/tmp/pycocotools/pycocotools-2.0.tar.gz --module-name object_detection.model_tpu_main --runtime-version 1.13 --scale-tier BASIC_TPU --region us-central1 -- --model_dir=gs://sonia-test/training/$1/model/ --pipeline_config_path=gs://sonia-test/training/$1/data/pipeline.config --tpu_zone us-central1
