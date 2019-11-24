from airflow import DAG
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator


dag = DAG("train_model", default_args=default_args, catchup=False)

start_task = DummyOperator(task_id="start_task", dag=dag)
end_task = DummyOperator(task_id="end_task", dag=dag)


# for index, json_file in enumerate(json_files):

# TODO: Compare labelbox
# TODO: Download required models
# TODO: Generate training config file
# TODO: Launch model training
# TODO: Launch model eval
