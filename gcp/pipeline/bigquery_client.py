import logging
import json
from typing import List, Tuple, Optional, Any
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from . import config

logger = logging.getLogger(__name__)

_client = None


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        project = config.PROJECT_ID or None
        _client = bigquery.Client(project=project)
    return _client


def table_ref(dataset: str, table_name: str) -> str:
    if config.PROJECT_ID:
        return f"{config.PROJECT_ID}.{dataset}.{table_name}"
    return f"{dataset}.{table_name}"


def table_exists(dataset: str, table_name: str) -> bool:
    client = get_client()
    try:
        client.get_table(table_ref(dataset, table_name))
        return True
    except NotFound:
        return False


def insert_rows(
    dataset: str,
    table_name: str,
    rows: List[dict],
    batch_size: int = None,
) -> int:
    if not rows:
        return 0
    client = get_client()
    table_ref_full = table_ref(dataset, table_name)
    batch_size = batch_size or config.BATCH_SIZE
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            logger.error("BigQuery insert errors for %s: %s", table_ref_full, errors[:3])
            raise RuntimeError(f"BigQuery insert failed: {errors}")
        total += len(batch)
    logger.debug("Inserted %d rows into %s", total, table_ref)
    return total


def execute_query(sql: str) -> Optional[list]:
    client = get_client()
    job = client.query(sql)
    result = job.result()
    if result.total_rows:
        return [dict(row) for row in result]
    return None


def execute_dml(sql: str) -> int:
    client = get_client()
    job = client.query(sql)
    return job.result().total_rows


def merge_from_staging(
    target_table: str,
    source_sql: str,
    join_keys: List[str],
    source_dataset: str = config.STAGING_DATASET,
    target_dataset: str = config.DW_DATASET,
):
    key_conditions = " AND ".join(
        f"T.{k} = S.{k}" for k in join_keys
    )
    full_target = table_ref(target_dataset, target_table)
    merge_sql = f"""
    MERGE `{full_target}` T
    USING ({source_sql}) S
    ON {key_conditions}
    WHEN NOT MATCHED THEN
      INSERT ROW
    """
    return execute_dml(merge_sql)


def get_existing_keys(
    dataset: str,
    table_name: str,
    key_columns: List[str],
) -> set:
    cols = ", ".join(key_columns)
    key_expr = ", ".join(f"CAST({c} AS STRING)" for c in key_columns)
    sql = f"SELECT DISTINCT CONCAT({key_expr}) AS _key FROM `{table_ref(dataset, table_name)}`"
    rows = execute_query(sql)
    if not rows:
        return set()
    return {r["_key"] for r in rows}


def batch_insert(
    dataset: str,
    table_name: str,
    columns: List[str],
    values: List[tuple],
    batch_size: int = None,
) -> int:
    if not values:
        return 0
    rows = [dict(zip(columns, row)) for row in values]
    return insert_rows(dataset, table_name, rows, batch_size)
