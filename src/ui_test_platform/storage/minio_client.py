from __future__ import annotations

from pathlib import Path

from ui_test_platform.config import settings


class ArtifactStore:
    """Local filesystem store with optional MinIO upload."""

    def __init__(self) -> None:
        self.use_minio = settings.use_minio
        self._client = None
        if self.use_minio:
            self._init_minio()

    def _init_minio(self) -> None:
        from minio import Minio

        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        if not self._client.bucket_exists(settings.minio_bucket):
            self._client.make_bucket(settings.minio_bucket)

    def upload_file(self, run_id: str, step_id: str, local_path: Path, tenant: str = "default") -> str:
        key = f"{tenant}/{run_id}/{step_id}.png"
        if self.use_minio and self._client and local_path.exists():
            self._client.fput_object(settings.minio_bucket, key, str(local_path))
            return f"s3://{settings.minio_bucket}/{key}"
        return str(local_path)
