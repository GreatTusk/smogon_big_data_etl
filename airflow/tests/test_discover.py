import pytest
import responses
from pipeline.db import init_db
from pipeline import discover


@responses.activate
def test_discover_months(mock_smogon):
    init_db()
    months = discover.discover_months()
    assert len(months) >= 5
    assert "2026-04" in months
    assert all(m.startswith("20") for m in months)


@responses.activate
def test_discover_sources_for_month(mock_smogon):
    init_db()
    usage, chaos, leads_, metagame_ = discover.discover_sources_for_month("2026-04")
    assert len(usage) >= 4
    assert ("2026-04", "gen9ou", 0) in usage
    assert ("2026-04", "gen9ou", 1500) in usage
    assert ("2026-04", "gen9ou", 1695) in usage
    assert len(chaos) >= 2
    assert len(leads_) >= 1
    assert len(metagame_) >= 1


@responses.activate
def test_run_stores_results(patched_db):
    result = discover.run(months=["2026-04"])
    assert "2026-04" in result
    import sqlite3
    conn = sqlite3.connect(patched_db)
    months = conn.execute("SELECT month FROM months").fetchall()
    conn.close()
    assert ("2026-04",) in months
