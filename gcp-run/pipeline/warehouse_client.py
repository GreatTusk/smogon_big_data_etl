import json
import logging
import tempfile
import time
from pathlib import Path

from google.cloud import bigquery

from .config import PROJECT_ID, BQ_DATASET, REGION, BUCKET_NAME, RUN_ID
from .storage_client import StorageClient

logger = logging.getLogger(__name__)


class WarehouseClient:
    def __init__(self, project_id=None, dataset=None, region=None, bucket_name=None, run_id=None):
        self.client = bigquery.Client(project=project_id or PROJECT_ID)
        self.project = self.client.project
        self.dataset = dataset or BQ_DATASET
        self.region = region or REGION
        self.bucket_name = bucket_name or BUCKET_NAME
        self.run_id = run_id or RUN_ID
        self.storage = StorageClient(bucket_name=self.bucket_name, run_id=self.run_id)

    @property
    def dataset_ref(self):
        return f"{self.project}.{self.dataset}"

    def table_ref(self, table_name):
        return f"{self.dataset_ref}.{table_name}"

    def ensure_dataset(self):
        dataset = bigquery.Dataset(self.dataset_ref)
        dataset.location = self.region
        self.client.create_dataset(dataset, exists_ok=True)
        logger.info("Ensured dataset %s in %s", self.dataset_ref, self.region)

    def ensure_table(self, table_name, schema, write_disposition=bigquery.WriteDisposition.WRITE_EMPTY):
        table_ref = self.table_ref(table_name)
        table = bigquery.Table(table_ref, schema=schema)
        table = self.client.create_table(table, exists_ok=True)
        logger.info("Ensured table %s", table_ref)
        return table

    def query(self, sql):
        job = self.client.query(sql)
        return [dict(row) for row in job.result()]

    def query_set(self, sql, num_columns=None):
        job = self.client.query(sql)
        rows = list(job.result())
        if not rows:
            return set()
        if num_columns == 1 or len(rows[0]) == 1:
            return {row[0] for row in rows}
        return {tuple(row.values()) for row in rows}

    def count_rows(self, table_name):
        job = self.client.query(f"SELECT COUNT(*) as cnt FROM `{self.table_ref(table_name)}`")
        rows = list(job.result())
        return rows[0]["cnt"] if rows else 0

    def truncate(self, table_name):
        self.client.query(f"TRUNCATE TABLE `{self.table_ref(table_name)}`").result()
        logger.info("Truncated table %s", self.table_ref(table_name))

    def write_rows(self, table_name, schema, rows, write_disposition=bigquery.WriteDisposition.WRITE_APPEND):
        if not rows:
            return
        table_ref = self.table_ref(table_name)
        table = bigquery.Table(table_ref, schema=schema)
        self.client.create_table(table, exists_ok=True)
        rows_as_dicts = []
        for row in rows:
            if isinstance(row, dict):
                rows_as_dicts.append(row)
            elif isinstance(row, (list, tuple)):
                keys = [field.name for field in schema]
                rows_as_dicts.append(dict(zip(keys, row)))
            else:
                rows_as_dicts.append(row)

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, dir="/tmp")
        try:
            for r in rows_as_dicts:
                tmp.write(json.dumps(r, default=str) + "\n")
            tmp.flush()
            tmp.close()

            blob_name = f"{self.storage.staged_prefix}/{table_name}/{self.run_id}_{int(time.time())}_{hash(str(rows_as_dicts[:1]))}.jsonl"
            uri = self.storage.upload_file(tmp.name, blob_name)

            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema=schema,
                write_disposition=write_disposition,
            )
            load_job = self.client.load_table_from_uri(uri, table_ref, job_config=job_config)
            load_job.result()
            logger.debug("Loaded %d rows to %s", len(rows_as_dicts), table_ref)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def delete_existing_for_source(self, table_name, month, format_id, elo_tier):
        sql = (
            f"DELETE FROM `{self.table_ref(table_name)}` "
            f"WHERE month = @month AND format_id = @format_id AND elo_tier = @elo_tier"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("month", "STRING", month),
                bigquery.ScalarQueryParameter("format_id", "STRING", format_id),
                bigquery.ScalarQueryParameter("elo_tier", "INT64", elo_tier),
            ]
        )
        self.client.query(sql, job_config=job_config).result()

    def table_exists(self, table_name):
        try:
            self.client.get_table(self.table_ref(table_name))
            return True
        except Exception:
            return False
