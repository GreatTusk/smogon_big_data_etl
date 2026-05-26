"""
ingest_usage.py — Refactored from 02_ingest_usage.py
Downloads usage .txt files, caches to GCS, parses and loads into BigQuery.
"""
import re
import logging
import gzip
import requests

from . import config
from .bigquery_client import batch_insert, get_existing_keys
from .gcs_utils import upload_string, download_string, blob_exists

logger = logging.getLogger(__name__)


def fetch_usage_text(month: str, format_id: str, elo_tier: int) -> str:
    cache_name = f"{format_id}-{elo_tier}.txt"
    cached = download_string("usage", month, cache_name)
    if cached is not None:
        return cached

    for ext in [".txt", ".txt.gz"]:
        url = f"{config.SMOGON_BASE}/{month}/{format_id}-{elo_tier}{ext}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                raw = resp.content
                if ext == ".txt.gz":
                    text = gzip.decompress(raw).decode("utf-8")
                else:
                    text = raw.decode("utf-8")
                upload_string(text, "usage", month, cache_name, compress=(ext == ".txt.gz"))
                return text
        except requests.RequestException:
            continue
    return None


def parse_usage_table(text: str):
    if not text:
        return [], None
    lines = text.splitlines()
    total_battles = None
    header_seen = False
    data_lines = []
    for line in lines:
        tm = re.search(r"Total battles:\s*(\d+)", line)
        if tm:
            total_battles = int(tm.group(1))
        if "| Rank | Pokemon" in line:
            header_seen = True
            continue
        if header_seen:
            if re.match(r"^\+\s*---", line):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                try:
                    rank = int(parts[1])
                except ValueError:
                    continue
                pokemon = parts[2]
                try:
                    usage_pct = float(parts[3].rstrip("%"))
                except ValueError:
                    usage_pct = 0.0
                try:
                    raw_count = int(parts[4].replace(",", ""))
                except ValueError:
                    raw_count = 0
                try:
                    raw_pct = float(parts[5].rstrip("%"))
                except ValueError:
                    raw_pct = 0.0
                try:
                    real_count = int(parts[6].replace(",", ""))
                except ValueError:
                    real_count = 0
                try:
                    real_pct = float(parts[7].rstrip("%"))
                except ValueError:
                    real_pct = 0.0
                data_lines.append((rank, pokemon, usage_pct, raw_count, raw_pct, real_count, real_pct))
    return data_lines, total_battles


def run(month: str, format_id: str, elo_tier: int):
    text = fetch_usage_text(month, format_id, elo_tier)
    if not text:
        logger.warning("No usage data for %s %s-%d", month, format_id, elo_tier)
        return

    data_lines, total_battles = parse_usage_table(text)
    if not data_lines:
        return

    # Insert raw payload
    raw_rows = [{"month": month, "format_id": format_id, "elo_tier": elo_tier,
                  "raw_payload": raw_payload,
                  "source_url": f"{config.SMOGON_BASE}/{month}/{format_id}-{elo_tier}.txt"}]
    from .bigquery_client import insert_rows
    from .bigquery_client import table_ref
    insert_rows(config.RAW_DATASET, "usage_stats", raw_rows)

    # Update month total battles
    if total_battles:
        execute_dml(
            f"UPDATE `{table_ref(config.STAGING_DATASET, 'months')}` "
            f"SET total_battles = {total_battles} WHERE month = '{month}'"
        )

    # Insert into staging
    cols = ["month", "format_id", "elo_tier", "pokemon", "rank",
            "usage_pct", "raw_count", "raw_pct", "real_count", "real_pct"]
    vals = [
        (month, format_id, elo_tier, p, r, up, rc, rp, rec, rep)
        for r, p, up, rc, rp, rec, rep in data_lines
    ]
    batch_insert(config.STAGING_DATASET, "usage_stats", cols, vals)

    # Upsert into dimensional layer via MERGE
    merge_sql = f"""
    MERGE `{table_ref(config.DW_DATASET, 'fact_usage')}` T
    USING (
      SELECT month, format_id, elo_tier, pokemon, rank, usage_pct, raw_count, raw_pct, real_count, real_pct FROM (
        SELECT month, format_id, elo_tier, pokemon, rank, usage_pct, raw_count, raw_pct, real_count, real_pct,
               ROW_NUMBER() OVER (PARTITION BY month, format_id, elo_tier, pokemon ORDER BY rank) AS rn
        FROM `{table_ref(config.STAGING_DATASET, 'usage_stats')}`
        WHERE month = '{month}' AND format_id = '{format_id}' AND elo_tier = {elo_tier}
      ) WHERE rn = 1
    ) S
    ON T.month = S.month AND T.format_id = S.format_id
       AND T.elo_tier = S.elo_tier AND T.pokemon = S.pokemon
    WHEN MATCHED THEN
      UPDATE SET rank = S.rank, usage_pct = S.usage_pct, raw_count = S.raw_count,
                 raw_pct = S.raw_pct, real_count = S.real_count, real_pct = S.real_pct
    WHEN NOT MATCHED THEN
      INSERT ROW
    """
    execute_dml(merge_sql)

    logger.info("Ingested %d usage rows for %s %s Elo %d", len(data_lines), format_id, month, elo_tier)
