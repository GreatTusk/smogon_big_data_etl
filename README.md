# Pokemon Dream Duos Pipeline

This project builds a data pipeline that identifies the most common and best-performing Pokemon pairs ("dream duos") in Pokemon Showdown Gen 9 OU. The pipeline merges two public datasets, filters for high-competition matches, computes co-occurrence and win rates, and exports a ranked CSV.

## Datasets Used (and Why They Fit Big Data)

### 1) Smogon Stats "Chaos" JSON (teammate co-occurrence matrix)
- Source: Smogon monthly stats archives
- URL pattern used by the pipeline:
  - `https://www.smogon.com/stats/YYYY-MM/chaos/gen9ou-1695.json`
- What it contains:
  - Aggregated usage and teammate statistics for the Gen 9 OU ladder.
  - "Teammates" section lists how frequently each Pokemon appears with others.
- Why it is big-data appropriate:
  - Aggregates massive volumes of ladder battles into a single, high-signal dataset.
  - Provides a stable, month-level snapshot that supports temporal comparisons and repeatable analysis.
  - Represents the behavior of a large, globally distributed player base, making it ideal for population-level insights.
- Why we use it:
  - It offers a high-ladder proxy (1695 rating tier) that closely tracks 1800+ play and is publicly available.
  - It provides reliable, aggregated co-occurrence signals even when replay logs are missing or incomplete.

### 2) Pokemon Showdown Replay Search API (live replay logs)
- Source: Pokemon Showdown public replay service
- Endpoints used by the pipeline:
  - Search metadata: `https://replay.pokemonshowdown.com/search.json?format=gen9ou&page=1`
  - Replay logs: `https://replay.pokemonshowdown.com/<replay_id>.log`
- What it contains:
  - Near-real-time match metadata (format, rating, players, replay id).
  - Detailed battle logs from which teams and winners can be reconstructed.
- Why it is big-data appropriate:
  - High volume and velocity: hundreds of new replays per day for popular formats.
  - Semi-structured text logs allow scalable parsing and feature extraction (teams, outcomes).
  - Enables granular, match-level analytics and validation of aggregated trends.
- Why we use it:
  - It captures live meta shifts and lets us compute win rates at the pair level.
  - It provides transparent, reproducible evidence for each pairing (not just aggregated stats).

## How We Get to Dream Duos (Data Flow)
- Step 1: Smogon Chaos JSON provides aggregated teammate frequencies (co-occurrence signals).
- Step 2: Replay Search API provides match metadata and replay ids.
- Step 3: Replay logs provide team membership via `|switch|` lines (each unique species seen on a side is part of that team).
- Step 4: The pipeline filters by Elo, counts pairs within each team, and computes win rates from `|win|` lines.
- Step 5: Co-occurrence counts from both sources are merged, ranked, and exported.

## Dataset Samples (Preview)

### Smogon Chaos JSON (real sample, trimmed)
Source month used by the sample: `2026-04`
```json
{
  "info": {
    "metagame": "gen9ou"
  },
  "data": {
    "Great Tusk": {
      "Teammates": {
        "Raging Bolt": 10323.846898460906,
        "Gholdengo": 15877.440215418977,
        "Dragonite": 15020.468091988245,
        "Kingambit": 13673.157391756937,
        "Dragapult": 6837.595001786193
      }
    }
  }
}
```

### Replay Search API metadata (real sample, trimmed)
```json
{
  "uploadtime": 1779156216,
  "id": "gen9ou-2612886364",
  "format": "[Gen 9] OU",
  "players": [
    "pokemhnatiaslatias",
    "eYeek"
  ],
  "rating": 1470,
  "private": 0,
  "password": null
}
```

### Replay log excerpt (real sample, trimmed)
```text
|player|p1|amiruae|psychic-gen4|1464
|player|p2|FiiFiFoFum|erika-gen1rb|1518
|switch|p1a: Samurott|Samurott-Hisui, M|100/100
|switch|p2a: Primarina|Primarina, F|100/100
|switch|p1a: Volcanion|Volcanion|100/100
|switch|p2a: Samurott|Samurott-Hisui, M|100/100
```

Why this matters:
- The `|switch|` lines are the concrete evidence of which Pokemon are on each team.
- The pipeline collects all unique Pokemon seen for each player, then forms every pair from those team lists.

## How the Pipeline Uses the Data
- Smogon stats supply a large, stable co-occurrence signal (pairs that appear together often).
- Replay logs supply match-level outcomes (win rates for pairs at high Elo).
- The pipeline filters for high-ladder games (Elo >= 1800) and exports ranked pairs to CSV.

## Outputs
- CSV file: `pokemon_dream_duos_gen9ou_1800elo.csv`
- Fields: `rank`, `pokemon_1`, `pokemon_2`, `co_occurrence_count`, `wins`, `win_rate_pct`

## Pandas DataFrame Sample Format (Input Datasets)

### A) Smogon Chaos JSON -> Teammate Pairs DataFrame
Example `pandas` view after extracting pairs from the Smogon "Teammates" section:

| pokemon_1  | pokemon_2 | teammate_score | source_month |
|------------|-----------|---------------:|--------------|
| Great Tusk | Kingambit | 13673.1574     | 2026-04      |
| Great Tusk | Dragonite | 15020.4681     | 2026-04      |
| Great Tusk | Gholdengo | 15877.4402     | 2026-04      |

Field descriptions:
- `pokemon_1`: First Pokemon in the pair (alphabetical ordering to normalize pairs).
- `pokemon_2`: Second Pokemon in the pair (alphabetical ordering to normalize pairs).
- `teammate_score`: Smogon co-occurrence score from the "Teammates" matrix (usage delta, not raw counts).
- `source_month`: Month of the Smogon stats archive used (`YYYY-MM`).

### B) Replay Search API -> Replay Metadata DataFrame
Example `pandas` view after fetching replay metadata:

| replay_id        | format     | rating | player_1           | player_2 | uploadtime  |
|------------------|------------|-------:|--------------------|----------|-------------|
| gen9ou-2612886364| [Gen 9] OU  | 1470   | pokemhnatiaslatias | eYeek    | 1779156216  |

Field descriptions:
- `replay_id`: Replay identifier used to fetch the full log.
- `format`: Ladder format label returned by the API.
- `rating`: Player 1 rating for the match (used for Elo filtering).
- `player_1`: Name of player on side p1.
- `player_2`: Name of player on side p2.
- `uploadtime`: Unix timestamp when the replay was uploaded.

### C) Replay Log -> Team Membership DataFrame
Example `pandas` view after parsing `|switch|` lines in a replay log:

| replay_id        | side | pokemon      |
|------------------|------|--------------|
| gen9ou-2612886364| p1   | Samurott-Hisui |
| gen9ou-2612886364| p1   | Volcanion    |
| gen9ou-2612886364| p2   | Primarina    |
| gen9ou-2612886364| p2   | Samurott-Hisui |

Field descriptions:
- `replay_id`: Replay identifier linking this row back to metadata.
- `side`: Team side (p1 or p2) from the battle log.
- `pokemon`: Cleaned Pokemon species name extracted from `|switch|` lines.

## Run
```bash
python3 pokemon_dream_duos_pipeline.py
```

## Notes for Review
- The Smogon dataset provides a validated, large-scale statistical backbone.
- The Replay API provides live, granular evidence and win-rate outcomes.
- Together they satisfy both volume (big-data scale) and verifiable detail (traceable replays).
