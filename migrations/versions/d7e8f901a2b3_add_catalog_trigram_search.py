"""Add an accent-insensitive trigram index for catalogue search.

Revision ID: d7e8f901a2b3
Revises: e2f3a4b5c6d7
Create Date: 2026-11-11

"""

from typing import Sequence, Union

from alembic import op

from src.bcd_api.core.catalog_search import (
    create_catalog_search_index,
    drop_catalog_search_index,
)

revision: str = "d7e8f901a2b3"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the SQLite FTS5 index."""
    create_catalog_search_index(op.get_bind())


def downgrade() -> None:
    """Remove the FTS5 index."""
    drop_catalog_search_index(op.get_bind())
