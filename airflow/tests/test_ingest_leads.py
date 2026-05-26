import pytest
import responses
from pipeline.db import init_db, get_conn
from pipeline import discover, ingest_leads


def setup_sources(patched_db):
    init_db()
    discover.run(months=["2026-04"])


def test_parse_leads_table():
    text = (
        "+ ---- + ------------------- + --------- + --------- +\n"
        "| Rank | Pokemon             | Usage %   | Raw       |\n"
        "+ ---- + ------------------- + --------- + --------- +\n"
        "|    1 | Great Tusk         |   24.50% |     12250 |\n"
        "+ ---- + ------------------- + --------- + --------- +"
    )
    rows = ingest_leads.parse_leads_table(text)
    assert len(rows) == 1
    assert rows[0] == (1, "Great Tusk", 24.50, 12250)


@responses.activate
def test_run_inserts_rows(patched_db, mock_smogon):
    setup_sources(patched_db)
    ingest_leads.run(format_filter="gen9ou")
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE month='2026-04' AND format_id='gen9ou' AND elo_tier=0"
        ).fetchone()[0]
    assert count >= 3
