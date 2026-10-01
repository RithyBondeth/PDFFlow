"""Add file_records.encrypted — whether an uploaded PDF is password protected.

Uploads used to reject encrypted PDFs outright, which left Unlock PDF with no
way to receive its input. They are now accepted and flagged, and the flag is
what keeps them away from every tool except Unlock.

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "file_records",
        sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("file_records", "encrypted")
