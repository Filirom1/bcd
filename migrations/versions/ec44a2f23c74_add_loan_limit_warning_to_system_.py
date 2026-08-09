"""add loan_limit_warning to system_settings

Revision ID: ec44a2f23c74
Revises: 29b4443cafa2
Create Date: 2026-07-06 08:20:20.803838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec44a2f23c74'
down_revision: Union[str, None] = '29b4443cafa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'system_settings',
        sa.Column('loan_limit_warning', sa.Integer(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    op.drop_column('system_settings', 'loan_limit_warning')
