"""remove_genre_field

Revision ID: 29b4443cafa2
Revises: d1c6bbb24cbd
Create Date: 2026-06-22 16:35:50.596705

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29b4443cafa2'
down_revision: Union[str, None] = 'd1c6bbb24cbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def migrate_rules_to_shelf_location(rules_json_str):
    if not rules_json_str:
        return rules_json_str
    try:
        rules = json.loads(rules_json_str)
        new_rules = []
        genre_to_shelf = {
            "Album": "Albums",
            "Roman": "Romans",
            "Conte": "Contes",
            "Poésie": "Poésie",
            "Théâtre": "Théâtre",
            "Bande dessinée": "Bandes dessinées",
            "Manga": "Mangas",
            "Documentaire": "Documentaires",
            "Périodique": "Périodiques"
        }
        for rule in rules:
            new_rule = {}
            for k, v in rule.items():
                if k == "genre":
                    new_rule["shelf_location"] = genre_to_shelf.get(v, v) if v is not None else None
                else:
                    new_rule[k] = v
            new_rules.append(new_rule)
        return json.dumps(new_rules, ensure_ascii=False)
    except Exception:
        return rules_json_str


def migrate_rules_back_to_genre(rules_json_str):
    if not rules_json_str:
        return rules_json_str
    try:
        rules = json.loads(rules_json_str)
        new_rules = []
        shelf_to_genre = {
            "Albums": "Album",
            "Romans": "Roman",
            "Contes": "Conte",
            "Poésie": "Poésie",
            "Théâtre": "Théâtre",
            "Bandes dessinées": "Bande dessinée",
            "Mangas": "Manga",
            "Documentaires": "Documentaire",
            "Périodiques": "Périodique"
        }
        for rule in rules:
            new_rule = {}
            for k, v in rule.items():
                if k == "shelf_location":
                    new_rule["genre"] = shelf_to_genre.get(v, v) if v is not None else None
                else:
                    new_rule[k] = v
            new_rules.append(new_rule)
        return json.dumps(new_rules, ensure_ascii=False)
    except Exception:
        return rules_json_str


def upgrade() -> None:
    bind = op.get_bind()
    
    # 1. Migrate item.shelf_location from bibliographic_record.genre if empty
    items = bind.execute(sa.text(
        "SELECT item.item_id, bibliographic_record.genre "
        "FROM item JOIN bibliographic_record ON item.bibliographic_record_id = bibliographic_record.id "
        "WHERE item.shelf_location IS NULL OR item.shelf_location = ''"
    )).fetchall()
    
    genre_to_shelf = {
        "Album": "Albums",
        "Roman": "Romans",
        "Conte": "Contes",
        "Poésie": "Poésie",
        "Théâtre": "Théâtre",
        "Bande dessinée": "Bandes dessinées",
        "Manga": "Mangas",
        "Documentaire": "Documentaires",
        "Périodique": "Périodiques"
    }
    
    for item_id, genre in items:
        if genre:
            shelf_location = genre_to_shelf.get(genre, genre)
            bind.execute(
                sa.text("UPDATE item SET shelf_location = :shelf WHERE item_id = :id"),
                {"shelf": shelf_location, "id": item_id}
            )

    # 2. Migrate catalog_call_number_rules in system_settings
    settings = bind.execute(sa.text("SELECT id, catalog_call_number_rules FROM system_settings")).fetchall()
    for setting_id, rules_str in settings:
        if rules_str:
            new_rules_str = migrate_rules_to_shelf_location(rules_str)
            bind.execute(
                sa.text("UPDATE system_settings SET catalog_call_number_rules = :rules WHERE id = :id"),
                {"rules": new_rules_str, "id": setting_id}
            )

    # 3. Drop index and genre column from bibliographic_record, and update index
    with op.batch_alter_table('bibliographic_record', schema=None) as batch_op:
        batch_op.drop_index('ix_bibliographic_record_genre')
        batch_op.drop_index('idx_biblio_category_genre_lang')
        batch_op.drop_column('genre')
        batch_op.create_index('idx_biblio_category_lang', ['category', 'language'], unique=False)

    # 4. Drop catalog_genres column from system_settings
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.drop_column('catalog_genres')


def downgrade() -> None:
    bind = op.get_bind()

    # 1. Add back genre column to bibliographic_record and restore indexes
    with op.batch_alter_table('bibliographic_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('genre', sa.String(length=100), nullable=True))
        batch_op.create_index('ix_bibliographic_record_genre', ['genre'], unique=False)
        batch_op.drop_index('idx_biblio_category_lang')
        batch_op.create_index('idx_biblio_category_genre_lang', ['category', 'genre', 'language'], unique=False)

    # 2. Add back catalog_genres column to system_settings
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('catalog_genres', sa.Text(), nullable=True, default="Album, Roman, Conte, Poésie, Théâtre, Bande dessinée, Manga, Documentaire, Autre"))

    # 3. Re-populate bibliographic_record.genre from first available item.shelf_location
    records = bind.execute(sa.text("SELECT id FROM bibliographic_record")).fetchall()
    shelf_to_genre = {
        "Albums": "Album",
        "Romans": "Roman",
        "Contes": "Conte",
        "Poésie": "Poésie",
        "Théâtre": "Théâtre",
        "Bandes dessinées": "Bande dessinée",
        "Mangas": "Manga",
        "Documentaires": "Documentaire",
        "Périodiques": "Périodique"
    }

    for record_row in records:
        record_id = record_row[0]
        # Find first non-null shelf_location for items under this record
        item_row = bind.execute(
            sa.text("SELECT shelf_location FROM item WHERE bibliographic_record_id = :id AND shelf_location IS NOT NULL AND shelf_location != '' LIMIT 1"),
            {"id": record_id}
        ).fetchone()
        
        if item_row and item_row[0]:
            genre = shelf_to_genre.get(item_row[0], item_row[0])
            bind.execute(
                sa.text("UPDATE bibliographic_record SET genre = :genre WHERE id = :id"),
                {"genre": genre, "id": record_id}
            )

    # 4. Migrate catalog_call_number_rules back in system_settings
    settings = bind.execute(sa.text("SELECT id, catalog_call_number_rules FROM system_settings")).fetchall()
    for setting_id, rules_str in settings:
        if rules_str:
            old_rules_str = migrate_rules_back_to_genre(rules_str)
            bind.execute(
                sa.text("UPDATE system_settings SET catalog_call_number_rules = :rules WHERE id = :id"),
                {"rules": old_rules_str, "id": setting_id}
            )
