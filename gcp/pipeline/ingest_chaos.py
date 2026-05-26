"""
ingest_chaos.py — Refactored from 03_ingest_chaos.py
Downloads chaos JSON, caches to GCS, parses all sub-sections into BigQuery.
"""
import re
import logging
import json
import gzip
import requests

from . import config
from .bigquery_client import batch_insert, get_existing_keys, execute_dml, table_ref
from .gcs_utils import upload_json, download_json

logger = logging.getLogger(__name__)


def fetch_chaos_json(month: str, format_id: str, elo_tier: int) -> dict:
    cache_name = f"{format_id}-{elo_tier}.json"
    cached = download_json("chaos", month, cache_name)
    if cached is not None:
        return cached

    for url_ext in [".json", ".json.gz"]:
        url = f"{config.SMOGON_BASE}/{month}/chaos/{format_id}-{elo_tier}{url_ext}"
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code == 200:
                raw = resp.content
                data = json.loads(gzip.decompress(raw) if url_ext == ".json.gz" else raw)
                upload_json(data, "chaos", month, cache_name)
                return data
        except requests.RequestException:
            continue
    return None


def parse_spread_key(key: str):
    m = re.match(r"(\w+):([\d/]+)", key.strip())
    if not m:
        return None, (0, 0, 0, 0, 0, 0)
    nature = m.group(1)
    evs = [int(x) if x.strip() else 0 for x in m.group(2).split("/")]
    evs = (evs + [0] * 6)[:6]
    return nature, evs


