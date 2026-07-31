"""Job event bus backed by Redis pub/sub.

The worker publishes; every API process subscribes on behalf of a connected
browser. Using pub/sub rather than in-process callbacks means the API can be
scaled horizontally without a client losing its progress stream.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

import redis
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

JOB_CREATED = "job_created"
JOB_PROGRESS = "job_progress"
JOB_COMPLETED = "job_completed"
JOB_FAILED = "job_failed"

_client: redis.Redis | None = None


def client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def channel(job_id: Any) -> str:
    return f"pdfflow:job:{job_id}"


def publish(job_id: Any, event: str, payload: dict) -> None:
    """Fire-and-forget. A dropped progress frame must never fail a job."""
    message = json.dumps({"event": event, "data": payload}, default=str)
    try:
        conn = client()
        conn.publish(channel(job_id), message)
        # Replayed to clients that connect after the event, so a fast job that
        # finishes before the browser subscribes is still reported correctly.
        conn.setex(f"{channel(job_id)}:last", 3600, message)
    except redis.RedisError:
        logger.warning("event_publish_failed", extra={"job_id": str(job_id)})


def last_event(job_id: Any) -> dict | None:
    try:
        raw = client().get(f"{channel(job_id)}:last")
    except redis.RedisError:
        return None
    return json.loads(raw) if raw else None


def subscribe(job_id: Any, *, timeout: float = 1.0) -> Iterator[dict | None]:
    """Yield events for a job; yields ``None`` on idle so the caller can send a
    keep-alive comment and notice client disconnects.

    Blocking, for synchronous callers. The API streams over
    :func:`subscribe_async` instead — a blocking subscription there would need
    a thread per connected browser.
    """
    pubsub = client().pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel(job_id))
    try:
        while True:
            message = pubsub.get_message(timeout=timeout)
            if message is None:
                yield None
                continue
            try:
                yield json.loads(message["data"])
            except (ValueError, KeyError):
                continue
    finally:
        pubsub.close()


# --- async side, used by the SSE endpoint ------------------------------
#
# A subscriber needs a connection of its own for as long as it is subscribed,
# so these take a client the caller owns and closes. Creating it per request
# also keeps every connection owned by the event loop that uses it, which a
# module-level client would not guarantee.


def async_client() -> aioredis.Redis:
    """A new async client. The caller is responsible for closing it."""
    return aioredis.Redis.from_url(settings.redis_url, decode_responses=True)


async def last_event_async(conn: aioredis.Redis, job_id: Any) -> dict | None:
    try:
        raw = await conn.get(f"{channel(job_id)}:last")
    except redis.RedisError:
        return None
    return json.loads(raw) if raw else None


async def subscribe_async(
    conn: aioredis.Redis, job_id: Any, *, timeout: float = 1.0
) -> AsyncIterator[dict | None]:
    """Async twin of :func:`subscribe`, yielding ``None`` on idle.

    Idling here parks a coroutine rather than a thread, so the number of
    browsers watching progress is not bounded by an executor's worker count.
    """
    pubsub = conn.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(channel(job_id))
    try:
        while True:
            message = await pubsub.get_message(timeout=timeout)
            if message is None:
                yield None
                continue
            try:
                yield json.loads(message["data"])
            except (ValueError, KeyError):
                continue
    finally:
        await pubsub.aclose()
