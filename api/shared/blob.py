"""Blob storage helpers: SAS issuance, quarantine download/delete, promotion
to the permanent labels container, and read-SAS for the agent UI."""

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, unquote

from azure.storage.blob import (
    BlobClient,
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)

QUARANTINE = os.environ.get("AZURE_STORAGE_CONTAINER_QUARANTINE", "quarantine")
LABELS = os.environ.get("AZURE_STORAGE_CONTAINER_LABELS", "labels")

UPLOAD_SAS_MINUTES = 5
READ_SAS_MINUTES = 60


def _conn_str() -> str:
    return os.environ["AZURE_STORAGE_CONNECTION_STRING"]


def _service() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(_conn_str())


def _account_parts():
    svc = _service()
    return svc.account_name, svc.credential.account_key


def sanitize_filename(name: str) -> str:
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return base[:120] or "image"


def make_upload_sas(filename: str, content_type: str, side: str) -> dict:
    """Write-only SAS for one image into quarantine. Returns upload_url (with
    SAS) and blob_url (without) — blob_url is what gets sent to /api/submit."""
    svc = _service()
    blob_name = f"{side}-{uuid.uuid4()}-{sanitize_filename(filename)}"
    account_name, account_key = svc.account_name, svc.credential.account_key
    sas = generate_blob_sas(
        account_name=account_name,
        container_name=QUARANTINE,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=UPLOAD_SAS_MINUTES),
        content_type=content_type,
    )
    blob_url = f"https://{account_name}.blob.core.windows.net/{QUARANTINE}/{blob_name}"
    return {"upload_url": f"{blob_url}?{sas}", "blob_url": blob_url}


def parse_blob_url(blob_url: str):
    """Validate the URL points at OUR storage account and return
    (container, blob_name). Raises ValueError otherwise (basic SSRF guard)."""
    svc = _service()
    parsed = urlparse(blob_url)
    expected_host = f"{svc.account_name}.blob.core.windows.net"
    if parsed.hostname != expected_host:
        raise ValueError("blob URL does not belong to this system")
    parts = unquote(parsed.path).lstrip("/").split("/", 1)
    if len(parts) != 2 or not parts[1]:
        raise ValueError("malformed blob URL")
    return parts[0], parts[1]


def download_quarantine_blob(blob_url: str) -> bytes:
    container, name = parse_blob_url(blob_url)
    if container != QUARANTINE:
        raise ValueError("blob is not in the quarantine container")
    client = _service().get_blob_client(container, name)
    return client.download_blob(max_concurrency=1).readall()


def delete_blob_quiet(blob_url: str) -> None:
    try:
        container, name = parse_blob_url(blob_url)
        _service().get_blob_client(container, name).delete_blob()
    except Exception:
        pass  # lifecycle policy is the backstop


def promote_to_labels(blob_url: str, data: bytes) -> str:
    """Upload the (already downloaded + quality-checked) bytes to the labels
    container and delete the quarantine original. Returns the permanent URL."""
    _, name = parse_blob_url(blob_url)
    svc = _service()
    dest = svc.get_blob_client(LABELS, name)
    dest.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type="image/jpeg"),
    )
    delete_blob_quiet(blob_url)
    return f"https://{svc.account_name}.blob.core.windows.net/{LABELS}/{name}"


def make_read_sas(blob_url: str) -> str | None:
    """Short-lived read URL so the agent UI can render private blobs."""
    try:
        container, name = parse_blob_url(blob_url)
    except ValueError:
        return None
    svc = _service()
    sas = generate_blob_sas(
        account_name=svc.account_name,
        container_name=container,
        blob_name=name,
        account_key=svc.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=READ_SAS_MINUTES),
    )
    return f"{blob_url}?{sas}"
