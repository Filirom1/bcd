"""Add a configurable delay between bulk cover downloads.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-11-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the delay setting with the existing 60-second default."""
    with op.batch_alter_table("system_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "cover_download_delay_seconds",
                sa.Integer(),
                nullable=False,
                server_default="60",
            )
        )
        batch_op.create_check_constraint(
            "check_cover_download_delay",
            "cover_download_delay_seconds BETWEEN 0 AND 300",
        )


def downgrade() -> None:
    """Remove the bulk cover download delay setting."""
    with op.batch_alter_table("system_settings") as batch_op:
        batch_op.drop_constraint("check_cover_download_delay", type_="check")
        batch_op.drop_column("cover_download_delay_seconds")
