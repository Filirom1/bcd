"""remove_denormalized_counters

Revision ID: 3673281a2377
Revises: 2162d1ab9dfc
Create Date: 2026-05-27 07:16:23.776444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3673281a2377'
down_revision: Union[str, None] = '2162d1ab9dfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('bibliographic_record', 'total_circulations')
    op.drop_column('bibliographic_record', 'last_borrowed_at')
    op.drop_column('class', 'student_count')
    op.drop_column('item', 'circulation_count')


def downgrade() -> None:
    op.add_column('item', sa.Column('circulation_count', sa.INTEGER(), nullable=False, server_default=sa.text("'0'")))
    op.add_column('class', sa.Column('student_count', sa.INTEGER(), nullable=False, server_default=sa.text("'0'")))
    op.add_column('bibliographic_record', sa.Column('last_borrowed_at', sa.DATETIME(), nullable=True))
    op.add_column('bibliographic_record', sa.Column('total_circulations', sa.INTEGER(), nullable=False, server_default=sa.text("'0'")))
