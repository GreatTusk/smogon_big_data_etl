-- =============================================================================
-- DIMENSIONAL LAYER: smogon_dw
-- Star schema for analytics / Looker Studio
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS smogon_dw;

-- ── DIMENSIONS ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS smogon_dw.dim_date (
  date_key STRING NOT NULL,   -- YYYY-MM
  year INT64,
  month INT64,
  quarter STRING,
  first_day DATE,
  last_day DATE,
  PRIMARY KEY (date_key) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS smogon_dw.dim_format (
  format_key STRING NOT NULL,  -- format_id
  generation INT64,
  tier STRING,
  category STRING,             -- ou, ubers, uu, nu, pu, zu, lc, etc.
  battle_type STRING,          -- singles, doubles, vgc, etc.
  PRIMARY KEY (format_key) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS smogon_dw.dim_elo_tier (
  elo_tier_key INT64 NOT NULL,
  tier_label STRING,           -- "All", "1500+", "1630+", etc.
  tier_group STRING,           -- "low", "mid", "high", "top"
  PRIMARY KEY (elo_tier_key) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS smogon_dw.dim_pokemon (
  pokemon_key STRING NOT NULL,
  display_name STRING,
  type1 STRING,                -- nullable; enrich later
  type2 STRING,
  generation_introduced INT64,
  PRIMARY KEY (pokemon_key) NOT ENFORCED
);

-- ── FACT TABLES ─────────────────────────────────────────────────────────────

-- Usage statistics
CREATE TABLE IF NOT EXISTS smogon_dw.fact_usage (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  rank INT64,
  usage_pct FLOAT64,
  raw_count INT64,
  raw_pct FLOAT64,
  real_count INT64,
  real_pct FLOAT64
)
PARTITION BY RANGE_BUCKET(elo_tier, GENERATE_ARRAY(0, 2000, 100))
CLUSTER BY format_id, pokemon;

-- Pokemon details / viability
CREATE TABLE IF NOT EXISTS smogon_dw.fact_pokemon_details (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  raw_count INT64,
  avg_weight FLOAT64,
  viability_ceiling INT64
)
CLUSTER BY format_id, pokemon;

-- Ability usage
CREATE TABLE IF NOT EXISTS smogon_dw.fact_abilities (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  ability STRING NOT NULL,
  usage_pct FLOAT64
)
CLUSTER BY format_id, pokemon;

-- Item usage
CREATE TABLE IF NOT EXISTS smogon_dw.fact_items (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  item STRING NOT NULL,
  usage_pct FLOAT64
)
CLUSTER BY format_id, pokemon;

-- Move usage
CREATE TABLE IF NOT EXISTS smogon_dw.fact_moves (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  move STRING NOT NULL,
  usage_pct FLOAT64
)
CLUSTER BY format_id, pokemon;

-- EV spreads
CREATE TABLE IF NOT EXISTS smogon_dw.fact_spreads (
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
  usage_pct FLOAT64
)
CLUSTER BY format_id, pokemon;

-- Tera type usage
CREATE TABLE IF NOT EXISTS smogon_dw.fact_tera_types (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  tera_type STRING NOT NULL,
  usage_pct FLOAT64
)
CLUSTER BY format_id, pokemon;

-- Teammate co-occurrence
CREATE TABLE IF NOT EXISTS smogon_dw.fact_teammates (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon1 STRING NOT NULL,
  pokemon2 STRING NOT NULL,
  usage_pct FLOAT64
)
CLUSTER BY format_id, pokemon1;

-- Checks and counters
CREATE TABLE IF NOT EXISTS smogon_dw.fact_checks_counters (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  counter_pokemon STRING NOT NULL,
  score FLOAT64,
  ko_pct FLOAT64,
  switch_pct FLOAT64
)
CLUSTER BY format_id, pokemon;

-- Leads
CREATE TABLE IF NOT EXISTS smogon_dw.fact_leads (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  pokemon STRING NOT NULL,
  rank INT64,
  usage_pct FLOAT64,
  raw_count INT64
)
CLUSTER BY format_id, pokemon;

-- Metagame
CREATE TABLE IF NOT EXISTS smogon_dw.fact_metagame (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  playstyle STRING NOT NULL,
  usage_pct FLOAT64
)
CLUSTER BY format_id, playstyle;

-- Replays
CREATE TABLE IF NOT EXISTS smogon_dw.fact_replays (
  replay_id STRING NOT NULL,
  format_id STRING,
  rating INT64,
  player1 STRING,
  player2 STRING,
  uploadtime INT64,
  month STRING
)
CLUSTER BY format_id;

-- Replay teams
CREATE TABLE IF NOT EXISTS smogon_dw.fact_replay_teams (
  replay_id STRING NOT NULL,
  side STRING NOT NULL,
  pokemon STRING NOT NULL,
  won INT64
)
CLUSTER BY replay_id;
