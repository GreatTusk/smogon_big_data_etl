from google.cloud import bigquery


TABLE_FORMATS = "formats"
TABLE_MONTHS = "months"
TABLE_ELO_TIERS = "elo_tiers"
TABLE_DISCOVERED_SOURCES = "discovered_sources"
TABLE_USAGE_STATS = "usage_stats"
TABLE_POKEMON_DETAILS = "pokemon_details"
TABLE_ABILITIES = "abilities"
TABLE_ITEMS = "items"
TABLE_MOVES = "moves"
TABLE_SPREADS = "spreads"
TABLE_TERA_TYPES = "tera_types"
TABLE_TEAMMATES = "teammates"
TABLE_CHECKS_COUNTERS = "checks_counters"
TABLE_LEADS = "leads"
TABLE_METAGAME = "metagame"
TABLE_REPLAYS = "replays"
TABLE_REPLAY_TEAMS = "replay_teams"

ALL_TABLES = [
    TABLE_FORMATS,
    TABLE_MONTHS,
    TABLE_ELO_TIERS,
    TABLE_DISCOVERED_SOURCES,
    TABLE_USAGE_STATS,
    TABLE_POKEMON_DETAILS,
    TABLE_ABILITIES,
    TABLE_ITEMS,
    TABLE_MOVES,
    TABLE_SPREADS,
    TABLE_TERA_TYPES,
    TABLE_TEAMMATES,
    TABLE_CHECKS_COUNTERS,
    TABLE_LEADS,
    TABLE_METAGAME,
    TABLE_REPLAYS,
    TABLE_REPLAY_TEAMS,
]

SCHEMA_FORMATS = [
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("generation", "INTEGER", default_value_expression="9"),
    bigquery.SchemaField("tier", "STRING"),
    bigquery.SchemaField("name", "STRING"),
]

SCHEMA_MONTHS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("total_battles", "INTEGER"),
]

SCHEMA_ELO_TIERS = [
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
]

SCHEMA_DISCOVERED_SOURCES = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("source_type", "STRING", mode="REQUIRED", default_value_expression="'usage'"),
]

SCHEMA_USAGE_STATS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("rank", "INTEGER"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
    bigquery.SchemaField("raw_count", "INTEGER"),
    bigquery.SchemaField("raw_pct", "FLOAT"),
    bigquery.SchemaField("real_count", "INTEGER"),
    bigquery.SchemaField("real_pct", "FLOAT"),
]

SCHEMA_POKEMON_DETAILS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("raw_count", "INTEGER"),
    bigquery.SchemaField("avg_weight", "FLOAT"),
    bigquery.SchemaField("viability_ceiling", "INTEGER"),
]

SCHEMA_ABILITIES = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("ability", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_ITEMS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("item", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_MOVES = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("move", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_SPREADS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("nature", "STRING"),
    bigquery.SchemaField("hp", "INTEGER"),
    bigquery.SchemaField("atk", "INTEGER"),
    bigquery.SchemaField("def", "INTEGER"),
    bigquery.SchemaField("spa", "INTEGER"),
    bigquery.SchemaField("spd", "INTEGER"),
    bigquery.SchemaField("spe", "INTEGER"),
    bigquery.SchemaField("spread_str", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_TERA_TYPES = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("tera_type", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_TEAMMATES = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon1", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("pokemon2", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_CHECKS_COUNTERS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("counter_pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("score", "FLOAT"),
    bigquery.SchemaField("ko_pct", "FLOAT"),
    bigquery.SchemaField("switch_pct", "FLOAT"),
]

SCHEMA_LEADS = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("rank", "INTEGER"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
    bigquery.SchemaField("raw_count", "INTEGER"),
]

SCHEMA_METAGAME = [
    bigquery.SchemaField("month", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("elo_tier", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("playstyle", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("usage_pct", "FLOAT"),
]

SCHEMA_REPLAYS = [
    bigquery.SchemaField("replay_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("format_id", "STRING"),
    bigquery.SchemaField("rating", "INTEGER"),
    bigquery.SchemaField("player1", "STRING"),
    bigquery.SchemaField("player2", "STRING"),
    bigquery.SchemaField("uploadtime", "INTEGER"),
    bigquery.SchemaField("month", "STRING"),
]

SCHEMA_REPLAY_TEAMS = [
    bigquery.SchemaField("replay_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("side", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("pokemon", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("won", "INTEGER"),
]

SCHEMA_MAP = {
    TABLE_FORMATS: SCHEMA_FORMATS,
    TABLE_MONTHS: SCHEMA_MONTHS,
    TABLE_ELO_TIERS: SCHEMA_ELO_TIERS,
    TABLE_DISCOVERED_SOURCES: SCHEMA_DISCOVERED_SOURCES,
    TABLE_USAGE_STATS: SCHEMA_USAGE_STATS,
    TABLE_POKEMON_DETAILS: SCHEMA_POKEMON_DETAILS,
    TABLE_ABILITIES: SCHEMA_ABILITIES,
    TABLE_ITEMS: SCHEMA_ITEMS,
    TABLE_MOVES: SCHEMA_MOVES,
    TABLE_SPREADS: SCHEMA_SPREADS,
    TABLE_TERA_TYPES: SCHEMA_TERA_TYPES,
    TABLE_TEAMMATES: SCHEMA_TEAMMATES,
    TABLE_CHECKS_COUNTERS: SCHEMA_CHECKS_COUNTERS,
    TABLE_LEADS: SCHEMA_LEADS,
    TABLE_METAGAME: SCHEMA_METAGAME,
    TABLE_REPLAYS: SCHEMA_REPLAYS,
    TABLE_REPLAY_TEAMS: SCHEMA_REPLAY_TEAMS,
}
