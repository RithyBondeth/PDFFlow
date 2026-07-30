"""Time helpers.

All timestamps in PDFFlow are UTC-aware. Postgres `TIMESTAMPTZ` returns them
that way, but not every driver does (SQLite, used by the test suite, drops the
offset), so comparisons go through :func:`ensure_utc` rather than assuming.
"""

from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Attach UTC to a naive datetime; leave aware ones untouched."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
