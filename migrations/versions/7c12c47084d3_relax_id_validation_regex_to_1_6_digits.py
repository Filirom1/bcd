"""relax_id_validation_regex_to_1_6_digits

Revision ID: 7c12c47084d3
Revises: a8f3c291b547
Create Date: 2026-06-17 20:43:46.621012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c12c47084d3'
down_revision: Union[str, None] = 'a8f3c291b547'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE system_settings SET id_validation_regex = '^\\d{1,6}$' "
        "WHERE id = 1 AND id_validation_regex != '^\\d{1,6}$'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET id_validation_regex = '^\\d{3,6}$' "
        "WHERE id = 1 AND id_validation_regex = '^\\d{1,6}$'"
    )
