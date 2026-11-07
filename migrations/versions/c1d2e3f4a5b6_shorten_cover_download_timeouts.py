"""Use shorter default timeouts for cover downloads.

Revision ID: c1d2e3f4a5b6
Revises: b5c6d7e8f901
Create Date: 2026-11-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b5c6d7e8f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COVER_SOURCES = (
    "custom_url",
    "amazon",
    "openlibrary",
    "google_books",
    "geobib",
)


def _update_timeout_defaults(old_default: int, new_default: int) -> None:
    settings = sa.table(
        "system_settings",
        *[sa.column(f"cover_{source}_timeout", sa.Integer) for source in _COVER_SOURCES],
    )
    for source in _COVER_SOURCES:
        column = settings.c[f"cover_{source}_timeout"]
        op.execute(
            settings.update().where(column == old_default).values({column.name: new_default})
        )


def _set_server_defaults(default: int) -> None:
    with op.batch_alter_table("system_settings") as batch_op:
        for source in _COVER_SOURCES:
            batch_op.alter_column(
                f"cover_{source}_timeout",
                existing_type=sa.Integer(),
                existing_nullable=False,
                server_default=str(default),
            )


def upgrade() -> None:
    """Lower unchanged default values while retaining custom timeouts."""
    _update_timeout_defaults(10, 2)
    _set_server_defaults(2)


def downgrade() -> None:
    """Restore the former default for values still matching the new default."""
    _update_timeout_defaults(2, 10)
    _set_server_defaults(10)
