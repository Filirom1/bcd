"""update_default_medium_types_and_genres

Revision ID: f949aa5e1f79
Revises: 7c12c47084d3
Create Date: 2026-06-22 06:19:30.852077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f949aa5e1f79'
down_revision: Union[str, None] = '7c12c47084d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE system_settings SET catalog_medium_types = 'Livre, Périodique, Audio, Vidéo, Jeu, Numérique, Autre' "
        "WHERE id = 1 AND (catalog_medium_types = 'Livre, Album illustré, Conte, Poème, Périodique, Bande dessinée, Manga, DVD, CD, Autre' OR catalog_medium_types IS NULL)"
    )
    op.execute(
        "UPDATE system_settings SET catalog_genres = 'Album, Roman, Conte, Poésie, Théâtre, Bande dessinée, Manga, Documentaire, Autre' "
        "WHERE id = 1 AND (catalog_genres = 'Aventure, Fantastique, Policier, Science-fiction, Historique, Biographie, Poésie, Théâtre, Autre' OR catalog_genres IS NULL)"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET catalog_medium_types = 'Livre, Album illustré, Conte, Poème, Périodique, Bande dessinée, Manga, DVD, CD, Autre' "
        "WHERE id = 1 AND catalog_medium_types = 'Livre, Périodique, Audio, Vidéo, Jeu, Numérique, Autre'"
    )
    op.execute(
        "UPDATE system_settings SET catalog_genres = 'Aventure, Fantastique, Policier, Science-fiction, Historique, Biographie, Poésie, Théâtre, Autre' "
        "WHERE id = 1 AND catalog_genres = 'Album, Roman, Conte, Poésie, Théâtre, Bande dessinée, Manga, Documentaire, Autre'"
    )
