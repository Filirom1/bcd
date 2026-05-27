"""Add dewey_colors to system_settings

Revision ID: 514a09aea333
Revises: 46877dbfbe26
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '514a09aea333'
down_revision: Union[str, None] = '46877dbfbe26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_DEWEY_COLORS = '["#000000","#9e6633","#f20000","#ff9813","#ffee00","#409d42","#0fafe9","#98238b","#d3d5d4","#ffffff"]'


def upgrade() -> None:
    op.add_column(
        'system_settings',
        sa.Column('dewey_colors', sa.Text(), nullable=True, server_default=DEFAULT_DEWEY_COLORS)
    )


def downgrade() -> None:
    op.drop_column('system_settings', 'dewey_colors')
