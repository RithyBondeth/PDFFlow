"""Application settings, loaded from the environment.

Everything that differs between local / docker / production lives here so that
no module has to reach for ``os.environ`` directly.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- app -------------------------------------------------------------
    app_name: str = "PDFFlow"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    api_prefix: str = "/api"

    # --- datastores ------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://pdfflow:pdfflow@localhost:5432/pdfflow"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    # --- storage ---------------------------------------------------------
    storage_root: Path = Field(default=Path("/data/storage"))
    max_upload_bytes: int = Field(default=100 * 1024 * 1024)  # 100 MB
    max_files_per_job: int = Field(default=25)
    file_ttl_minutes: int = Field(default=30)
    cleanup_interval_seconds: int = Field(default=300)  # every 5 minutes

    @property
    def upload_dir(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.storage_root / "processed"

    # --- security --------------------------------------------------------
    # NoDecode stops pydantic-settings from trying to JSON-parse the raw env
    # value before validation. Without it, a plain comma-separated list —
    # which is what .env.example and docker-compose supply — raises at import
    # time, taking down the API, worker and beat before they start.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000"]
    )
    rate_limit_uploads: str = Field(default="30/minute")
    rate_limit_jobs: str = Field(default="60/minute")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def ensure_directories(self) -> None:
        for directory in (self.upload_dir, self.processed_dir):
            directory.mkdir(parents=True, exist_ok=True)
            directory.chmod(0o700)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
