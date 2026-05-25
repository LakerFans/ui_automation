from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ui-agent-test-platform"
    artifacts_dir: Path = Path("artifacts")
    registry_dir: Path = Path("data/registry")
    agent_browser_bin: str = "agent-browser"
    browser_backend: Literal["agent-browser", "mock"] = "mock"
    allowed_url_patterns: str = "https://*,http://localhost*,http://127.0.0.1*"
    max_retries: int = 3
    confidence_threshold: float = 0.85
    clarify_threshold: float = 0.60
    max_clarify_attempts: int = 2
    command_timeout_sec: int = 60

    # Phase 1
    postgres_uri: str = "postgresql://ui_test:ui_test@localhost:5432/ui_test"
    use_postgres_checkpointer: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ui-test-artifacts"
    minio_secure: bool = False
    use_minio: bool = False
    require_risk_confirmation: bool = True


settings = Settings()
settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
