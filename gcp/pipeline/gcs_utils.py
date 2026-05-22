import logging
import gzip
import json
from google.cloud import storage
from google.cloud.exceptions import NotFound

from . import config

logger = logging.getLogger(__name__)

_client = None


def get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=config.PROJECT_ID)
    return _client


def get_bucket() -> storage.Bucket:
    return get_client().bucket(config.RAW_BUCKET)


def blob_path(source_type: str, month: str, filename: str) -> str:
    return f"{source_type}/{month}/{filename}"


def upload_string(
    content: str,
    source_type: str,
    month: str,
    filename: str,
    compress: bool = False,
) -> str:
    bucket = get_bucket()
    path = blob_path(source_type, month, filename)
    blob = bucket.blob(path)
    if compress:
        blob.upload_from_string(gzip.compress(content.encode("utf-8")))
        blob.content_encoding = "gzip"
    else:
        blob.upload_from_string(content, content_type="text/plain")
    logger.debug("Uploaded gs://%s/%s", config.RAW_BUCKET, path)
    return f"gs://{config.RAW_BUCKET}/{path}"


def download_string(
    source_type: str,
    month: str,
    filename: str,
) -> str:
    bucket = get_bucket()
    path = blob_path(source_type, month, filename)
    blob = bucket.blob(path)
    if not blob.exists():
        return None
    raw = blob.download_as_bytes()
    if filename.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def blob_exists(source_type: str, month: str, filename: str) -> bool:
    bucket = get_bucket()
    path = blob_path(source_type, month, filename)
    return bucket.blob(path).exists()


def upload_json(
    data: dict,
    source_type: str,
    month: str,
    filename: str,
) -> str:
    content = json.dumps(data)
    return upload_string(content, source_type, month, filename)


def download_json(
    source_type: str,
    month: str,
    filename: str,
) -> dict:
    content = download_string(source_type, month, filename)
    if content is None:
        return None
    return json.loads(content)
