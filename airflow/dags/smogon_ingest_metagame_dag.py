"""
smogon_ingest_metagame_dag.py — Metagame ingestion DAG
Downloads metagame/*.txt files and loads into SQLite.
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


def _ingest_metagame():
    from pipeline import ingest_metagame
    ingest_metagame.run()


with DAG(
    dag_id="smogon_ingest_metagame",
    default_args=default_args,
    description="Ingest Smogon metagame stats into SQLite",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "metagame"],
) as dag:

    ingest_metagame = PythonOperator(
        task_id="ingest_metagame",
        python_callable=_ingest_metagame,
    )

    ingest_metagame
