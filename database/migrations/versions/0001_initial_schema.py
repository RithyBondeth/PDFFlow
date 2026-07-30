"""Initial schema: jobs and file_records.

Revision ID: 0001
Revises:
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JOB_STATUS = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    "expired",
    name="job_status",
    create_type=False,
)


def upgrade() -> None:
    JOB_STATUS.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("status", JOB_STATUS, nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(64), nullable=True),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_filename", sa.String(255), nullable=True),
        sa.Column("output_filename", sa.String(255), nullable=True),
        sa.Column("output_stored_name", sa.String(255), nullable=True),
        sa.Column("output_size", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_expires_at_status", "jobs", ["expires_at", "status"])

    op.create_table(
        "file_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False, unique=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_file_records_job_id", "file_records", ["job_id"])
    op.create_index(
        "ix_file_records_expires_at", "file_records", ["expires_at", "deleted"]
    )


def downgrade() -> None:
    op.drop_table("file_records")
    op.drop_table("jobs")
    JOB_STATUS.drop(op.get_bind(), checkfirst=True)
