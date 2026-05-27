# Smogon ETL Cloud Run Job - Runbook

## Overview

This directory contains the Smogon Big Data ETL pipeline refactored for GCP Cloud Run.
The pipeline reads data from Smogon.com and Pokemon Showdown, caches raw files in Cloud Storage,
and loads final analytical data into BigQuery.

## Architecture

```
Smogon.com / Pokemon Showdown
        |
        v
  Cloud Run Job (container)
        |
        ├── Raw data → Cloud Storage (gs://<bucket>/raw/<run_id>/...)
        ├── Staged data → Cloud Storage (gs://<bucket>/staged/<run_id>/...)
        └── Final output → BigQuery (dataset: smogon_etl)
```

## Prerequisites

- GCP project with billing enabled
- Cloud Shell or gcloud SDK installed locally
- Docker (for local testing)

## Required Environment Variables

| Variable | Description | Example |
|---|---|---|
| `PROJECT_ID` | GCP project ID | `my-project` |
| `REGION` | GCP region | `us-central1` |
| `BUCKET_NAME` | Cloud Storage bucket | `smogon-etl-my-project` |
| `BQ_DATASET` | BigQuery dataset name | `smogon_etl` |
| `RUN_ID` | Unique run identifier (auto-generated if empty) | `run_20250101_120000` |

Optional:

| Variable | Description |
|---|---|
| `SMOGON_FORMAT` | Process only this format (e.g., `gen9ou`) |
| `SMOGON_SKIP_DISCOVER` | Set to `true` to skip the discovery step |

## Setup (one-time)

Run the provisioning script from Cloud Shell:

```bash
export PROJECT_ID="your-gcp-project"
bash setup_resources.sh
```

This creates:
- Service account with minimal permissions
- Cloud Storage bucket with uniform bucket-level access
- BigQuery dataset in the chosen region
- IAM role bindings for the service account

## Build & Deploy

### 1. Build and push the container image

```bash
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/smogon-etl
```

### 2. Create the Cloud Run job

```bash
gcloud run jobs create smogon-etl \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/smogon-etl \
    --region ${REGION} \
    --service-account smogon-etl-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},BUCKET_NAME=${BUCKET_NAME},BQ_DATASET=${BQ_DATASET} \
    --memory 4Gi --cpu 2 --task-timeout 3600
```

### 3. Execute the job

```bash
gcloud run jobs execute smogon-etl --region ${REGION}
```

To process a single format:

```bash
gcloud run jobs execute smogon-etl --region ${REGION} \
    --args "--format,gen9ou"
```

To skip the discovery step (if sources are already discovered):

```bash
gcloud run jobs execute smogon-etl --region ${REGION} \
    --args "--skip-discover"
```

## Local Testing

You can run the pipeline locally with simulated GCP credentials:

```bash
# Using Application Default Credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export PROJECT_ID="my-project"
export REGION="us-central1"
export BUCKET_NAME="smogon-etl-my-project"
export BQ_DATASET="smogon_etl"

python main.py --format gen9ou
```

## Validation

After execution, check:

1. **Cloud Logging**: View logs at
   https://console.cloud.google.com/run/jobs/details/${REGION}/smogon-etl/executions

2. **BigQuery**: Query the dataset to verify row counts:
   ```sql
   SELECT table_name, table_rows
   FROM `region-${REGION}`.INFORMATION_SCHEMA.TABLES
   WHERE table_catalog = '${PROJECT_ID}'
     AND table_schema = '${BQ_DATASET}';
   ```

3. **Cloud Storage**: Check archived raw files:
   ```bash
   gsutil ls gs://${BUCKET_NAME}/raw/
   ```

## Cleaning Up

To delete all created resources:

```bash
# Delete the Cloud Run job
gcloud run jobs delete smogon-etl --region ${REGION}

# Delete the bucket and its contents
gsutil rm -r gs://${BUCKET_NAME}

# Delete the BigQuery dataset and all tables
bq rm -r -f ${PROJECT_ID}:${BQ_DATASET}

# Delete the service account
gcloud iam service-accounts delete smogon-etl-sa@${PROJECT_ID}.iam.gserviceaccount.com
```
