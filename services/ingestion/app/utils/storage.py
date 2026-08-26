"""MinIO Object Storage - Durable S3-compatible store for uploaded documents.

If the `minio` package is unavailable (image not yet rebuilt), the module
degrades gracefully: uploads continue without the object-store copy and a
warning is logged.
"""
try:
    from minio import Minio
    MINIO_AVAILABLE = True
except ImportError:
    Minio = None
    MINIO_AVAILABLE = False

from app.core.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
)

_client: Minio = None


def get_client():
    """Get the global MinIO client (or None if unavailable)."""
    global _client
    if not MINIO_AVAILABLE:
        print("WARNING: 'minio' package not installed — object storage disabled")
        return None
    if _client is None:
        print(f"Connecting to MinIO at {MINIO_ENDPOINT}")
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
    return _client


def ensure_bucket():
    """Create the uploads bucket if it does not exist."""
    client = get_client()
    if client is None:
        return
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        print(f"MinIO bucket '{MINIO_BUCKET}' created")
    else:
        print(f"MinIO bucket '{MINIO_BUCKET}' already exists")


def upload_document(local_path: str, object_name: str) -> str:
    """Upload a file to MinIO. Returns an S3-style object key.

    Returns None if object storage is unavailable (local copy still saved).
    """
    client = get_client()
    if client is None:
        return None
    ensure_bucket()
    client.fput_object(MINIO_BUCKET, object_name, local_path)
    object_key = f"{MINIO_BUCKET}/{object_name}"
    print(f"Uploaded '{object_name}' to MinIO ({object_key})")
    return object_key


def get_object_url(object_key: str) -> str:
    """Return a presigned GET URL (valid 1 hour) for an object key."""
    try:
        client = get_client()
        if client is None:
            return object_key
        bucket, name = object_key.split("/", 1)
        return client.presigned_get_object(bucket, name)
    except Exception as e:
        print(f"Could not build presigned URL: {e}")
        return object_key