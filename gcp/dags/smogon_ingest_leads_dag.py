"""
smogon_ingest_leads_dag.py — Leads stats ingestion DAG
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
    WHERE source_type = 'leads'
      AND format_id = '{fmt}'
      AND (month, format_id, elo_tier) NOT IN (
        SELECT DISTINCT month, format_id, elo_tier
        FROM `{config.PROJECT_ID}.{config.STAGING_DATASET}.leads`
      )
    ORDER BY month DESC
    LIMIT 20
    """
    rows = execute_query(sql) or []
    return [dict(r) for r in rows]

def _ingest_leads(**context):
    from pipeline.ingest_leads import run
    sources = _get_pending_sources(**context)
    if not sources:
        print("No pending leads sources to ingest")
        return
    for src in sources:
        run(src["month"], src["format_id"], src["elo_tier"])
    print(f"Ingested {len(sources)} leads sources")

with DAG(
    dag_id="smogon_ingest_leads",
    default_args=default_args,
    description="Ingest Smogon leads stats into BigQuery",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "leads"],
) as dag:

    ingest_leads = PythonOperator(
        task_id="ingest_leads",
        python_callable=_ingest_leads,
        provide_context=True,
    )

    ingest_leads
