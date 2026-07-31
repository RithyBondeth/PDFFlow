from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, default_expiry

if TYPE_CHECKING:
    from app.models.job import Job


class FileRecord(Base):
    """A file that currently exists on disk under storage/uploads.

    ``stored_name`` is always ``<uuid>.<ext>`` — the original name is kept only
    so the download can be given a friendly filename.
    """

    __tablename__ = "file_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    # Where this file sits in its job's input order — set from the order the
    # client sent the ids in. Tools that combine documents (merge) depend on
    # it, so it has to be persisted rather than inferred from row order.
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=default_expiry
    )

    job: Mapped[Job | None] = relationship(back_populates="files")

    __table_args__ = (Index("ix_file_records_expires_at", "expires_at", "deleted"),)
