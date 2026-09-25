"""Add configurable external catalog source settings.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source switches and bounded timeout values."""
    op.add_column(
        "system_settings",
        sa.Column("bnf_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "system_settings",
        sa.Column("bnf_timeout", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "system_settings",
        sa.Column("google_books_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "system_settings",
        sa.Column("google_books_timeout", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "system_settings",
        sa.Column("sudoc_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "system_settings",
        sa.Column("sudoc_timeout", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    """Remove source settings in reverse order."""
    op.drop_column("system_settings", "sudoc_timeout")
    op.drop_column("system_settings", "sudoc_enabled")
    op.drop_column("system_settings", "google_books_timeout")
    op.drop_column("system_settings", "google_books_enabled")
    op.drop_column("system_settings", "bnf_timeout")
    op.drop_column("system_settings", "bnf_enabled")
