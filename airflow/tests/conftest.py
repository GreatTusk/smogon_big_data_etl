import os
import sys
import sqlite3
import pytest
import responses

AIRFLOW_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, AIRFLOW_ROOT)
os.environ["AIRFLOW_HOME"] = "/tmp/airflow_test"
os.environ["PYTHONPATH"] = AIRFLOW_ROOT


@pytest.fixture
def fresh_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS formats (
            format_id TEXT PRIMARY KEY,
            generation INTEGER DEFAULT 9,
            tier TEXT,
            name TEXT
        );
        CREATE TABLE IF NOT EXISTS months (
            month TEXT PRIMARY KEY,
            total_battles INTEGER
        );
        CREATE TABLE IF NOT EXISTS elo_tiers (
            elo_tier INTEGER PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS discovered_sources (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'usage',
            PRIMARY KEY (month, format_id, elo_tier, source_type)
        );
        CREATE TABLE IF NOT EXISTS usage_stats (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            rank INTEGER,
            usage_pct REAL,
            raw_count INTEGER,
            raw_pct REAL,
            real_count INTEGER,
            real_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon)
        );
        CREATE TABLE IF NOT EXISTS pokemon_details (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            raw_count INTEGER,
            avg_weight REAL,
            viability_ceiling INTEGER,
            PRIMARY KEY (month, format_id, elo_tier, pokemon)
        );
        CREATE TABLE IF NOT EXISTS abilities (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            ability TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon, ability)
        );
        CREATE TABLE IF NOT EXISTS items (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            item TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon, item)
        );
        CREATE TABLE IF NOT EXISTS moves (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            move TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon, move)
        );
        CREATE TABLE IF NOT EXISTS spreads (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            nature TEXT,
            hp INTEGER, atk INTEGER, def INTEGER, spa INTEGER, spd INTEGER, spe INTEGER,
            spread_str TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon, spread_str)
        );
        CREATE TABLE IF NOT EXISTS tera_types (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            tera_type TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon, tera_type)
        );
        CREATE TABLE IF NOT EXISTS teammates (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon1 TEXT NOT NULL,
            pokemon2 TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon1, pokemon2)
        );
        CREATE TABLE IF NOT EXISTS checks_counters (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            counter_pokemon TEXT NOT NULL,
            score REAL,
            ko_pct REAL,
            switch_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, pokemon, counter_pokemon)
        );
        CREATE TABLE IF NOT EXISTS leads (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            pokemon TEXT NOT NULL,
            rank INTEGER,
            usage_pct REAL,
            raw_count INTEGER,
            PRIMARY KEY (month, format_id, elo_tier, pokemon)
        );
        CREATE TABLE IF NOT EXISTS metagame (
            month TEXT NOT NULL,
            format_id TEXT NOT NULL,
            elo_tier INTEGER NOT NULL,
            playstyle TEXT NOT NULL,
            usage_pct REAL,
            PRIMARY KEY (month, format_id, elo_tier, playstyle)
        );
        CREATE TABLE IF NOT EXISTS replays (
            replay_id TEXT PRIMARY KEY,
            format_id TEXT,
            rating INTEGER,
            player1 TEXT,
            player2 TEXT,
            uploadtime INTEGER,
            month TEXT
        );
        CREATE TABLE IF NOT EXISTS replay_teams (
            replay_id TEXT NOT NULL,
            side TEXT NOT NULL,
            pokemon TEXT NOT NULL,
            won INTEGER,
            PRIMARY KEY (replay_id, side, pokemon)
        );
    """)
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def patched_db(fresh_db, monkeypatch):
    import pipeline.db
    import pipeline.config
    monkeypatch.setattr(pipeline.config, "DB_PATH", fresh_db)
    monkeypatch.setattr(pipeline.db, "DB_PATH", fresh_db)
    yield fresh_db


SMOGON_INDEX_HTML = """
<html><body>
<a href="2022-11/">2022-11</a>
<a href="2022-12/">2022-12</a>
<a href="2023-01/">2023-01</a>
<a href="2023-02/">2023-02</a>
<a href="2024-01/">2024-01</a>
<a href="2025-01/">2025-01</a>
<a href="2026-01/">2026-01</a>
<a href="2026-04/">2026-04</a>
</body></html>
"""

SMOGON_MONTH_HTML = """
<html><body>
<a href="gen9ou-0.txt">gen9ou-0.txt</a>
<a href="gen9ou-0.txt.gz">gen9ou-0.txt.gz</a>
<a href="gen9ou-1500.txt">gen9ou-1500.txt</a>
<a href="gen9ou-1695.txt">gen9ou-1695.txt</a>
<a href="gen9ubers-0.txt">gen9ubers-0.txt</a>
<a href="gen9ou-0.json">gen9ou-0.json</a>
<a href="gen9ou-0.json.gz">gen9ou-0.json.gz</a>
<a href="gen9ou-0.json">chaos/gen9ou-0.json</a>
chaos/
leads/
metagame/
</body></html>
"""

SMOGON_LEADS_HTML = """
<html><body>
<a href="gen9ou-0.txt">gen9ou-0.txt</a>
</body></html>
"""

SMOGON_METAGAME_HTML = """
<html><body>
<a href="gen9ou-0.txt">gen9ou-0.txt</a>
</body></html>
"""


def make_usage_txt(total=50000, rows=None):
    if rows is None:
        rows = [
            (1, "Great Tusk", 18.52, 9260, 17.23, 8120, 15.12),
            (2, "Gholdengo", 12.41, 6205, 11.56, 5430, 10.11),
            (3, "Kingambit", 10.22, 5110, 9.54, 4456, 8.30),
        ]
    lines = [
        "Total battles: " + str(total),
        "",
        "+ ---- + ------------------- + --------- + --------- + --------- + --------- + --------- +",
        "| Rank | Pokemon             | Usage %   | Raw       | Raw %     | Real      | Real %   |",
        "+ ---- + ------------------- + --------- + --------- + --------- + --------- + --------- +",
    ]
    for rank, poke, usage, raw, raw_pct, real, real_pct in rows:
        lines.append(
            f"| {rank:>4} | {poke:<19} | {usage:>7}% | {raw:>8} | {raw_pct:>7}% | {real:>8} | {real_pct:>7}% |"
        )
    lines.append("+ ---- + ------------------- + --------- + --------- + --------- + --------- + --------- +")
    return "\n".join(lines)


def make_leads_txt(rows=None):
    if rows is None:
        rows = [
            (1, "Great Tusk", 24.5, 12250),
            (2, "Gholdengo", 18.3, 9150),
            (3, "Kingambit", 12.1, 6050),
        ]
    lines = [
        "+ ---- + ------------------- + --------- + --------- +",
        "| Rank | Pokemon             | Usage %   | Raw       |",
        "+ ---- + ------------------- + --------- + --------- +",
    ]
    for rank, poke, usage, raw in rows:
        lines.append(f"| {rank:>4} | {poke:<19} | {usage:>7}% | {raw:>8} |")
    lines.append("+ ---- + ------------------- + --------- + --------- +")
    return "\n".join(lines)


def make_metagame_txt(rows=None):
    if rows is None:
        rows = [
            ("Offense", 38.76),
            ("Balance", 35.02),
            ("Stall", 9.55),
            ("Weather", 16.67),
        ]
    return "\n".join(f"{playstyle}......{pct}%" for playstyle, pct in rows)


def make_chaos_json(pokemon_data=None):
    if pokemon_data is None:
        pokemon_data = {
            "Great Tusk": {
                "Raw count": 9260,
                "Viability Ceiling": [9260, 1415, 0.583],
                "Abilities": {"Protosynthesis": 8920, "Defiant": 340},
                "Items": {"Leftovers": 4200, "Heavy-Duty Boots": 3800},
                "Moves": {"Earthquake": 8500, "Headlong Rush        ": 7800},
                "Tera Types": {"Ground": 5200, "Steel": 2800},
                "Spreads": {"Adamant:252/252/4/0/0/4": 0.63},
                "Teammates": {"Gholdengo": 0.55, "King Gambit": 0.42},
                "Checks and Counters": {"Gholdengo": {"n": 1200, "p": 0.55, "d": 0.30}},
            },
            "Gholdengo": {
                "Raw count": 6205,
                "Viability Ceiling": [6205, 1380, 0.512],
                "Abilities": {"Good as Gold": 6000},
                "Items": {"Air Balloon": 3100, "Life Orb": 2000},
                "Moves": {"Shadow Ball": 5400, "Nasty Plot": 4900},
                "Tera Types": {"Steel": 4100, "Ghost": 1500},
                "Spreads": {"Timid:0/4/0/252/0/252": 0.71},
                "Teammates": {"Great Tusk": 0.55},
                "Checks and Counters": {"Great Tusk": {"n": 980, "p": 0.51, "d": 0.28}},
            },
        }
    import json
    return json.dumps({"data": pokemon_data})


def register_smogon_mocks(extra_month_html=None):
    responses.add(responses.GET, "https://www.smogon.com/stats", body=SMOGON_INDEX_HTML, status=200)
    for month in ["2022-11", "2022-12", "2023-01", "2023-02", "2024-01", "2025-01", "2026-01", "2026-04"]:
        responses.add(
            responses.GET,
            f"https://www.smogon.com/stats/{month}/",
            body=extra_month_html or SMOGON_MONTH_HTML,
            status=200,
        )
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/gen9ou-0.txt", body=make_usage_txt(), status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/gen9ou-1500.txt", body=make_usage_txt(total=30000), status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/gen9ou-1695.txt", body=make_usage_txt(total=15000), status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/gen9ubers-0.txt", body=make_usage_txt(total=10000), status=200)

    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/chaos/", body=SMOGON_MONTH_HTML, status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/chaos/gen9ou-0.json", body=make_chaos_json(), status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/chaos/gen9ou-1500.json", body=make_chaos_json(), status=200)

    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/leads/", body=SMOGON_LEADS_HTML, status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/leads/gen9ou-0.txt", body=make_leads_txt(), status=200)

    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/metagame/", body=SMOGON_MONTH_HTML, status=200)
    responses.add(responses.GET, "https://www.smogon.com/stats/2026-04/metagame/gen9ou-0.txt", body=make_metagame_txt(), status=200)


@pytest.fixture
def mock_smogon():
    register_smogon_mocks()
    yield
