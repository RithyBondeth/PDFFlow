import redis
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.job import HealthOut
from app.services import events

router = APIRouter(tags=["system"])

VERSION = "0.1.0"


@router.get("/health", response_model=HealthOut, summary="Liveness and dependency check")
def health(response: Response, db: Session = Depends(get_db)) -> HealthOut:
    database = "up"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database = "down"

    cache = "up"
    try:
        events.client().ping()
    except redis.RedisError:
        cache = "down"

    overall = "ok" if database == "up" and cache == "up" else "degraded"
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthOut(status=overall, version=VERSION, database=database, redis=cache)


@router.get("/config", summary="Client-visible limits")
def client_config() -> dict:
    return {
        "maxUploadBytes": settings.max_upload_bytes,
        "maxFilesPerJob": settings.max_files_per_job,
        "fileTtlMinutes": settings.file_ttl_minutes,
    }
