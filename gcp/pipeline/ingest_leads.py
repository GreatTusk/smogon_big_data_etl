"""
ingest_leads.py — Refactored from 04_ingest_leads.py
"""
import re
import logging
import gzip
import requests

from . import config
from .bigquery_client import batch_insert, execute_dml
from .gcs_utils import upload_string, download_string

logger = logging.getLogger(__name__)


def fetch_leads_text(month: str, format_id: str, elo_tier: int) -> str:
    cache_name = f"{format_id}-{elo_tier}.txt"
    cached = download_string("leads", month, cache_name)
    if cached is not None:
        return cached
    for ext in [".txt", ".txt.gz"]:
        url = f"{config.SMOGON_BASE}/{month}/leads/{format_id}-{elo_tier}{ext}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                raw = resp.content
                text = gzip.decompress(raw).decode("utf-8") if ext == ".txt.gz" else raw.decode("utf-8")
                upload_string(text, "leads", month, cache_name)
                return text
        except requests.RequestException:
            continue
    return None


def parse_leads_table(text: str):
    if not text:
        return []
    header_seen = False
    results = []
    for line in text.splitlines():
        if "| Rank | Pokemon" in line:
            header_seen = True
            continue
        if header_seen:
            if re.match(r"^\+\s*---", line):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                try:
                    rank = int(parts[1])
                except ValueError:
                    continue
                try:
                    usage_pct = float(parts[3].rstrip("%"))
                except ValueError:
                    usage_pct = 0.0
                try:
                    raw_count = int(parts[4].replace(",", ""))
                except ValueError:
                    raw_count = 0
                results.append((rank, parts[2], usage_pct, raw_count))
    return results


def run(month: str, format_id: str, elo_tier: int):
    text = fetch_leads_text(month, format_id, elo_tier)
    if not text:
        logger.warning("No leads data for %s %s-%d", month, format_id, elo_tier)
        return
    rows = parse_leads_table(text)
    if not rows:
        return

    cols = ["month", "format_id", "elo_tier", "pokemon", "rank", "usage_pct", "raw_count"]
    vals = [(month, format_id, elo_tier, p, r, u, rc) for r, p, u, rc in rows]
    batch_insert(config.STAGING_DATASET, "leads", cols, vals)

    merge_sql = f"""
    MERGE `{config.PROJECT_ID}.{config.DW_DATASET}.fact_leads` T
    USING (
      SELECT * FROM `{config.PROJECT_ID}.{config.STAGING_DATASET}.leads`
      WHERE month = '{month}' AND format_id = '{format_id}' AND elo_tier = {elo_tier}
    ) S
    ON T.month = S.month AND T.format_id = S.format_id
       AND T.elo_tier = S.elo_tier AND T.pokemon = S.pokemon
    WHEN MATCHED THEN
      UPDATE SET rank = S.rank, usage_pct = S.usage_pct, raw_count = S.raw_count
    WHEN NOT MATCHED THEN
      INSERT ROW
    """
    execute_dml(merge_sql)

    logger.info("Ingested %d leads rows for %s %s Elo %d", len(rows), format_id, month, elo_tier)
