"""Use shorter default timeouts for external catalog sources.

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-11-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Shorten only values that still match the previous defaults."""
    settings = sa.table(
        "system_settings",
        sa.column("bnf_timeout", sa.Integer),
        sa.column("google_books_timeout", sa.Integer),
        sa.column("sudoc_timeout", sa.Integer),
    )
    op.execute(settings.update().where(settings.c.bnf_timeout == 4).values(bnf_timeout=2))
    op.execute(
        settings.update().where(settings.c.google_books_timeout == 4).values(google_books_timeout=2)
    )
    op.execute(settings.update().where(settings.c.sudoc_timeout == 5).values(sudoc_timeout=3))


def downgrade() -> None:
    """Restore previous defaults for values that still match the new defaults."""
    settings = sa.table(
        "system_settings",
        sa.column("bnf_timeout", sa.Integer),
        sa.column("google_books_timeout", sa.Integer),
        sa.column("sudoc_timeout", sa.Integer),
    )
    op.execute(settings.update().where(settings.c.bnf_timeout == 2).values(bnf_timeout=4))
    op.execute(
        settings.update().where(settings.c.google_books_timeout == 2).values(google_books_timeout=4)
    )
    op.execute(settings.update().where(settings.c.sudoc_timeout == 3).values(sudoc_timeout=5))
