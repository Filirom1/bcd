"""Tests for the shorter cover download timeout defaults migration."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "c1d2e3f4a5b6_shorten_cover_download_timeouts.py"
)
_SPEC = importlib.util.spec_from_file_location("shorten_cover_timeout_migration", _MIGRATION_PATH)
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)


def test_upgrade_shortens_defaults_without_changing_custom_timeouts():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE system_settings ("
                "id INTEGER PRIMARY KEY, "
                "cover_custom_url_timeout INTEGER NOT NULL DEFAULT 10, "
                "cover_amazon_timeout INTEGER NOT NULL DEFAULT 10, "
                "cover_openlibrary_timeout INTEGER NOT NULL DEFAULT 10, "
                "cover_google_books_timeout INTEGER NOT NULL DEFAULT 10, "
                "cover_geobib_timeout INTEGER NOT NULL DEFAULT 10)"
            )
        )
        connection.execute(text("INSERT INTO system_settings VALUES " "(1, 10, 7, 10, 2, 10)"))

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            _MIGRATION.upgrade()

        row = connection.execute(
            text(
                "SELECT cover_custom_url_timeout, cover_amazon_timeout, "
                "cover_openlibrary_timeout, cover_google_books_timeout, "
                "cover_geobib_timeout FROM system_settings WHERE id = 1"
            )
        ).one()
        connection.execute(text("INSERT INTO system_settings (id) VALUES (2)"))
        defaults = connection.execute(
            text(
                "SELECT cover_custom_url_timeout, cover_amazon_timeout, "
                "cover_openlibrary_timeout, cover_google_books_timeout, "
                "cover_geobib_timeout FROM system_settings WHERE id = 2"
            )
        ).one()

    assert row == (2, 7, 2, 2, 2)
    assert defaults == (2, 2, 2, 2, 2)
    engine.dispose()
