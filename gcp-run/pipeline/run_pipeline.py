import argparse
import importlib
import logging
import time

from . import config
from .warehouse_client import WarehouseClient
from .db import SCHEMA_MAP, ALL_TABLES

logger = logging.getLogger(__name__)

STEP_MODULES = [
    "01_discover",
    "02_ingest_usage",
    "03_ingest_chaos",
    "04_ingest_leads",
    "05_ingest_metagame",
    "06_ingest_replays",
]


def ensure_all_tables(wh):
    wh.ensure_dataset()
    for table in ALL_TABLES:
        schema = SCHEMA_MAP[table]
        wh.ensure_table(table, schema)


def run(format_filter=None, skip_discover=False):
    wh = WarehouseClient()
    ensure_all_tables(wh)

    logger.info("=" * 55)
    logger.info("  SMOGON BIG DATA ETL PIPELINE (GCP)")
    if format_filter:
        logger.info("  Format filter: %s", format_filter)
    logger.info("  Run ID: %s", config.RUN_ID)
    logger.info("  Bucket: %s", config.BUCKET_NAME)
    logger.info("  BQ Dataset: %s.%s", config.PROJECT_ID, config.BQ_DATASET)
    logger.info("=" * 55)

    for mod_name in STEP_MODULES:
        if skip_discover and mod_name == "01_discover":
            logger.info(">>> SKIP: %s", mod_name)
            continue
        try:
            mod = importlib.import_module(f"pipeline.{mod_name}")
        except Exception as e:
            logger.warning("Could not import %s: %s, skipping", mod_name, e)
            continue
        logger.info(">>> STEP: %s", mod_name)
        start = time.time()
        try:
            mod.run(format_filter=format_filter) if "format_filter" in mod.run.__code__.co_varnames else mod.run()
        except Exception:
            logger.exception("Step %s failed", mod_name)
            raise
        elapsed = time.time() - start
        logger.info("<<< %s completed in %.1fs", mod_name, elapsed)

    logger.info("=" * 55)
    logger.info("  PIPELINE COMPLETE - TABLE COUNTS")
    logger.info("=" * 55)
    for table in ALL_TABLES:
        cnt = wh.count_rows(table)
        logger.info("  %-25s %d", table, cnt)
    logger.info("=" * 55)
    logger.info("  Output also archived in gs://%s/%s/", config.BUCKET_NAME, wh.storage.results_prefix)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smogon Big Data ETL Pipeline (GCP)")
    parser.add_argument("--format", help="Process only this format (e.g., gen9ou)")
    parser.add_argument("--skip-discover", action="store_true", help="Skip discovery step")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    run(format_filter=args.format, skip_discover=args.skip_discover)
