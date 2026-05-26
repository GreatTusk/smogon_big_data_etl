"""
smogon_ingest_replays_dag.py — Replay ingestion DAG
Fetches live replays from Pokemon Showdown API and loads into SQLite.
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


def _ingest_replays():
    from pipeline import ingest_replays
    ingest_replays.run()


with DAG(
    dag_id="smogon_ingest_replays",
    default_args=default_args,
    description="Ingest Pokemon Showdown replays into SQLite",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "replays"],
) as dag:

    ingest_replays = PythonOperator(
        task_id="ingest_replays",
        python_callable=_ingest_replays,
    )

    ingest_replays
