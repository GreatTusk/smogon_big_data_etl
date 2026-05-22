#!/usr/bin/env bash
# =============================================================================
# 02_create_gcs_buckets.sh — Create GCS buckets for raw data + DAGs
# =============================================================================
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-us-central1}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project-id> [region]"
  exit 1
fi

RAW_BUCKET="smogon-raw-${PROJECT_ID}"
DAGS_BUCKET="smogon-dags-${PROJECT_ID}"

echo "=== Creating GCS buckets in $REGION ==="

# Raw data bucket (holds downloaded Smogon files for caching)
gsutil mb -p "$PROJECT_ID" -l "$REGION" -c STANDARD "gs://${RAW_BUCKET}/" || echo "Bucket $RAW_BUCKET may already exist"
gsutil uniformbucketlevelaccess set on "gs://${RAW_BUCKET}/" || true

# DAGs bucket for Cloud Composer
gsutil mb -p "$PROJECT_ID" -l "$REGION" -c STANDARD "gs://${DAGS_BUCKET}/" || echo "Bucket $DAGS_BUCKET may already exist"
gsutil uniformbucketlevelaccess set on "gs://${DAGS_BUCKET}/" || true

# Create subdirectories in raw bucket
for subdir in usage chaos leads metagame replays; do
  gsutil cp /dev/null "gs://${RAW_BUCKET}/${subdir}/" 2>/dev/null || true
done

echo "=== Buckets created ==="
echo "  Raw data: gs://${RAW_BUCKET}"
echo "  DAGs:     gs://${DAGS_BUCKET}"
