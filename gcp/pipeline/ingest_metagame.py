"""
ingest_metagame.py — Refactored from 05_ingest_metagame.py
"""
import re
import logging
import gzip
import requests

from . import config
from .bigquery_client import batch_insert, execute_dml
from .gcs_utils import upload_string, download_string

logger = logging.getLogger(__name__)


def fetch_metagame_text(month: str, format_id: str, elo_tier: int) -> str:
    cache_name = f"{format_id}-{elo_tier}.txt"
    cached = download_string("metagame", month, cache_name)
    if cached is not None:
        return cached
    for ext in [".txt", ".txt.gz"]:
        url = f"{config.SMOGON_BASE}/{month}/metagame/{format_id}-{elo_tier}{ext}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                raw = resp.content
                text = gzip.decompress(raw).decode("utf-8") if ext == ".txt.gz" else raw.decode("utf-8")
                upload_string(text, "metagame", month, cache_name)
                return text
        except requests.RequestException:
            continue
    return None


def parse_metagame_text(text: str):
    if not text:
        return []
    results = []
    for line in text.splitlines():
        m = re.match(r"(\w[\w\s-]*?)\.{3,}\s*([\d.]+)%", line)
        if m:
            results.append((m.group(1).strip(), float(m.group(2))))
    return results


def run(month: str, format_id: str, elo_tier: int):
    text = fetch_metagame_text(month, format_id, elo_tier)
    if not text:
        logger.warning("No metagame data for %s %s-%d", month, format_id, elo_tier)
        return
    rows = parse_metagame_text(text)
    if not rows:
        return

    cols = ["month", "format_id", "elo_tier", "playstyle", "usage_pct"]
    vals = [(month, format_id, elo_tier, playstyle, pct) for playstyle, pct in rows]
    batch_insert(config.STAGING_DATASET, "metagame", cols, vals)

    merge_sql = f"""
    MERGE `{config.PROJECT_ID}.{config.DW_DATASET}.fact_metagame` T
    USING (
      SELECT * FROM `{config.PROJECT_ID}.{config.STAGING_DATASET}.metagame`
      WHERE month = '{month}' AND format_id = '{format_id}' AND elo_tier = {elo_tier}
    ) S
    ON T.month = S.month AND T.format_id = S.format_id
       AND T.elo_tier = S.elo_tier AND T.playstyle = S.playstyle
    WHEN MATCHED THEN
      UPDATE SET usage_pct = S.usage_pct
    WHEN NOT MATCHED THEN
      INSERT ROW
    """
    execute_dml(merge_sql)

    logger.info("Ingested %d metagame rows for %s %s Elo %d", len(rows), format_id, month, elo_tier)
