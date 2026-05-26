"""
smogon_ingest_leads_dag.py — Leads ingestion DAG
Downloads leads/*.txt files and loads into SQLite.
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


def _ingest_leads():
    from pipeline import ingest_leads
    ingest_leads.run()


with DAG(
    dag_id="smogon_ingest_leads",
    default_args=default_args,
    description="Ingest Smogon leads stats into SQLite",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "leads"],
) as dag:

    ingest_leads = PythonOperator(
        task_id="ingest_leads",
        python_callable=_ingest_leads,
    )

    ingest_leads
