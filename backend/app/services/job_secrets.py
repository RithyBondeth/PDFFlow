"""Read-once, short-lived hand-off of job secrets from the API to the worker.

Document passwords for Protect and Unlock cannot go where the rest of a job's
options go. ``jobs.options`` is a durable Postgres column, the Celery message
can be inspected and redelivered, and both outlive the job. A password should
exist only for as long as it takes the worker to use it once.

So the API splits secret options off before the job row is written and puts
them in Redis under the job id with a TTL. The worker reads them with GETDEL,
which removes them in the same step. If the job never runs, the TTL removes
them anyway. The bundled Compose Redis runs with persistence disabled, so the
value never touches disk there; see docs/security.md for managed Redis.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol, cast

import redis

from app.core.config import settings
from app.core.errors import PDFFlowError
from app.services import events

logger = logging.getLogger(__name__)

# Option names that must never be persisted, logged or returned.
SECRET_OPTION_KEYS = frozenset({"password"})


class _Store(Protocol):
    def setex(self, name: str, time: int, value: str) -> Any: ...
    def getdel(self, name: str) -> Any: ...
    def delete(self, *names: str) -> Any: ...


class SecretUnavailableError(PDFFlowError):
    status_code = 503
    code = "service_unavailable"


def _store() -> _Store:
    return cast(_Store, events.client())


def _key(job_id: Any) -> str:
    return f"pdfflow:job:{job_id}:secrets"


def split(options: dict) -> tuple[dict, dict]:
    """Return (options safe to persist, secret options)."""
    public = {k: v for k, v in options.items() if k not in SECRET_OPTION_KEYS}
    secret = {k: v for k, v in options.items() if k in SECRET_OPTION_KEYS}
    return public, secret


def stash(job_id: Any, secret: dict) -> None:
    if not secret:
        return
    try:
        _store().setex(
            _key(job_id), settings.file_ttl_minutes * 60, json.dumps(secret)
        )
    except redis.RedisError as exc:
        # Without the hand-off the job could only fail later, so refuse now.
        logger.warning("job_secret_stash_failed", extra={"job_id": str(job_id)})
        raise SecretUnavailableError(
            "This tool is temporarily unavailable. Please try again shortly."
        ) from exc


def take(job_id: Any) -> dict:
    """Fetch and delete in one step. Returns {} if nothing is (still) there."""
    try:
        raw = _store().getdel(_key(job_id))
    except redis.RedisError:
        logger.warning("job_secret_take_failed", extra={"job_id": str(job_id)})
        return {}
    if not raw:
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def discard(job_id: Any) -> None:
    try:
        _store().delete(_key(job_id))
    except redis.RedisError:
        logger.warning("job_secret_discard_failed", extra={"job_id": str(job_id)})
