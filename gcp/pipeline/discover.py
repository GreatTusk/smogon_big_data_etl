"""
discover.py — Refactored from 01_discover.py
Scrapes Smogon.com/stats to discover available months, formats, and Elo tiers.
Writes results to BigQuery (smogon_raw.discovered_sources + smogon_staging tables).
"""
import re
import logging
import requests
from typing import List, Tuple

from . import config
from .bigquery_client import batch_insert, execute_query, get_existing_keys, table_ref

logger = logging.getLogger(__name__)


def fetch_index_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning("Could not fetch %s: %s", url, e)
        return None


def discover_months() -> List[str]:
    text = fetch_index_text(config.SMOGON_BASE)
    if not text:
        return []
    months = []
    for line in text.splitlines():
        m = re.search(r'<a href="(\d{4}-\d{2})/', line)
        if m:
            month = m.group(1)
            if month >= config.GEN9_START:
                months.append(month)
    return sorted(months)


def discover_sources_for_month(
    month: str,
) -> Tuple[List[Tuple], List[Tuple], List[Tuple], List[Tuple]]:
    month_url = f"{config.SMOGON_BASE}/{month}/"
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
                if elo in config.DEFAULT_ELO_TIERS:
                    usage.append((month, fmt_base, elo))

        m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.json(\.gz)?">', line)
        if m:
            fmt_base = m.group(1)
            elo = int(m.group(2))
            if elo in config.DEFAULT_ELO_TIERS:
                chaos.append((month, fmt_base, elo))

    text_lower = text.lower()
    if "chaos/" in text_lower:
        chaos_text = fetch_index_text(f"{config.SMOGON_BASE}/{month}/chaos/")
        if chaos_text:
            for line in chaos_text.splitlines():
                m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.json(\.gz)?">', line)
                if m:
                    fmt_base = m.group(1)
                    elo = int(m.group(2))
                    if elo in config.DEFAULT_ELO_TIERS:
                        row = (month, fmt_base, elo)
                        if row not in chaos:
                            chaos.append(row)

    if "leads/" in text_lower:
        leads_text = fetch_index_text(f"{config.SMOGON_BASE}/{month}/leads/")
        if leads_text:
            for line in leads_text.splitlines():
                m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.txt(\.gz)?">', line)
                if m:
                    fmt_base = m.group(1)
                    elo = int(m.group(2))
                    if elo in config.DEFAULT_ELO_TIERS:
                        leads_.append((month, fmt_base, elo))

    if "metagame/" in text_lower:
        meta_text = fetch_index_text(f"{config.SMOGON_BASE}/{month}/metagame/")
        if meta_text:
            for line in meta_text.splitlines():
                m = re.search(r'<a href="(gen9[^"]+)-(\d+)\.txt(\.gz)?">', line)
                if m:
                    fmt_base = m.group(1)
                    elo = int(m.group(2))
                    if elo in config.DEFAULT_ELO_TIERS:
                        metagame_.append((month, fmt_base, elo))

    return usage, chaos, leads_, metagame_


def get_discovered_keys() -> set:
    return get_existing_keys(
        config.RAW_DATASET, "discovered_sources",
        ["month", "format_id", "elo_tier", "source_type"],
    )


def run(months: List[str] = None, format_filter: str = None) -> List[str]:
    if months is None:
        months = discover_months()
    discovered_keys = get_discovered_keys()
    made_key = lambda m, f, e, t: f"{m}|{f}|{e}|{t}"

    # Insert months
    batch_insert(config.STAGING_DATASET, "months", ["month"], [(m,) for m in months])

    # Insert elo tiers
    tier_rows = [{"elo_tier": t} for t in config.DEFAULT_ELO_TIERS]
    batch_insert(
        config.STAGING_DATASET, "elo_tiers", ["elo_tier"],
        [(t,) for t in config.DEFAULT_ELO_TIERS],
    )

    all_sources = []
    all_formats = set()

    for month in months:
        logger.info("Discovering sources for %s", month)
        usage, chaos, leads_, metagame_ = discover_sources_for_month(month)

        if format_filter:
            usage = [r for r in usage if r[1] == format_filter]
            chaos = [r for r in chaos if r[1] == format_filter]
            leads_ = [r for r in leads_ if r[1] == format_filter]
            metagame_ = [r for r in metagame_ if r[1] == format_filter]

        for row in usage:
            key = made_key(row[0], row[1], row[2], "usage")
            if key not in discovered_keys:
                all_sources.append({
                    "month": row[0], "format_id": row[1],
                    "elo_tier": row[2], "source_type": "usage",
                })
                all_formats.add(row[1])
                discovered_keys.add(key)

        for row in chaos:
            key = made_key(row[0], row[1], row[2], "chaos")
            if key not in discovered_keys:
                all_sources.append({
                    "month": row[0], "format_id": row[1],
                    "elo_tier": row[2], "source_type": "chaos",
                })
                all_formats.add(row[1])
                discovered_keys.add(key)

        for row in leads_:
            key = made_key(row[0], row[1], row[2], "leads")
            if key not in discovered_keys:
                all_sources.append({
                    "month": row[0], "format_id": row[1],
                    "elo_tier": row[2], "source_type": "leads",
                })
                all_formats.add(row[1])
                discovered_keys.add(key)

        for row in metagame_:
            key = made_key(row[0], row[1], row[2], "metagame")
            if key not in discovered_keys:
                all_sources.append({
                    "month": row[0], "format_id": row[1],
                    "elo_tier": row[2], "source_type": "metagame",
                })
                all_formats.add(row[1])
                discovered_keys.add(key)

    if all_sources:
        batch_insert(
            config.RAW_DATASET, "discovered_sources",
            ["month", "format_id", "elo_tier", "source_type"],
            [(r["month"], r["format_id"], r["elo_tier"], r["source_type"]) for r in all_sources],
        )

    # Insert formats
    existing_fmts = set()
    existing = execute_query(
        f"SELECT format_id FROM `{table_ref(config.STAGING_DATASET, 'formats')}`"
    )
    if existing:
        existing_fmts = {r["format_id"] for r in existing}
    new_fmts = [
        (fmt, 9, fmt.replace("gen9", ""))
        for fmt in sorted(all_formats)
        if fmt not in existing_fmts
    ]
    if new_fmts:
        batch_insert(
            config.STAGING_DATASET, "formats",
            ["format_id", "generation", "tier"],
            new_fmts,
        )

    logger.info("Discovered %d months, %d new sources, %d formats", len(months), len(all_sources), len(new_fmts))
    return months
