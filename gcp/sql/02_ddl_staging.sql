-- =============================================================================
-- STAGING LAYER: smogon_staging
-- Parsed/normalized data matching the original SQLite schema
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS smogon_staging;

-- Format dimension (parse on write from format_id)
CREATE TABLE IF NOT EXISTS smogon_staging.formats (
  format_id STRING NOT NULL,
  generation INT64 DEFAULT 9,
  tier STRING,
  name STRING,
  PRIMARY KEY (format_id) NOT ENFORCED
);

-- Month metadata
CREATE TABLE IF NOT EXISTS smogon_staging.months (
  month STRING NOT NULL,
  total_battles INT64,
  PRIMARY KEY (month) NOT ENFORCED
);

-- Elo tier lookup
CREATE TABLE IF NOT EXISTS smogon_staging.elo_tiers (
  elo_tier INT64 NOT NULL,
  PRIMARY KEY (elo_tier) NOT ENFORCED
);

-- Usage stats
CREATE TABLE IF NOT EXISTS smogon_staging.usage_stats (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  rank INT64,
  usage_pct FLOAT64,
  raw_count INT64,
  raw_pct FLOAT64,
  real_count INT64,
  real_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY RANGE_BUCKET(elo_tier, GENERATE_ARRAY(0, 2000, 100))
CLUSTER BY format_id, month, pokemon;

-- Pokemon details (from chaos)
CREATE TABLE IF NOT EXISTS smogon_staging.pokemon_details (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  raw_count INT64,
  avg_weight FLOAT64,
  viability_ceiling INT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Abilities
CREATE TABLE IF NOT EXISTS smogon_staging.abilities (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  ability STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Items
CREATE TABLE IF NOT EXISTS smogon_staging.items (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  item STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Moves
CREATE TABLE IF NOT EXISTS smogon_staging.moves (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  move STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Spreads (EV/nature combinations)
CREATE TABLE IF NOT EXISTS smogon_staging.spreads (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  nature STRING,
  hp INT64,
  atk INT64,
  def INT64,
  spa INT64,
  spd INT64,
  spe INT64,
  spread_str STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Tera types
CREATE TABLE IF NOT EXISTS smogon_staging.tera_types (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  tera_type STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Teammates (co-occurrence)
CREATE TABLE IF NOT EXISTS smogon_staging.teammates (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon1 STRING NOT NULL,
  pokemon2 STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Checks and counters
CREATE TABLE IF NOT EXISTS smogon_staging.checks_counters (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  counter_pokemon STRING NOT NULL,
  score FLOAT64,
  ko_pct FLOAT64,
  switch_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Leads
CREATE TABLE IF NOT EXISTS smogon_staging.leads (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  rank INT64,
  usage_pct FLOAT64,
  raw_count INT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Metagame
CREATE TABLE IF NOT EXISTS smogon_staging.metagame (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  playstyle STRING NOT NULL,
  usage_pct FLOAT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY format_id, month;

-- Replays
CREATE TABLE IF NOT EXISTS smogon_staging.replays (
  replay_id STRING NOT NULL,
  format_id STRING,
  rating INT64,
  player1 STRING,
  player2 STRING,
  uploadtime INT64,
  month STRING,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (replay_id) NOT ENFORCED
)
CLUSTER BY format_id;

-- Replay teams
CREATE TABLE IF NOT EXISTS smogon_staging.replay_teams (
  replay_id STRING NOT NULL,
  side STRING NOT NULL,
  pokemon STRING NOT NULL,
  won INT64,
  _ingested_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY replay_id;
