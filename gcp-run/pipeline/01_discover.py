import re
import logging
import requests
from tqdm import tqdm

from .config import SMOGON_BASE, GEN9_START, DEFAULT_ELO_TIERS
from .warehouse_client import WarehouseClient
from .db import SCHEMA_MAP, TABLE_MONTHS, TABLE_FORMATS, TABLE_ELO_TIERS, TABLE_DISCOVERED_SOURCES

logger = logging.getLogger(__name__)


def fetch_index_text(url):
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning("Could not fetch %s: %s", url, e)
        return None


def discover_months():
    text = fetch_index_text(SMOGON_BASE)
    if not text:
        return []
    months = []
    for line in text.splitlines():
        m = re.search(r'<a href="(\d{4}-\d{2})/', line)
        if m:
            month = m.group(1)
            if month >= GEN9_START:
                months.append(month)
    return sorted(months)


def discover_sources_for_month(month):
    month_url = f"{SMOGON_BASE}/{month}/"
    text = fetch_index_text(month_url)
    if not text:
        return [], [], [], []
    usage, chaos, leads_, metagame_ = [], [], [], []
    for line in text.splitlines():
        m = re.search(r'<a href="(gen9[^"]+)\.txt(\.gz)?">', line)
        if m:
            filename = m.group(1)
            parts = filename.rsplit("-", 1)
            if len(parts) == 2:
                fmt_base, elo_str = parts
                try:
                    elo = int(elo_str)
                except ValueError:
                    continue
                if elo in DEFAULT_ELO_TIERS:
                    usage.append((month, fmt_base, elo))
        m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.json(\.gz)?">', line)
        if m:
            fmt_base = m.group(1)
            elo = int(m.group(2))
            if elo in DEFAULT_ELO_TIERS:
                chaos.append((month, fmt_base, elo))
    text_lower = text.lower()
    if "chaos/" in text_lower:
        chaos_url = f"{SMOGON_BASE}/{month}/chaos/"
        chaos_text = fetch_index_text(chaos_url)
        if chaos_text:
            for line in chaos_text.splitlines():
                m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.json(\.gz)?">', line)
                if m:
                    fmt_base = m.group(1)
                    elo = int(m.group(2))
                    if elo in DEFAULT_ELO_TIERS:
                        row = (month, fmt_base, elo)
                        if row not in chaos:
                            chaos.append(row)
    if "leads/" in text_lower:
        leads_url = f"{SMOGON_BASE}/{month}/leads/"
        leads_text = fetch_index_text(leads_url)
        if leads_text:
            for line in leads_text.splitlines():
                m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.txt(\.gz)?">', line)
                if m:
                    fmt_base = m.group(1)
                    elo = int(m.group(2))
                    if elo in DEFAULT_ELO_TIERS:
                        leads_.append((month, fmt_base, elo))
    if "metagame/" in text_lower:
        meta_url = f"{SMOGON_BASE}/{month}/metagame/"
        meta_text = fetch_index_text(meta_url)
        if meta_text:
            for line in meta_text.splitlines():
                m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.txt(\.gz)?">', line)
                if m:
                    fmt_base = m.group(1)
                    elo = int(m.group(2))
                    if elo in DEFAULT_ELO_TIERS:
                        metagame_.append((month, fmt_base, elo))
    return usage, chaos, leads_, metagame_


def run(months=None):
    wh = WarehouseClient()
    for table, schema in SCHEMA_MAP.items():
        wh.ensure_table(table, schema)

    if months is None:
        months = discover_months()

    all_months = [{"month": m} for m in months]
    all_elo_tiers = [{"elo_tier": e} for e in DEFAULT_ELO_TIERS]
    all_ds_rows = []
    seen_formats = set()

    for month in tqdm(months, desc="Discovering sources"):
        usage, chaos, leads_, metagame_ = discover_sources_for_month(month)
        for row in usage:
            all_ds_rows.append({"month": row[0], "format_id": row[1], "elo_tier": row[2], "source_type": "usage"})
            seen_formats.add(row[1])
        for row in chaos:
            all_ds_rows.append({"month": row[0], "format_id": row[1], "elo_tier": row[2], "source_type": "chaos"})
            seen_formats.add(row[1])
        for row in leads_:
            all_ds_rows.append({"month": row[0], "format_id": row[1], "elo_tier": row[2], "source_type": "leads"})
            seen_formats.add(row[1])
        for row in metagame_:
            all_ds_rows.append({"month": row[0], "format_id": row[1], "elo_tier": row[2], "source_type": "metagame"})
            seen_formats.add(row[1])

    all_format_rows = [
        {"format_id": fmt, "generation": 9, "tier": fmt.replace("gen9", "")}
        for fmt in sorted(seen_formats)
    ]

    wh.write_rows(TABLE_MONTHS, SCHEMA_MAP[TABLE_MONTHS], all_months)
    wh.write_rows(TABLE_ELO_TIERS, SCHEMA_MAP[TABLE_ELO_TIERS], all_elo_tiers)
    if all_ds_rows:
        wh.write_rows(TABLE_DISCOVERED_SOURCES, SCHEMA_MAP[TABLE_DISCOVERED_SOURCES], all_ds_rows)
    if all_format_rows:
        wh.write_rows(TABLE_FORMATS, SCHEMA_MAP[TABLE_FORMATS], all_format_rows)

    fmt_count = len(seen_formats)
    logger.info("Discovered %d months, %d formats", len(months), fmt_count)
    for m in months:
        logger.info("  %s", m)
    return months


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
