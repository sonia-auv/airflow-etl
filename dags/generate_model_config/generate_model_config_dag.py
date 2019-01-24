"""
 This DAG will extract labeled dataset from labelbox or unity simulator and generate tf_record
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.slack_operator import SlackAPIPostOperator


INPUT_DATA_LOCATION = ""
STATING_DATA_LOCATION = ""
OUTPUT_DATA_LOCATION = ""

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2019, 1, 24),
    "email": ["club.sonia@etsmtl.net"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}


with DAG("generate_model_config", catchup=False, default_args=default_args) as dag:
    # t1, t2 and t3 are examples of tasks created by instantiating operators

    # TODO: Generate model config
    # TODO: Package training into git

    t1 = BashOperator(task_id="print_date", bash_command="date", dag=dag)

    t2 = BashOperator(task_id="sleep", bash_command="sleep 5", retries=3, dag=dag)

    templated_command = """
        {% for i in range(5) %}
            echo "{{ ds }}"
            echo "{{ macros.ds_add(ds, 7)}}"
            echo "{{ params.my_param }}"
        {% endfor %}
    """

    t3 = BashOperator(
        task_id="templated",
        bash_command=templated_command,
        params={"my_param": "Parameter I passed in"},
        dag=dag,
    )

    t2.set_upstream(t1)
    t3.set_upstream(t1)
