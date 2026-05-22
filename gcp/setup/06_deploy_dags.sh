#!/usr/bin/env bash
# =============================================================================
# 06_deploy_dags.sh — Deploy DAGs and pipeline code to Cloud Composer
# =============================================================================
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-us-central1}"
COMPOSER_ENV="${3:-smogon-composer-env}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project-id> [region] [env-name]"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DAGS_SRC="$REPO_ROOT/gcp/dags"
PIPELINE_SRC="$REPO_ROOT/gcp/pipeline"
REQUIREMENTS_SRC="$REPO_ROOT/gcp/requirements-composer.txt"

echo "=== Deploying DAGs and pipeline code to Composer ==="

# Upload DAG files
echo "  Uploading DAGs ..."
gcloud composer environments storage dags import \
  --environment="$COMPOSER_ENV" --location="$REGION" \
  --source="$DAGS_SRC/" \
  --project="$PROJECT_ID"

# Upload pipeline modules (placed in a subfolder that DAGs can import)
echo "  Uploading pipeline modules ..."
python_plugins_dest="gs://$(gcloud composer environments describe "$COMPOSER_ENV" \
  --location="$REGION" --format="value(config.dagGcsPrefix)" --project="$PROJECT_ID")/plugins/pipeline/"

gsutil -m rsync -r "$PIPELINE_SRC/" "$python_plugins_dest"

# Upload custom PyPI requirements
echo "  Installing custom requirements ..."
gcloud composer environments update "$COMPOSER_ENV" \
  --location="$REGION" \
  --update-pypi-packages-from-file="$REQUIREMENTS_SRC" \
  --project="$PROJECT_ID"

echo "=== Deployment complete ==="
