"""
smogon_ingest_metagame_dag.py — Metagame stats ingestion DAG
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

def _get_pending_sources():
    from pipeline.bigquery_client import execute_query
    sql = """
    SELECT month, format_id, elo_tier
    FROM `smogon_raw.discovered_sources`
    WHERE source_type = 'metagame'
      AND (month, format_id, elo_tier) NOT IN (
        SELECT DISTINCT month, format_id, elo_tier
        FROM `smogon_staging.metagame`
      )
    ORDER BY month DESC
    LIMIT 20
    """
    rows = execute_query(sql) or []
    return [dict(r) for r in rows]

def _ingest_metagame(**context):
    from pipeline.ingest_metagame import run
    sources = _get_pending_sources()
    if not sources:
        print("No pending metagame sources to ingest")
        return
    for src in sources:
        run(src["month"], src["format_id"], src["elo_tier"])
    print(f"Ingested {len(sources)} metagame sources")

with DAG(
    dag_id="smogon_ingest_metagame",
    default_args=default_args,
    description="Ingest Smogon metagame stats into BigQuery",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "ingest", "metagame"],
) as dag:

    ingest_metagame = PythonOperator(
        task_id="ingest_metagame",
        python_callable=_ingest_metagame,
        provide_context=True,
    )

    ingest_metagame
