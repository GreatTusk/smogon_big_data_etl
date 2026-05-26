"""
smogon_ingest_chaos_dag.py — Chaos JSON ingestion DAG
Downloads chaos/*.json files and loads 8 tables into SQLite.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "smogon-pipeline",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}


def _ingest_chaos():
    from pipeline import ingest_chaos
    ingest_chaos.run()


with DAG(
    dag_id="smogon_ingest_chaos",
    default_args=default_args,
    description="Ingest Smogon chaos JSON into SQLite",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "chaos"],
) as dag:

    ingest_chaos = PythonOperator(
        task_id="ingest_chaos",
        python_callable=_ingest_chaos,
    )

    ingest_chaos
