"""Add file_records.position — the input order within a job.

Merge combines documents in the order the user drags them into, and that order
was previously implicit in whatever order Postgres happened to return the rows.
Storing it makes the ordering a fact rather than a coincidence.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "file_records",
        sa.Column(
            "position", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )


def downgrade() -> None:
    op.drop_column("file_records", "position")
