"""
smogon_discover_dag.py — Discover sources DAG
Scrapes Smogon.com/stats index to find available months, formats, and Elo tiers.
Defaults to gen9ou when no format is specified.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

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

def _discover_sources(**context):
    from pipeline.discover import run
    fmt = _get_format(**context)
    print(f"Discovering sources for format: {fmt}")
    months = run(format_filter=fmt)
    context["ti"].xcom_push(key="discovered_months", value=months)
    return months

def _summarize_discovery(**context):
    ti = context["ti"]
    months = ti.xcom_pull(task_ids="discover", key="discovered_months")
    if months:
        print(f"Discovered {len(months)} months: {months[0]} .. {months[-1]}")
    else:
        print("No new months discovered")

with DAG(
    dag_id="smogon_discover",
    default_args=default_args,
    description="Discover Smogon data sources for available months/formats/tiers",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
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
