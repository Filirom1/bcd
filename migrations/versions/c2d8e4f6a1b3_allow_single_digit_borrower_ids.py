"""allow single-digit reusable borrower IDs

Revision ID: c2d8e4f6a1b3
Revises: b7e2f4a1c9d0
Create Date: 2026-09-14

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c2d8e4f6a1b3"
down_revision: Union[str, None] = "b7e2f4a1c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE system_settings SET id_validation_regex = '^\\d{1,6}$' "
        "WHERE id = 1"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET id_validation_regex = '^\\d{3,6}$' "
        "WHERE id = 1"
    )
