import pytest
import responses
from pipeline.db import init_db, get_conn
from pipeline import discover, ingest_chaos


def setup_sources(patched_db):
    init_db()
    discover.run(months=["2026-04"])


def test_parse_spread_key():
    nature, evs = ingest_chaos.parse_spread_key("Adamant:252/252/4/0/0/4")
    assert nature == "Adamant"
    assert evs == [252, 252, 4, 0, 0, 4]


@responses.activate
def test_fetch_chaos_json(patched_db, mock_smogon):
    setup_sources(patched_db)
    data = ingest_chaos.fetch_chaos_json("2026-04", "gen9ou", 0)
    assert data is not None
    assert "data" in data
    assert "Great Tusk" in data["data"]


@responses.activate
def test_run_inserts_tables(patched_db, mock_smogon):
    setup_sources(patched_db)
    ingest_chaos.run(format_filter="gen9ou")
    with get_conn() as conn:
        details = conn.execute("SELECT COUNT(*) FROM pokemon_details WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
        abilities = conn.execute("SELECT COUNT(*) FROM abilities WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
        items = conn.execute("SELECT COUNT(*) FROM items WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
        moves = conn.execute("SELECT COUNT(*) FROM moves WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
        tera = conn.execute("SELECT COUNT(*) FROM tera_types WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
        teammates = conn.execute("SELECT COUNT(*) FROM teammates WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
        checks = conn.execute("SELECT COUNT(*) FROM checks_counters WHERE month='2026-04' AND format_id='gen9ou'").fetchone()[0]
    assert details >= 2, f"Expected >=2 pokemon_details, got {details}"
    assert abilities >= 3
    assert items >= 2
    assert moves >= 2
    assert tera >= 1
    assert teammates >= 1
    assert checks >= 1
