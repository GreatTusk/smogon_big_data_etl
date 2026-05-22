#!/usr/bin/env bash
# =============================================================================
# 01_enable_apis.sh — Enable all required GCP APIs
# =============================================================================
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project-id>"
  exit 1
fi

echo "=== Enabling APIs for project: $PROJECT_ID ==="

apis=(
  composer.googleapis.com
  bigquery.googleapis.com
  bigqueryconnection.googleapis.com
  storage.googleapis.com
  storage-api.googleapis.com
  cloudbuild.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
  cloudresourcemanager.googleapis.com
  iam.googleapis.com
  iamcredentials.googleapis.com
)

for api in "${apis[@]}"; do
  echo "  Enabling $api ..."
  gcloud services enable "$api" --project="$PROJECT_ID" --quiet
done

echo "=== All APIs enabled ==="
