import pytest
import asyncio
import responses
from aioresponses import aioresponses
from pipeline.db import init_db, get_conn
from pipeline import discover, ingest_replays


def setup_sources(patched_db):
    init_db()
    discover.run(months=["2026-04"])


REPLAY_SEARCH_JSON = [
    {"id": "replay1", "rating": 1600, "players": ["alice", "bob"], "uploadtime": 1700000000},
    {"id": "replay2", "rating": 1550, "players": ["charlie", "dave"], "uploadtime": 1700001000},
]

REPLAY_LOG = (
    '|player|p1|alice\n'
    '|player|p2|bob\n'
    '|switch|p1a: Great Tusk, L50\n'
    '|switch|p1a: Gholdengo, L50\n'
    '|switch|p2a: Gholdengo, L50\n'
    '|win|alice\n'
)


@pytest.mark.asyncio
async def test_fetch_replay_list():
    with aioresponses() as mocked:
        mocked.get(
            "https://replay.pokemonshowdown.com/search.json?format=gen9ou&page=1",
            payload=REPLAY_SEARCH_JSON,
        )
        import aiohttp
        async with aiohttp.ClientSession() as session:
            results = await ingest_replays.fetch_replay_list(session, "gen9ou", 1)
        assert len(results) == 2


@responses.activate
def test_run_inserts_replays(patched_db, mock_smogon):
    setup_sources(patched_db)
    with aioresponses() as mocked:
        mocked.get(
            "https://replay.pokemonshowdown.com/search.json?format=gen9ou&page=1",
            payload=REPLAY_SEARCH_JSON,
        )
        mocked.get("https://replay.pokemonshowdown.com/replay1.log", body=REPLAY_LOG)
        mocked.get("https://replay.pokemonshowdown.com/replay2.log", body=REPLAY_LOG)
        ingest_replays.run(format_filter="gen9ou", pages=1)
    with get_conn() as conn:
        replay_count = conn.execute("SELECT COUNT(*) FROM replays").fetchone()[0]
        team_count = conn.execute("SELECT COUNT(*) FROM replay_teams").fetchone()[0]
    assert replay_count == 2
    assert team_count == 6
