"""
smogon_master_dag.py — Master orchestrator DAG
Triggers individual step DAGs in sequence using TriggerDagRunOperator.
Scheduled monthly on the 1st at 6:00 AM.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.dummy import DummyOperator

default_args = {
    "owner": "smogon-pipeline",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="smogon_master",
    default_args=default_args,
    description="Master orchestrator for Smogon ETL pipeline",
    schedule_interval="0 6 1 * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "master"],
    max_active_runs=1,
) as dag:

    start = DummyOperator(task_id="start")
    end = DummyOperator(task_id="end")

    discover = TriggerDagRunOperator(
        task_id="trigger_discover",
        trigger_dag_id="smogon_discover",
        wait_for_completion=True,
        allowed_states=["success"],
        trigger_rule="all_done",
    )

    ingest_usage = TriggerDagRunOperator(
        task_id="trigger_ingest_usage",
        trigger_dag_id="smogon_ingest_usage",
        wait_for_completion=True,
        allowed_states=["success"],
    )

    ingest_chaos = TriggerDagRunOperator(
        task_id="trigger_ingest_chaos",
        trigger_dag_id="smogon_ingest_chaos",
        wait_for_completion=True,
        allowed_states=["success"],
    )

    ingest_leads = TriggerDagRunOperator(
        task_id="trigger_ingest_leads",
        trigger_dag_id="smogon_ingest_leads",
        wait_for_completion=True,
        allowed_states=["success"],
    )

    ingest_metagame = TriggerDagRunOperator(
        task_id="trigger_ingest_metagame",
        trigger_dag_id="smogon_ingest_metagame",
        wait_for_completion=True,
        allowed_states=["success"],
    )

    ingest_replays = TriggerDagRunOperator(
        task_id="trigger_ingest_replays",
        trigger_dag_id="smogon_ingest_replays",
        wait_for_completion=True,
        allowed_states=["success"],
    )

    start >> discover >> ingest_usage >> ingest_chaos >> ingest_leads >> ingest_metagame >> ingest_replays >> end
