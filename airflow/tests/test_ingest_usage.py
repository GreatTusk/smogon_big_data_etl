import pytest
import responses
from pipeline.db import init_db, get_conn
from pipeline import discover, ingest_usage
from conftest import make_usage_txt


def setup_sources(patched_db):
    init_db()
    discover.run(months=["2026-04"])


@responses.activate
def test_parse_usage_table(patched_db, mock_smogon):
    setup_sources(patched_db)
    text = make_usage_txt()
    data_lines, total = ingest_usage.parse_usage_table(text)
    assert len(data_lines) >= 1
    assert total == 50000
    rank, poke, usage_pct, raw_count, raw_pct, real_count, real_pct = data_lines[0]
    assert rank == 1
    assert poke == "Great Tusk"
    assert usage_pct == pytest.approx(18.52)


@responses.activate
def test_fetch_usage_text_caches(patched_db, mock_smogon, tmp_path):
    setup_sources(patched_db)
    text = ingest_usage.fetch_usage_text("2026-04", "gen9ou", 0)
    assert text is not None
    assert "Great Tusk" in text


@responses.activate
def test_run_inserts_rows(patched_db, mock_smogon):
    setup_sources(patched_db)
    ingest_usage.run(format_filter="gen9ou")
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM usage_stats WHERE month='2026-04' AND format_id='gen9ou' AND elo_tier=0"
        ).fetchone()[0]
    assert count >= 3


@responses.activate
def test_run_is_idempotent(patched_db, mock_smogon):
    setup_sources(patched_db)
    ingest_usage.run(format_filter="gen9ou")
    ingest_usage.run(format_filter="gen9ou")
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM usage_stats WHERE month='2026-04' AND format_id='gen9ou' AND elo_tier=0"
        ).fetchone()[0]
    assert count >= 3
