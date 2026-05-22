"""
smogon_ingest_usage_dag.py — Usage stats ingestion DAG
Downloads usage .txt files for discovered sources, parses, and loads to BigQuery.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook

default_args = {
    "owner": "smogon-pipeline",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}

def _get_pending_sources(**context):
    from pipeline.bigquery_client import execute_query
    sql = """
    SELECT month, format_id, elo_tier
    FROM `smogon_raw.discovered_sources`
    WHERE source_type = 'usage'
      AND (month, format_id, elo_tier) NOT IN (
        SELECT DISTINCT month, format_id, elo_tier
        FROM `smogon_raw.usage_stats`
      )
    ORDER BY month DESC
    LIMIT 20
    """
    rows = execute_query(sql) or []
    return [dict(r) for r in rows]

def _ingest_one_source(source: dict, **context):
    from pipeline.ingest_usage import run
    run(source["month"], source["format_id"], source["elo_tier"])

def _ingest_all_sources(**context):
    from pipeline.bigquery_client import execute_query
    sources = _get_pending_sources(**context)
    if not sources:
        print("No pending usage sources to ingest")
        return 0
    for src in sources:
        _ingest_one_source(src)
    print(f"Ingested {len(sources)} usage sources")

with DAG(
    dag_id="smogon_ingest_usage",
    default_args=default_args,
    description="Ingest Smogon usage statistics into BigQuery",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "usage"],
) as dag:

    ingest_usage = PythonOperator(
        task_id="ingest_usage",
        python_callable=_ingest_all_sources,
        provide_context=True,
    )

    ingest_usage
