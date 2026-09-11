"""add_dewey_colors_enabled_to_system_settings

Revision ID: 8f2a1b9c3d4e
Revises: a8f3c291b547
Create Date: 2026-09-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2a1b9c3d4e'
down_revision: Union[str, None] = 'ec44a2f23c74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'system_settings',
        sa.Column('dewey_colors_enabled', sa.Boolean(), nullable=False, server_default=sa.text('1'))
    )


def downgrade() -> None:
    op.drop_column('system_settings', 'dewey_colors_enabled')
