"""
 This DAG will extract labeled dataset from labelbox or unity simulator and generate tf_record
"""

import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.models import Variable

from create_tf_record_from_labaled_data import create_tf_record_from_labaled_data
from utils import file_ops

ROOT_FOLDER = "/usr/local/airflow/data/"

JSON_FOLDER = os.path.join(ROOT_FOLDER, "json/")
TRAIN_JSON_FOLDER = os.path.join(ROOT_FOLDER, "train_json/")
VOC_FOLDER = os.path.join(ROOT_FOLDER, "voc/")
TF_RECORD_FOLDER = os.path.join(ROOT_FOLDER, "tfrecords/")
TRAIN_IMG_FOLDER = os.path.join(ROOT_FOLDER, "train_images/")
LABEL_MAP_FOLDER = os.path.join(ROOT_FOLDER, "label_map/")
TRAINVAL_FOLDER = os.path.join(ROOT_FOLDER, "trainval/")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}


with DAG("create_tf_record_from_labaled_data", catchup=False, default_args=default_args) as dag:
    # Get Admin variables
    
    trainset = Variable.get("Trainset")

    # Extract topics list
    datasets_string = Variable.get("Dataset_to_Trainset")
    datasets = datasets_string.split(",")

    # Build folder paths
    for i in range(len(datasets)):
        datasets[i] = JSON_FOLDER + datasets[i] + ".json"
    json_path = os.path.join(TRAIN_JSON_FOLDER, trainset) + ".json"
    voc_path = os.path.join(VOC_FOLDER, trainset)
    train_img_path = os.path.join(TRAIN_IMG_FOLDER, trainset)
    tf_record_path = os.path.join(TF_RECORD_FOLDER, trainset)
    label_map_path = os.path.join(LABEL_MAP_FOLDER, trainset) + ".pbtxt"
    trainval_path = os.path.join(TRAINVAL_FOLDER, trainset) + ".txt"

    #create missing directories
    if not os.path.exists(str(voc_path)):
        os.mkdir(str(voc_path))

    if not os.path.exists(str(train_img_path)):
        os.mkdir(str(train_img_path))

    task_notify_start = SlackAPIPostOperator(
        task_id="task_notify_start",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=" :dolphin:[PROCESSING] DAG (create_tf_record_from_labaled_data): create tf_record",
        dag=dag,
    )

    task_json_concat = PythonOperator(
        task_id="task_json_concat",
        python_callable=file_ops.concat_json,
        op_kwargs={"json_files": datasets, "output_path": json_path},
        dag=dag,
    )

    command = "cd /usr/local/airflow/dags/create_tf_record_from_labaled_data/; python3 -c \"import lb.exporters.voc_exporter as lb2pa; lb2pa.from_json(\'{json_file}\', \'{voc_dir}\', \'{image_dir}\', label_format='XY')\"".format(
        json_file=json_path, voc_dir=voc_path, image_dir=train_img_path
    )

    task_json_to_voc = BashOperator(
        task_id="task_json_to_voc", bash_command=command, dag=dag
    )

    task_create_trainval = PythonOperator(
        task_id="task_create_trainval",
        python_callable=create_tf_record_from_labaled_data.generate_trainval_file,
        op_kwargs={
            "annotation_dir": voc_path, 
            "output_file": trainval_path
        },
        dag=dag,
    )

    command = "python /usr/local/airflow/dags/create_tf_record_from_labaled_data/create_tf_record.py --annotation_dir={voc_dir} --image_dir={img_dir} --label_map_file={label_map_path} --trainval_file={trainval_path} --output_dir={tf_dir}".format(
        voc_dir=voc_path, img_dir=train_img_path, tf_dir=tf_record_path, label_map_path=label_map_path, trainval_path=trainval_path
    )

    task_voc_to_tf = BashOperator(
        task_id="task_voc_to_tf", bash_command=command, dag=dag
    )

    task_notify_extraction_success = SlackAPIPostOperator(
        task_id="task_notify_extraction_success",
        channel="#airflow",
        token="xoxp-6204505398-237247190021-380986807988-97ab748d120f996289f735c370cbac46",
        text=":heavy_check_mark: [SUCCESS] DAG (create_tf_record_from_labaled_data): succeed to create tf_record",
        trigger_rule="all_success",
        dag=dag,
    )

    task_notify_start >> task_json_concat >> task_json_to_voc >> task_create_trainval >> task_voc_to_tf >> task_notify_extraction_success
