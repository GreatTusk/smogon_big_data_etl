import asyncio
import logging
import re
import aiohttp
import argparse
import json
from tqdm import tqdm
from datetime import datetime

from .config import REPLAY_SEARCH_URL, REPLAY_BASE, MAX_CONCURRENT_LOGS, REPLAY_PAGES, MIN_ELO_REPLAY, BATCH_SIZE
from .warehouse_client import WarehouseClient
from .storage_client import StorageClient
from .db import SCHEMA_MAP, TABLE_REPLAYS, TABLE_REPLAY_TEAMS, TABLE_DISCOVERED_SOURCES

logger = logging.getLogger(__name__)


async def fetch_replay_list(session, format_id, page):
    try:
        async with session.get(REPLAY_SEARCH_URL, params={"format": format_id, "page": page}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.debug("Error fetching page %d for %s: %s", page, format_id, e)
        return []


async def fetch_replay_log(session, replay_id, semaphore):
    try:
        async with semaphore:
            async with session.get(f"{REPLAY_BASE}/{replay_id}.log", timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                return await resp.text()
    except Exception:
        return None


async def fetch_and_parse(session, meta, semaphore):
    replay_id = meta.get("id", "")
    if not replay_id:
        return None
    log = await fetch_replay_log(session, replay_id, semaphore)
    if not log:
        return None
    team1, team2 = [], []
    winner = None
    p1_name = p2_name = ""
    for line in log.splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        tag = parts[1]
        if tag == "player" and len(parts) >= 4:
            if parts[2] == "p1":
                p1_name = parts[3]
            elif parts[2] == "p2":
                p2_name = parts[3]
        elif tag == "switch" and len(parts) >= 3:
            sid = parts[2]
            if ": " in sid:
                poke = sid.split(": ", 1)[1].split(",")[0].strip()
                poke = re.sub(r"\s*\(.*?\)$", "", poke).strip()
            else:
                continue
            if not poke:
                continue
            if sid.startswith("p1") and poke not in team1:
                team1.append(poke)
            elif sid.startswith("p2") and poke not in team2:
                team2.append(poke)
        elif tag == "win" and len(parts) >= 3:
            wn = parts[2].strip()
            if wn == p1_name:
                winner = "p1"
            elif wn == p2_name:
                winner = "p2"
    if not team1 and not team2:
        return None
    return meta, team1, team2, winner


async def _run_async(format_id, wh, storage, pages=REPLAY_PAGES):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOGS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_LOGS)
    async with aiohttp.ClientSession(connector=connector) as session:
        all_replays = []
        for page in range(1, pages + 1):
            rl = await fetch_replay_list(session, format_id, page)
            if not rl:
                break
            all_replays.extend(rl)
        if not all_replays:
            logger.info("No replays found for %s", format_id)
            return
        good = [m for m in all_replays if (m.get("rating", 0) or 0) >= MIN_ELO_REPLAY and m.get("id")]
        logger.info("Fetched %d replays for %s, filtered to %d with Elo >= %d",
                    len(all_replays), format_id, len(good), MIN_ELO_REPLAY)
        tasks = [fetch_and_parse(session, meta, semaphore) for meta in good]
        results = await asyncio.gather(*tasks)
        rbatch, tbatch = [], []
        for parsed in results:
            if not parsed:
                continue
            meta, t1, t2, winner = parsed
            rid = meta["id"]
            rating = meta.get("rating", 0) or 0
            players = meta.get("players", ["", ""])
            p1 = players[0] if isinstance(players, list) else ""
            p2 = players[1] if isinstance(players, list) else ""
            ut = meta.get("uploadtime", 0)
            month = datetime.utcfromtimestamp(ut).strftime("%Y-%m") if ut else ""
            rbatch.append({"replay_id": rid, "format_id": format_id, "rating": rating,
                          "player1": p1, "player2": p2, "uploadtime": ut, "month": month})
            for side_name, team in [("p1", t1), ("p2", t2)]:
                won = 1 if winner == side_name else 0
                for poke in team:
                    tbatch.append({"replay_id": rid, "side": side_name, "pokemon": poke, "won": won})
        for i in range(0, len(rbatch), BATCH_SIZE):
            wh.write_rows(TABLE_REPLAYS, SCHEMA_MAP[TABLE_REPLAYS], rbatch[i:i + BATCH_SIZE])
        for i in range(0, len(tbatch), BATCH_SIZE):
            wh.write_rows(TABLE_REPLAY_TEAMS, SCHEMA_MAP[TABLE_REPLAY_TEAMS], tbatch[i:i + BATCH_SIZE])
        logger.info("Ingested %d replays with %d team entries for %s", len(rbatch), len(tbatch), format_id)


def run(format_filter=None, pages=REPLAY_PAGES):
    wh = WarehouseClient()
    storage = StorageClient()
    wh.ensure_table(TABLE_REPLAYS, SCHEMA_MAP[TABLE_REPLAYS])
    wh.ensure_table(TABLE_REPLAY_TEAMS, SCHEMA_MAP[TABLE_REPLAY_TEAMS])

    rows = wh.query(
        f"SELECT DISTINCT format_id FROM `{wh.table_ref(TABLE_DISCOVERED_SOURCES)}` WHERE source_type = 'usage'"
        + (f" AND format_id = @format_filter" if format_filter else "")
    )
    if format_filter:
        rows = [r for r in rows if r["format_id"] == format_filter]

    formats = [r["format_id"] for r in rows]
    for fmt in formats:
        asyncio.run(_run_async(fmt, wh, storage, pages=pages))
    logger.info("Replay ingestion complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", help="Format filter")
    parser.add_argument("--pages", type=int, default=REPLAY_PAGES, help="Number of pages to fetch")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(format_filter=args.format, pages=args.pages)
