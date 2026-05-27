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
| `BUCKET_NAME` | Cloud Storage bucket (default: `smogon-etl-<project>`) | `smogon-etl-my-project` |
| `BQ_DATASET` | BigQuery dataset name (default: `smogon_etl`) | `smogon_etl` |

Optional:

| Variable | Default | Description |
|---|---|---|
| `IMAGE_NAME` | `gcr.io/${PROJECT_ID}/smogon-etl` | Container image tag |
| `JOB_NAME` | `smogon-etl` | Cloud Run job name |
| `SERVICE_ACCOUNT_NAME` | `smogon-etl-sa` | Service account name |

## One-Command Setup, Deploy & Run

From Cloud Shell, run:

```bash
export PROJECT_ID="your-gcp-project"
bash setup_resources.sh gen9ou
```

This single command does **everything**:
1. Enables required APIs
2. Creates service account, bucket, and BigQuery dataset
3. Grants IAM permissions (least-privilege)
4. Builds and pushes the container image (via Cloud Build)
5. Creates the Cloud Run job
6. Executes the job with `--format gen9ou`

To process all formats instead of a single one, omit the argument:
```bash
bash setup_resources.sh
```

> **Note:** The `setup_resources.sh` script is idempotent — you can re-run it safely.

## Manual Steps (if not using the all-in-one script)

### 1. Provision infrastructure
```bash
# Clone, set vars, and run only the provisioning portion
export PROJECT_ID="your-gcp-project"
bash setup_resources.sh   # will stop at error if PROJECT_ID unset
# Or just run the individual steps manually
```

### 2. Build and push the container image
```bash
gcloud builds submit --tag gcr.io/${PROJECT_ID}/smogon-etl
```

### 3. Create the Cloud Run job
```bash
gcloud run jobs create smogon-etl \
    --image gcr.io/${PROJECT_ID}/smogon-etl \
    --region ${REGION} \
    --service-account smogon-etl-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-env-vars PROJECT_ID=${PROJECT_ID},REGION=${REGION},BUCKET_NAME=${BUCKET_NAME},BQ_DATASET=${BQ_DATASET} \
    --memory 4Gi --cpu 2 --task-timeout 3600
```

### 4. Execute the job
```bash
# Single format
gcloud run jobs execute smogon-etl --region ${REGION} --args "--format,gen9ou"

# Skip discovery (if sources already discovered)
gcloud run jobs execute smogon-etl --region ${REGION} --args "--skip-discover"
```

## Local Testing

You can run the pipeline locally with GCP credentials:

```bash
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
