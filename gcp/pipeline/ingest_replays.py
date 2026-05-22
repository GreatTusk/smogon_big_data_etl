"""
ingest_replays.py — Refactored from 06_ingest_replays.py
Fetches replay data from Pokemon Showdown API and loads into BigQuery.
"""
import asyncio
import logging
import re
import aiohttp
from datetime import datetime

from . import config
from .bigquery_client import batch_insert, execute_dml
from .gcs_utils import upload_string

logger = logging.getLogger(__name__)


async def fetch_replay_list(session, format_id: str, page: int):
    try:
        async with session.get(
            config.REPLAY_SEARCH_URL,
            params={"format": format_id, "page": page},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.debug("Error fetching page %d for %s: %s", page, format_id, e)
        return []


async def fetch_replay_log(session, replay_id: str, semaphore):
    try:
        async with semaphore:
            async with session.get(
                f"{config.REPLAY_BASE}/{replay_id}.log",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
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


async def _run_async(format_id: str, pages: int = None):
    pages = pages or config.REPLAY_PAGES
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_LOGS)
    connector = aiohttp.TCPConnector(limit=config.MAX_CONCURRENT_LOGS)
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

        good = [
            m for m in all_replays
            if (m.get("rating", 0) or 0) >= config.MIN_ELO_REPLAY and m.get("id")
        ]
        logger.info(
            "Fetched %d replays for %s, filtered to %d with Elo >= %d",
            len(all_replays), format_id, len(good), config.MIN_ELO_REPLAY,
        )

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
            rbatch.append((rid, format_id, rating, p1, p2, ut, month))
            for side_name, team in [("p1", t1), ("p2", t2)]:
                won = 1 if winner == side_name else 0
                for poke in team:
                    tbatch.append((rid, side_name, poke, won))

        if rbatch:
            r_cols = ["replay_id", "format_id", "rating", "player1", "player2", "uploadtime", "month"]
            batch_insert(config.STAGING_DATASET, "replays", r_cols, rbatch)

            # Store raw log metadata
            for r in rbatch:
                gcs_path = upload_string(
                    str(r),
                    "replays",
                    r[6] or "unknown",
                    f"{r[0]}.meta.json",
                )

            # MERGE into dw
            merge_sql = f"""
            MERGE `{config.PROJECT_ID}.{config.DW_DATASET}.fact_replays` T
            USING (
              SELECT * FROM `{config.PROJECT_ID}.{config.STAGING_DATASET}.replays`
              WHERE format_id = '{format_id}'
            ) S
            ON T.replay_id = S.replay_id
            WHEN NOT MATCHED THEN
              INSERT ROW
            """
            execute_dml(merge_sql)

        if tbatch:
            t_cols = ["replay_id", "side", "pokemon", "won"]
            batch_insert(config.STAGING_DATASET, "replay_teams", t_cols, tbatch)

            merge_sql = f"""
            MERGE `{config.PROJECT_ID}.{config.DW_DATASET}.fact_replay_teams` T
            USING (
              SELECT * FROM `{config.PROJECT_ID}.{config.STAGING_DATASET}.replay_teams`
              WHERE replay_id IN (SELECT replay_id FROM `{config.PROJECT_ID}.{config.STAGING_DATASET}.replays`
                                   WHERE format_id = '{format_id}')
            ) S
            ON T.replay_id = S.replay_id AND T.side = S.side AND T.pokemon = S.pokemon
            WHEN NOT MATCHED THEN
              INSERT ROW
            """
            execute_dml(merge_sql)

        logger.info("Ingested %d replays with %d team entries for %s", len(rbatch), len(tbatch), format_id)


def run(format_id: str, pages: int = None):
    asyncio.run(_run_async(format_id, pages=pages))
