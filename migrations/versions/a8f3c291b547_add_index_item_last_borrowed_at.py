"""add_index_item_last_borrowed_at

Revision ID: a8f3c291b547
Revises: 3673281a2377
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a8f3c291b547'
down_revision: Union[str, None] = '3673281a2377'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_item_last_borrowed_at', 'item', ['last_borrowed_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_item_last_borrowed_at', table_name='item')
