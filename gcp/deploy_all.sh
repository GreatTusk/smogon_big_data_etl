#!/usr/bin/env bash
# =============================================================================
# GCP Deployment Script for Smogon ETL Pipeline (gen9ou only)
# Run this entire script once from Cloud Shell to set up everything.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ---- Variables ----
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project --quiet)}"
REGION="${REGION:-us-central1}"
RAW_BUCKET="smogon-raw-${PROJECT_ID}"
DAGS_BUCKET="smogon-dags-${PROJECT_ID}"
COMPOSER_ENV="smogon-composer-env"
SA_NAME="smogon-pipeline-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SQL_DIR="${REPO_ROOT}/gcp/sql"

# =============================================================================
# STEP 1: Clone repo
# =============================================================================
echo "=== Step 1: Cloning repository ==="
if [[ -d "$REPO_ROOT" ]]; then
    echo "  Repo already exists — pulling latest..."
    git -C "$REPO_ROOT" pull
else
    echo "  Cloning..."
    git clone https://github.com/GreatTusk/smogon_big_data_etl.git "$REPO_ROOT"
fi
SQL_DIR="$REPO_ROOT/gcp/sql"
echo "  Done."

# =============================================================================
# STEP 2: Variables are already set above
# =============================================================================
echo "=== Step 2: Configuration ==="
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Raw bucket:    gs://${RAW_BUCKET}"
echo "  DAGs bucket:   gs://${DAGS_BUCKET}"
echo "  Composer env:  $COMPOSER_ENV"
echo "  Service acct:  $SA_EMAIL"

# =============================================================================
# STEP 3: Enable APIs
# =============================================================================
echo "=== Step 3: Enabling GCP APIs ==="
gcloud services enable \
  composer.googleapis.com \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  storage.googleapis.com \
  storage-api.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  --project="$PROJECT_ID" --quiet
echo "  Done."

# =============================================================================
# STEP 4: Create GCS buckets
# =============================================================================
echo "=== Step 4: Creating GCS buckets ==="
gsutil mb -p "$PROJECT_ID" -l "$REGION" -c STANDARD "gs://${RAW_BUCKET}/" 2>/dev/null || echo "  Raw bucket already exists"
gsutil uniformbucketlevelaccess set on "gs://${RAW_BUCKET}/" 2>/dev/null || true

gsutil mb -p "$PROJECT_ID" -l "$REGION" -c STANDARD "gs://${DAGS_BUCKET}/" 2>/dev/null || echo "  DAGs bucket already exists"
gsutil uniformbucketlevelaccess set on "gs://${DAGS_BUCKET}/" 2>/dev/null || true

for subdir in usage chaos leads metagame replays; do
  gsutil cp /dev/null "gs://${RAW_BUCKET}/${subdir}/" 2>/dev/null || true
done

echo "  Done."

# =============================================================================
# STEP 5: Create BigQuery datasets and tables
# =============================================================================
echo "=== Step 5: Creating BigQuery datasets and tables ==="
bq mk --dataset --location="$REGION" --description="Smogon raw data layer" "${PROJECT_ID}:smogon_raw" 2>/dev/null || echo "  smogon_raw already exists"
bq mk --dataset --location="$REGION" --description="Smogon staging transforms" "${PROJECT_ID}:smogon_staging" 2>/dev/null || echo "  smogon_staging already exists"
bq mk --dataset --location="$REGION" --description="Smogon dimensional warehouse" "${PROJECT_ID}:smogon_dw" 2>/dev/null || echo "  smogon_dw already exists"

for ddl in 01_ddl_raw.sql 02_ddl_staging.sql 03_ddl_dimensional.sql 04_views_dashboard.sql; do
  echo "  Running ${ddl}..."
  bq query --use_legacy_sql=false --project_id="$PROJECT_ID" --location="$REGION" < "${SQL_DIR}/${ddl}"
done
echo "  Done."

# =============================================================================
# STEP 6: Create service account and IAM
# =============================================================================
echo "=== Step 6: Creating service account and IAM ==="
gcloud iam service-accounts create "$SA_NAME" \
  --project="$PROJECT_ID" \
  --display-name="Smogon ETL Pipeline Service Account" 2>/dev/null || echo "  SA already exists"

for role in roles/composer.worker roles/bigquery.dataEditor roles/bigquery.jobUser \
            roles/storage.objectAdmin roles/storage.objectViewer \
            roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" --quiet 2>/dev/null || true
done

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@cloudcomposer-accounts.iam.gserviceaccount.com" \
  --role="roles/composer.ServiceAgentV2Ext" --quiet 2>/dev/null || true

echo "  Done."

# =============================================================================
# STEP 7: Create Cloud Composer environment
# =============================================================================
echo "=== Step 7: Creating Cloud Composer environment ==="
echo "  This takes ~15-20 minutes. Waiting..."
gcloud composer environments create "$COMPOSER_ENV" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --image-version="composer-2-airflow-2" \
  --service-account="$SA_EMAIL" \
  --env-variables="RAW_BUCKET=smogon-raw-${PROJECT_ID},DAGS_BUCKET=smogon-dags-${PROJECT_ID}" \
  --network="default" \
  --subnetwork="default"

echo "  Composer environment created: $COMPOSER_ENV"

# Wait for environment to be RUNNING
echo "  Waiting for Composer to be ready..."
while true; do
  STATUS=$(gcloud composer environments describe "$COMPOSER_ENV" --location="$REGION" --format="value(state)" 2>/dev/null)
  echo "    Status: $STATUS"
  if [[ "$STATUS" == "RUNNING" ]]; then
    break
  fi
  if [[ "$STATUS" == "ERROR" ]]; then
    echo "  ERROR: Composer environment failed to create. Check GCP Console."
    exit 1
  fi
  sleep 30
done

echo "  Composer is ready."

# =============================================================================
# STEP 8: Deploy DAGs and pipeline code
# =============================================================================
echo "=== Step 8: Deploying DAGs and pipeline code ==="

echo "  Uploading DAGs..."
gcloud composer environments storage dags import \
  --environment="$COMPOSER_ENV" \
  --location="$REGION" \
  --source="${REPO_ROOT}/gcp/dags/" \
  --project="$PROJECT_ID"

echo "  Uploading pipeline modules..."
gsutil -m rsync -r "${REPO_ROOT}/gcp/pipeline/" "gs://${DAGS_BUCKET}/plugins/pipeline/"

echo "  Installing PyPI packages (this takes ~5 minutes)..."
gcloud composer environments update "$COMPOSER_ENV" \
  --location="$REGION" \
  --update-pypi-packages-from-file="${REPO_ROOT}/gcp/requirements-composer.txt" \
  --project="$PROJECT_ID"

echo "  Done. DAGs will appear in Airflow within 2-5 minutes."

# =============================================================================
# DONE
# =============================================================================
echo ""
echo "============================================================"
echo "All done! Infrastructure is deployed."
echo ""
echo "Next: Run the pipeline for gen9ou"
echo "  1. Open Cloud Console → search 'Cloud Composer' → open $COMPOSER_ENV"
echo "  2. Click 'Airflow Web UI'"
echo "  3. Trigger smogon_master_dag with: {\"format\": \"gen9ou\"}"
echo ""
echo "Or from Cloud Shell:"
echo "  gcloud composer environments run $COMPOSER_ENV --location=$REGION trigger_dag -- smogon_master_dag"
echo "============================================================"