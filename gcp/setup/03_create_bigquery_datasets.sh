#!/usr/bin/env bash
# =============================================================================
# 03_create_bigquery_datasets.sh — Create BQ datasets and tables
# =============================================================================
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-us-central1}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project-id> [region]"
  exit 1
fi

SQL_DIR="$(cd "$(dirname "$0")/../sql" && pwd)"
echo "=== Creating BigQuery datasets and tables ==="

# Create datasets
for ds in smogon_raw smogon_staging smogon_dw; do
  bq mk --dataset --location="$REGION" --description="Smogon ${ds} layer" "${PROJECT_ID}:${ds}" 2>/dev/null || echo "Dataset $ds may already exist"
done

# Execute DDL scripts
for ddl in 01_ddl_raw.sql 02_ddl_staging.sql 03_ddl_dimensional.sql 04_views_dashboard.sql; do
  echo "  Executing $ddl ..."
  bq query --use_legacy_sql=false --project_id="$PROJECT_ID" --location="$REGION" < "${SQL_DIR}/${ddl}"
done

echo "=== BigQuery setup complete ==="
