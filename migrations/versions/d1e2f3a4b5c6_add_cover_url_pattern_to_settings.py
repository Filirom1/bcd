"""Store the custom cover URL pattern in system settings.

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-11-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the optional database-managed URL pattern."""
    op.add_column(
        "system_settings",
        sa.Column("cover_image_url_pattern", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove the database-managed URL pattern."""
    op.drop_column("system_settings", "cover_image_url_pattern")
