"""add_catalog_call_number_rules

Revision ID: d1c6bbb24cbd
Revises: f949aa5e1f79
Create Date: 2026-06-22 06:56:23.875340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1c6bbb24cbd'
down_revision: Union[str, None] = 'f949aa5e1f79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('system_settings', sa.Column('catalog_call_number_rules', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('system_settings', 'catalog_call_number_rules')
