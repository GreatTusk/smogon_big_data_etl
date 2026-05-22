#!/usr/bin/env bash
# =============================================================================
# 05_setup_iam.sh — Create service account and configure IAM
# =============================================================================
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project-id>"
  exit 1
fi

SA_NAME="smogon-pipeline-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Creating service account: $SA_EMAIL ==="

# Create the service account
gcloud iam service-accounts create "$SA_NAME" \
  --project="$PROJECT_ID" \
  --display-name="Smogon ETL Pipeline Service Account" || echo "SA may already exist"

# Grant BigQuery roles
for role in roles/bigquery.dataEditor roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" --quiet
done

# Grant GCS roles
for role in roles/storage.objectAdmin roles/storage.objectViewer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" --quiet
done

# Grant Composer worker role
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/composer.worker" --quiet

# Grant logging + monitoring
for role in roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" --quiet
done

echo "=== IAM setup complete ==="
echo "  Service account: $SA_EMAIL"
