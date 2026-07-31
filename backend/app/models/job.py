from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import ensure_utc
from app.core.time import now as utc_now
from app.db.base import Base, default_expiry

# JSONB on Postgres; plain JSON elsewhere so the suite can run on SQLite.
JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    expired = "expired"

    @property
    def is_terminal(self) -> bool:
        return self in {JobStatus.completed, JobStatus.failed, JobStatus.expired}


class Job(Base):
    """One user-requested operation on one or more temporary files."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=True),
        nullable=False,
        default=JobStatus.pending,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Operation-specific parameters (page ranges, watermark text, ...).
    options: Mapped[dict] = mapped_column(JsonColumn, nullable=False, default=dict)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Display names only — never used to build a filesystem path.
    input_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # UUID-based name inside storage/processed. Never leaves the server.
    output_stored_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=default_expiry
    )

    # order_by is load-bearing, not cosmetic: the worker feeds `files` straight
    # into the operation handler, so for merge this *is* the page order the
    # user dragged into place. Without it the database is free to return the
    # rows however it likes.
    files: Mapped[list[FileRecord]] = relationship(  # noqa: F821
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="FileRecord.position",
    )

    __table_args__ = (Index("ix_jobs_expires_at_status", "expires_at", "status"),)

    @property
    def is_expired(self) -> bool:
        return utc_now() >= ensure_utc(self.expires_at)
