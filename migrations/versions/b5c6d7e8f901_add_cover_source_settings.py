"""Add configurable cover provider settings.

Revision ID: b5c6d7e8f901
Revises: a1b2c3d4e5f6
Create Date: 2026-11-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f901"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COVER_SOURCES = (
    "custom_url",
    "amazon",
    "openlibrary",
    "google_books",
    "geobib",
)


def upgrade() -> None:
    """Add per-provider switches and bounded download timeouts."""
    with op.batch_alter_table("system_settings") as batch_op:
        for source in _COVER_SOURCES:
            batch_op.add_column(
                sa.Column(
                    f"cover_{source}_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
            batch_op.add_column(
                sa.Column(
                    f"cover_{source}_timeout",
                    sa.Integer(),
                    nullable=False,
                    server_default="2",
                )
            )
        batch_op.create_check_constraint(
            "check_cover_source_timeouts",
            "cover_custom_url_timeout BETWEEN 1 AND 60 AND "
            "cover_amazon_timeout BETWEEN 1 AND 60 AND "
            "cover_openlibrary_timeout BETWEEN 1 AND 60 AND "
            "cover_google_books_timeout BETWEEN 1 AND 60 AND "
            "cover_geobib_timeout BETWEEN 1 AND 60",
        )


def downgrade() -> None:
    """Remove cover provider settings in reverse order."""
    with op.batch_alter_table("system_settings") as batch_op:
        batch_op.drop_constraint("check_cover_source_timeouts", type_="check")
        for source in reversed(_COVER_SOURCES):
            batch_op.drop_column(f"cover_{source}_timeout")
            batch_op.drop_column(f"cover_{source}_enabled")
