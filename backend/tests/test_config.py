"""Settings are loaded from the environment in every real deployment, so the
env path needs its own tests — validating only the in-process defaults once let
a startup-breaking bug reach a running container."""

import pytest

from app.core.config import Settings


def test_cors_origins_accepts_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch):
    """The form .env.example and docker-compose actually supply."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:3000")

    assert Settings().cors_origins == [
        "http://localhost:8080",
        "http://localhost:3000",
    ]


def test_cors_origins_tolerates_padding_and_trailing_commas(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CORS_ORIGINS", " http://a , http://b ,")

    assert Settings().cors_origins == ["http://a", "http://b"]


def test_cors_origins_accepts_a_single_value(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://pdfflow.app")

    assert Settings().cors_origins == ["https://pdfflow.app"]


def test_cors_origins_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert Settings().cors_origins == ["http://localhost:3000"]


def test_numeric_and_path_settings_load_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "52428800")
    monkeypatch.setenv("FILE_TTL_MINUTES", "15")
    monkeypatch.setenv("STORAGE_ROOT", "/data/storage")

    settings = Settings()

    assert settings.max_upload_bytes == 52428800
    assert settings.file_ttl_minutes == 15
    assert settings.upload_dir.as_posix() == "/data/storage/uploads"
    assert settings.processed_dir.as_posix() == "/data/storage/processed"


def test_env_example_values_all_load(monkeypatch: pytest.MonkeyPatch):
    """Every value shipped in .env.example must produce a usable Settings —
    this is the exact combination `docker compose up` feeds the containers."""
    for key, value in {
        "ENVIRONMENT": "development",
        "DEBUG": "false",
        "MAX_UPLOAD_BYTES": "104857600",
        "MAX_FILES_PER_JOB": "25",
        "FILE_TTL_MINUTES": "30",
        "CLEANUP_INTERVAL_SECONDS": "300",
        "CORS_ORIGINS": "http://localhost:8080,http://localhost:3000",
        "RATE_LIMIT_UPLOADS": "30/minute",
        "RATE_LIMIT_JOBS": "60/minute",
        "DATABASE_URL": "postgresql+psycopg://pdfflow:pdfflow@postgres:5432/pdfflow",
        "REDIS_URL": "redis://redis:6379/0",
        "STORAGE_ROOT": "/data/storage",
    }.items():
        monkeypatch.setenv(key, value)

    settings = Settings()

    assert settings.celery_broker_url == "redis://redis:6379/0"
    assert settings.max_files_per_job == 25
    assert len(settings.cors_origins) == 2
