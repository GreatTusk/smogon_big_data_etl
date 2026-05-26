"""
smogon_discover_dag.py — Discover sources DAG
Scrapes Smogon.com/stats to discover all available months, formats, and Elo tiers.
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


def _discover_sources(**context):
    import logging
    from pipeline.db import init_db
    from pipeline import discover
    init_db()
    months = discover.run()
    context["ti"].xcom_push(key="discovered_months", value=months)
    return months


def _summarize_discovery(**context):
    ti = context["ti"]
    months = ti.xcom_pull(task_ids="discover", key="discovered_months")
    if months:
        logging.info("Discovered %d months: %s .. %s", len(months), months[0], months[-1])
    else:
        logging.warning("No new months discovered")


with DAG(
    dag_id="smogon_discover",
    default_args=default_args,
    description="Discover Smogon data sources for available months/formats/tiers",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["smogon", "etl", "discover"],
) as dag:

    discover = PythonOperator(
        task_id="discover",
        python_callable=_discover_sources,
        provide_context=True,
    )

    summarize = PythonOperator(
        task_id="summarize",
        python_callable=_summarize_discovery,
        provide_context=True,
    )

    discover >> summarize
