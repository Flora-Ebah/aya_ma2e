from io import BytesIO
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def tenant_bucket(tenant_slug: str) -> str:
    return f"tenant-{tenant_slug}"


def ensure_bucket(tenant_slug: str) -> str:
    name = tenant_bucket(tenant_slug)
    try:
        if not _get_client().bucket_exists(name):
            _get_client().make_bucket(name)
    except S3Error:
        pass
    return name


def put_object(tenant_slug: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    bucket = ensure_bucket(tenant_slug)
    stream = BytesIO(data)
    _get_client().put_object(bucket, key, stream, length=len(data), content_type=content_type)
    return f"minio://{bucket}/{key}"


def get_presigned_url(tenant_slug: str, key: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta
    bucket = tenant_bucket(tenant_slug)
    return _get_client().presigned_get_object(bucket, key, expires=timedelta(seconds=expires_seconds))


def get_object_bytes_from_url(url: str) -> tuple[bytes, str]:
    """Récupère un objet depuis MinIO via son URL `minio://bucket/key`.

    Retourne (data_bytes, filename).
    """
    if not url or not url.startswith("minio://"):
        raise ValueError(f"not a minio url: {url!r}")
    rest = url[len("minio://"):]
    bucket, key = rest.split("/", 1)
    response = _get_client().get_object(bucket, key)
    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()
    filename = key.rsplit("/", 1)[-1] if "/" in key else key
    return data, filename


def presigned_from_minio_url(url: str, expires_seconds: int = 3600) -> str | None:
    """Convertit une URL `minio://bucket/key` en URL HTTPS présignée."""
    from datetime import timedelta
    if not url or not url.startswith("minio://"):
        return None
    rest = url[len("minio://"):]
    try:
        bucket, key = rest.split("/", 1)
    except ValueError:
        return None
    try:
        return _get_client().presigned_get_object(bucket, key, expires=timedelta(seconds=expires_seconds))
    except Exception:
        return None
