"""add optional generic external ID to borrowers

Revision ID: b7e2f4a1c9d0
Revises: 8f2a1b9c3d4e
Create Date: 2026-09-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2f4a1c9d0"
down_revision: Union[str, None] = "8f2a1b9c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "borrower",
        sa.Column("external_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_borrower_external_id",
        "borrower",
        ["external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_borrower_external_id", table_name="borrower")
    op.drop_column("borrower", "external_id")