def run(month: str, format_id: str, elo_tier: int):
    data = fetch_chaos_json(month, format_id, elo_tier)
    if not data:
        logger.warning("No chaos data for %s %s-%d", month, format_id, elo_tier)
        return

    # Store raw payload
    raw_rows = [{
        "month": month,
        "format_id": format_id,
        "elo_tier": elo_tier,
        "raw_payload": json.dumps(data)[:100000],
        "source_url": f"{config.SMOGON_BASE}/{month}/chaos/{format_id}-{elo_tier}.json",
    }]
    batch_insert(config.RAW_DATASET, "chaos_json", ["month", "format_id", "elo_tier", "raw_payload", "source_url"],
                 [(r["month"], r["format_id"], r["elo_tier"], r["raw_payload"], r["source_url"]) for r in raw_rows])

    pokemon_data = data.get("data", {})
    if not pokemon_data:
        return

    batch_details = []
    batch_abilities = []
    batch_items = []
    batch_moves = []
    batch_spreads = []
    batch_tera = []
    batch_teammates = []
    batch_checks = []

    for poke_name, info in pokemon_data.items():
        if not isinstance(info, dict):
            continue
        raw_count = info.get("Raw count")
        vc_arr = info.get("Viability Ceiling")
        viability = vc_arr[1] if isinstance(vc_arr, list) and len(vc_arr) >= 2 else None
        if isinstance(raw_count, str):
            try:
                raw_count = int(raw_count.replace(",", ""))
            except (ValueError, AttributeError):
                raw_count = None
        batch_details.append((month, format_id, elo_tier, poke_name, raw_count, None, viability))

        for section in ("Abilities", "Items", "Moves", "Tera Types", "Teammates", "Spreads", "Checks and Counters"):
            data_section = info.get(section)
            if not isinstance(data_section, dict):
                continue
            for key, val in data_section.items():
                if section == "Checks and Counters":
                    if isinstance(val, dict):
                        batch_checks.append((
                            month, format_id, elo_tier, poke_name, key,
                            float(val.get("n", 0)), float(val.get("p", 0)), float(val.get("d", 0))
                        ))
                    elif isinstance(val, (int, float)):
                        batch_checks.append((month, format_id, elo_tier, poke_name, key, float(val), None, None))
                    continue
                if not isinstance(val, (int, float)):
                    continue
                score = float(val)
                if section == "Abilities":
                    batch_abilities.append((month, format_id, elo_tier, poke_name, key, score))
                elif section == "Items":
                    batch_items.append((month, format_id, elo_tier, poke_name, key, score))
                elif section == "Moves":
                    batch_moves.append((month, format_id, elo_tier, poke_name, key, score))
                elif section == "Tera Types":
                    batch_tera.append((month, format_id, elo_tier, poke_name, key, score))
                elif section == "Spreads":
                    nature, evs = parse_spread_key(key)
                    batch_spreads.append((month, format_id, elo_tier, poke_name, nature, *evs, key, score))
                elif section == "Teammates":
                    p1, p2 = sorted([poke_name, key])
                    batch_teammates.append((month, format_id, elo_tier, p1, p2, score))

    inserts = [
        ("pokemon_details", ["month", "format_id", "elo_tier", "pokemon", "raw_count", "avg_weight", "viability_ceiling"], batch_details),
        ("abilities", ["month", "format_id", "elo_tier", "pokemon", "ability", "usage_pct"], batch_abilities),
        ("items", ["month", "format_id", "elo_tier", "pokemon", "item", "usage_pct"], batch_items),
        ("moves", ["month", "format_id", "elo_tier", "pokemon", "move", "usage_pct"], batch_moves),
        ("spreads", ["month", "format_id", "elo_tier", "pokemon", "nature", "hp", "atk", "def", "spa", "spd", "spe", "spread_str", "usage_pct"], batch_spreads),
        ("tera_types", ["month", "format_id", "elo_tier", "pokemon", "tera_type", "usage_pct"], batch_tera),
        ("teammates", ["month", "format_id", "elo_tier", "pokemon1", "pokemon2", "usage_pct"], batch_teammates),
        ("checks_counters", ["month", "format_id", "elo_tier", "pokemon", "counter_pokemon", "score", "ko_pct", "switch_pct"], batch_checks),
    ]

    for dw_table, cols, batch in inserts:
        if not batch:
            continue
        # Insert into staging
        batch_insert(config.STAGING_DATASET, dw_table, cols, batch)
        # MERGE into dw layer
        col_names = ", ".join(cols)

        dw_key = ["month", "format_id", "elo_tier"]
        if dw_table == "teammates":
            dw_key.extend(["pokemon1", "pokemon2"])
        elif dw_table == "checks_counters":
            dw_key.extend(["pokemon", "counter_pokemon"])
        elif dw_table == "spreads":
            dw_key.extend(["pokemon", "spread_str"])
        elif dw_table == "pokemon_details":
            dw_key.append("pokemon")
        else:
            dw_key.append("pokemon")
            singular = {
                "abilities": "ability",
                "items": "item",
                "moves": "move",
                "tera_types": "tera_type",
            }
            dw_key.append(singular.get(dw_table, dw_table[:-1]))

        on_clause = " AND ".join(f"T.{k} = S.{k}" for k in dw_key)
        update_cols = [c for c in cols if c not in dw_key]
        set_clause = ", ".join(f"{c} = S.{c}" for c in update_cols) if update_cols else ""

        merge_sql = f"""
        MERGE `{table_ref(config.DW_DATASET, f'fact_{dw_table}')}` T
        USING (
          SELECT {col_names}
          FROM `{table_ref(config.STAGING_DATASET, dw_table)}`
          {src_filter}
        ) S
        ON {on_clause}
        WHEN MATCHED THEN
          UPDATE SET {set_clause}
        WHEN NOT MATCHED THEN
          INSERT ROW
        """
        try:
            execute_dml(merge_sql)
        except Exception as e:
            logger.warning("MERGE failed for fact_%s: %s", dw_table, e)

    logger.info(
        "Ingested chaos data for %s %s Elo %d: %d pokemon, %d abilities, %d items, %d moves, %d spreads, %d tera, %d teammates, %d checks",
        format_id, month, elo_tier,
        len(batch_details), len(batch_abilities), len(batch_items),
        len(batch_moves), len(batch_spreads), len(batch_tera),
        len(batch_teammates), len(batch_checks),
    )
