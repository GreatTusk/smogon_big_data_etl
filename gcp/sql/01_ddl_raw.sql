-- =============================================================================
-- RAW LAYER: smogon_raw
-- Stores original downloaded payloads as-is for audit/reprocessing
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS smogon_raw;

-- Raw usage stats (tab-separated text stored as STRING)
CREATE TABLE IF NOT EXISTS smogon_raw.usage_stats (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  raw_payload STRING,
  source_url STRING,
  download_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  file_size_bytes INT64
)
PARTITION BY RANGE_BUCKET(elo_tier, GENERATE_ARRAY(0, 2000, 100))
CLUSTER BY format_id, month;

-- Raw chaos JSON (nested JSON stored as STRING)
CREATE TABLE IF NOT EXISTS smogon_raw.chaos_json (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  raw_payload STRING,
  source_url STRING,
  download_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  file_size_bytes INT64
)
PARTITION BY RANGE_BUCKET(elo_tier, GENERATE_ARRAY(0, 2000, 100))
CLUSTER BY format_id, month;

-- Raw leads stats
CREATE TABLE IF NOT EXISTS smogon_raw.leads_stats (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  raw_payload STRING,
  source_url STRING,
  download_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  file_size_bytes INT64
)
PARTITION BY RANGE_BUCKET(elo_tier, GENERATE_ARRAY(0, 2000, 100))
CLUSTER BY format_id, month;

-- Raw metagame stats
CREATE TABLE IF NOT EXISTS smogon_raw.metagame_stats (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  raw_payload STRING,
  source_url STRING,
  download_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  file_size_bytes INT64
)
PARTITION BY RANGE_BUCKET(elo_tier, GENERATE_ARRAY(0, 2000, 100))
CLUSTER BY format_id, month;

-- Raw discovered sources catalog
CREATE TABLE IF NOT EXISTS smogon_raw.discovered_sources (
  month STRING NOT NULL,
  format_id STRING NOT NULL,
  elo_tier INT64 NOT NULL,
  source_type STRING NOT NULL,
  discovered_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (month, format_id, elo_tier, source_type) NOT ENFORCED
)
CLUSTER BY format_id, month;
