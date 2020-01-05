from airflow.hooks.base_hook import BaseHook
from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator

SLACK_CONN_ID = "slack"


def task_fail_slack_alert(context):
    slack_webhook_token = BaseHook.get_connection(SLACK_CONN_ID).password
    slack_msg = """
            :red_circle: Task Failed.
            *Task*: {task}
            *Dag*: {dag}
            *Execution Time*: {exec_date}
            *Log Url*: {log_url}
            """.format(
        task=context.get("task_instance").task_id,
        dag=context.get("task_instance").dag_id,
        ti=context.get("task_instance"),
        exec_date=context.get("execution_date"),
        log_url=context.get("task_instance").log_url,
    )
    failed_alert = SlackWebhookOperator(
        task_id="slack_task_error",
        http_conn_id="slack",
        webhook_token=slack_webhook_token,
        message=slack_msg,
        username="airflow",
    )
    return failed_alert.execute(context=context)


def dag_notify_start_slack_alert(dag):
    slack_webhook_token = BaseHook.get_connection(SLACK_CONN_ID).password
    slack_msg = """
            :dolphin: DAG Started
            *Dag*: {dag}
            """.format(
        dag=dag.dag_id,
    )
    success_alert = SlackWebhookOperator(
        task_id="notify_dag_start",
        http_conn_id="slack",
        webhook_token=slack_webhook_token,
        message=slack_msg,
        username="airflow",
        dag=dag,
    )
    return success_alert


def dag_notify_success_slack_alert(dag):
    slack_webhook_token = BaseHook.get_connection(SLACK_CONN_ID).password
    slack_msg = """
            :white_check_mark: DAG Completed.
            *Dag*: {dag}
            """.format(
        dag=dag.dag_id,
    )
    success_alert = SlackWebhookOperator(
        task_id="notify_dag_success",
        http_conn_id="slack",
        webhook_token=slack_webhook_token,
        message=slack_msg,
        username="airflow",
        trigger_rule="all_success",
        dag=dag,
    )
    return success_alert

    def task_notify_training_in_progress(dag, training_name, tensorboard_url):
        slack_webhook_token = BaseHook.get_connection(SLACK_CONN_ID).password
        slack_msg = """
                :hourglass: Training in progress.
                *Task*: {task}
                *Dag*: {dag}
                *Execution Time*: {exec_date}
                *Log Url*: {log_url}
                *Tensorboard Url*: {tensorboard_url}
                """.format(
            dag=dag.dag_id, tensorboard_url=tensorboard_url,
        )
        training_alert = SlackWebhookOperator(
            task_id="slack_task_training_in_progress_{training_name}",
            http_conn_id="slack",
            webhook_token=slack_webhook_token,
            message=slack_msg,
            username="airflow",
        )
        return training_alert
