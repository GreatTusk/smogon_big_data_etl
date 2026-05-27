#!/usr/bin/env bash
# GCP ETL Resource Provisioning Script
# Run this from Cloud Shell to create all required infrastructure.
# Usage: bash setup_resources.sh

set -euo pipefail

# ---- Configuration - edit these or set env vars before running ----
PROJECT_ID="${PROJECT_ID:?"PROJECT_ID must be set"}"
REGION="${REGION:-us-central1}"
BUCKET_NAME="${BUCKET_NAME:-smogon-etl-${PROJECT_ID}}"
BQ_DATASET="${BQ_DATASET:-smogon_etl}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-smogon-etl-sa}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== GCP ETL Resource Setup ==="
echo "Project:      ${PROJECT_ID}"
echo "Region:       ${REGION}"
echo "Bucket:       ${BUCKET_NAME}"
echo "BQ Dataset:   ${BQ_DATASET}"
echo "Service Acct: ${SERVICE_ACCOUNT}"
echo "=============================="

# 1. Set project
echo ">>> Setting project..."
gcloud config set project "${PROJECT_ID}"

# 2. Enable required APIs
echo ">>> Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    storage.googleapis.com \
    --project="${PROJECT_ID}"

# 3. Create service account (idempotent)
echo ">>> Creating service account..."
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project="${PROJECT_ID}" &>/dev/null; then
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="Smogon ETL Service Account" \
        --project="${PROJECT_ID}"
    echo "Created service account: ${SERVICE_ACCOUNT}"
else
    echo "Service account already exists: ${SERVICE_ACCOUNT}"
fi

# 4. Create Cloud Storage bucket (idempotent)
echo ">>> Creating Cloud Storage bucket..."
if gsutil ls "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "Bucket already exists: gs://${BUCKET_NAME}"
else
    gsutil mb -l "${REGION}" "gs://${BUCKET_NAME}"
    gsutil uniformbucketlevelaccess set on "gs://${BUCKET_NAME}"
    echo "Created bucket: gs://${BUCKET_NAME}"
fi

# 5. Create BigQuery dataset (idempotent)
echo ">>> Creating BigQuery dataset..."
bq --location="${REGION}" mk --dataset --exists_ok "${PROJECT_ID}:${BQ_DATASET}"
echo "Ensured dataset: ${PROJECT_ID}:${BQ_DATASET}"

# 6. Grant project-level BigQuery job user
echo ">>> Granting IAM roles..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.jobUser" \
    --condition=None \
    --quiet

# 7. Grant bucket-level storage.objectAdmin
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectAdmin" "gs://${BUCKET_NAME}"

# 8. Grant dataset-level BigQuery dataEditor
bq add-iam-policy-binding \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.dataEditor" \
    "${PROJECT_ID}:${BQ_DATASET}"

echo ""
echo "=== Setup Complete ==="
echo "Service Account: ${SERVICE_ACCOUNT}"
echo "Bucket:          gs://${BUCKET_NAME}"
echo "BigQuery Dataset: ${PROJECT_ID}:${BQ_DATASET}"
echo ""
echo "To run the ETL as a Cloud Run job:"
echo "  1. Build and push the image:"
echo "     gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/smogon-etl"
echo ""
echo "  2. Create the Cloud Run job:"
echo "     gcloud run jobs create smogon-etl \\"
echo "        --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/smogon-etl \\"
echo "        --region ${REGION} \\"
echo "        --service-account ${SERVICE_ACCOUNT} \\"
echo "        --set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},BUCKET_NAME=${BUCKET_NAME},BQ_DATASET=${BQ_DATASET} \\"
echo "        --memory 4Gi --cpu 2 --task-timeout 3600"
echo ""
echo "  3. Execute the job:"
echo "     gcloud run jobs execute smogon-etl --region ${REGION}"
echo ""
