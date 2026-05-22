"""
smogon_ingest_replays_dag.py — Replay ingestion DAG
Fetches Pokemon Showdown replays via the replay API.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "smogon-pipeline",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def _ingest_replays(**context):
    from pipeline.ingest_replays import run
    from pipeline.bigquery_client import execute_query
    formats = execute_query(
        "SELECT DISTINCT format_id FROM `smogon_staging.formats`"
    ) or []
    for fmt_row in formats:
        run(fmt_row["format_id"])
    print(f"Ingested replays for {len(formats)} formats")

with DAG(
    dag_id="smogon_ingest_replays",
    default_args=default_args,
    description="Ingest Pokemon Showdown replay data into BigQuery",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "replays"],
) as dag:

    ingest_replays = PythonOperator(
        task_id="ingest_replays",
        python_callable=_ingest_replays,
        provide_context=True,
    )

    ingest_replays
