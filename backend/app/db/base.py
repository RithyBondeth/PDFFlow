"""Declarative base.

Deliberately imports nothing from ``app.models`` — models import *this*, so a
back-import here would be circular. Anything that needs the full metadata
(Alembic, ``create_all`` in tests) imports ``app.models`` instead, which
registers every table.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def default_expiry() -> datetime:
    """Shared TTL default for jobs and their files."""
    return datetime.now(UTC) + timedelta(minutes=settings.file_ttl_minutes)
