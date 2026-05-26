"""
smogon_ingest_chaos_dag.py — Chaos JSON ingestion DAG
Downloads chaos JSON files, parses all sub-sections, loads to BigQuery.
Defaults to gen9ou when no format is specified.
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

def _get_format(**context):
    dag_conf = context.get("dag_run", {}).conf if context.get("dag_run") else {}
    return dag_conf.get("format", "gen9ou")

def _get_pending_sources(**context):
    from pipeline.bigquery_client import execute_query
    from pipeline import config
    fmt = _get_format(**context)
    sql = f"""
    SELECT month, format_id, elo_tier
    FROM `{config.PROJECT_ID}.{config.RAW_DATASET}.discovered_sources`
    WHERE source_type = 'chaos'
      AND format_id = '{fmt}'
      AND (month, format_id, elo_tier) NOT IN (
        SELECT DISTINCT month, format_id, elo_tier
        FROM `{config.PROJECT_ID}.{config.RAW_DATASET}.chaos_json`
      )
    ORDER BY month DESC
    LIMIT 10
    """
    rows = execute_query(sql) or []
    return [dict(r) for r in rows]

def _ingest_chaos(**context):
    from pipeline.ingest_chaos import run
    sources = _get_pending_sources(**context)
    if not sources:
        print("No pending chaos sources to ingest")
        return
    for src in sources:
        run(src["month"], src["format_id"], src["elo_tier"])
    print(f"Ingested {len(sources)} chaos sources")

with DAG(
    dag_id="smogon_ingest_chaos",
    default_args=default_args,
    description="Ingest Smogon chaos JSON into BigQuery",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "chaos"],
) as dag:

    ingest_chaos = PythonOperator(
        task_id="ingest_chaos",
        python_callable=_ingest_chaos,
        provide_context=True,
    )

    ingest_chaos
