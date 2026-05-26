"""
smogon_ingest_usage_dag.py — Usage stats ingestion DAG
Downloads usage .txt files for discovered sources and loads into SQLite.
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


def _ingest_usage():
    from pipeline import ingest_usage
    ingest_usage.run()
    from pipeline.db import get_conn
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM discovered_sources WHERE source_type = 'usage' "
            "AND (month, format_id, elo_tier) NOT IN ("
            "  SELECT DISTINCT month, format_id, elo_tier FROM usage_stats"
            ")"
        ).fetchone()[0]
    return count


with DAG(
    dag_id="smogon_ingest_usage",
    default_args=default_args,
    description="Ingest Smogon usage statistics into SQLite",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "usage"],
) as dag:

    ingest = PythonOperator(
        task_id="ingest_usage",
        python_callable=_ingest_usage,
    )

    ingest
