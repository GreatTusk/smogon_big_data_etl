import pytest
import responses
from pipeline.db import init_db, get_conn
from pipeline import discover, ingest_metagame


def setup_sources(patched_db):
    init_db()
    discover.run(months=["2026-04"])


@responses.activate
def test_parse_metagame_text(mock_smogon):
    text = "Offense......38.76%\nBalance......35.02%\nStall......9.55%"
    rows = ingest_metagame.parse_metagame_text(text)
    assert len(rows) == 3
    assert rows[0] == ("Offense", 38.76)
    assert rows[2] == ("Stall", 9.55)


@responses.activate
def test_run_inserts_rows(patched_db, mock_smogon):
    setup_sources(patched_db)
    ingest_metagame.run(format_filter="gen9ou")
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM metagame WHERE month='2026-04' AND format_id='gen9ou' AND elo_tier=0"
        ).fetchone()[0]
    assert count == 4
