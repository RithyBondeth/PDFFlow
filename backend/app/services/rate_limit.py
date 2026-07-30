"""Rate limiting.

With no accounts there is no identity to key on, so limits are per client IP
(taken from the trusted proxy header that nginx sets). Counters live in Redis
so several API replicas share one budget.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # nginx appends the real peer last; take the first entry it set.
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_key,
    storage_uri=settings.redis_url,
    headers_enabled=True,
)
