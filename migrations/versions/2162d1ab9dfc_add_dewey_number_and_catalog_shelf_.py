"""add_dewey_number_and_catalog_shelf_locations

Revision ID: 2162d1ab9dfc
Revises: 514a09aea333
Create Date: 2026-04-22 09:16:58.944053

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2162d1ab9dfc'
down_revision: Union[str, None] = '514a09aea333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SHELF_LOCATIONS = json.dumps([
    {"label": "Romans",           "color": "#c0392b"},
    {"label": "Albums",           "color": "#e67e22"},
    {"label": "Bandes dessinées", "color": "#2980b9"},
    {"label": "Documentaires",    "color": "#27ae60"},
    {"label": "Périodiques",      "color": "#16a085"},
    {"label": "Contes",           "color": "#f39c12"},
    {"label": "Poésie",           "color": "#8e44ad"},
])


def upgrade() -> None:
    op.add_column('bibliographic_record',
        sa.Column('dewey_number', sa.Text(), nullable=True))
    op.add_column('system_settings',
        sa.Column('catalog_shelf_locations', sa.Text(), nullable=True,
                  server_default=DEFAULT_SHELF_LOCATIONS))


def downgrade() -> None:
    op.drop_column('bibliographic_record', 'dewey_number')
    op.drop_column('system_settings', 'catalog_shelf_locations')
