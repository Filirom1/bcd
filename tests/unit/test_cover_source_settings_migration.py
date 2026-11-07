"""Tests for configurable cover provider settings migration."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "b5c6d7e8f901_add_cover_source_settings.py"
)
_SPEC = importlib.util.spec_from_file_location("cover_source_settings_migration", _MIGRATION_PATH)
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)


def test_upgrade_adds_enabled_sources_with_ten_second_defaults():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE system_settings (id INTEGER PRIMARY KEY, library_name TEXT)")
        )
        connection.execute(
            text("INSERT INTO system_settings (id, library_name) VALUES (1, 'Test')")
        )

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            _MIGRATION.upgrade()

        row = connection.execute(
            text(
                "SELECT cover_custom_url_enabled, cover_custom_url_timeout, "
                "cover_amazon_enabled, cover_amazon_timeout, "
                "cover_openlibrary_enabled, cover_openlibrary_timeout, "
                "cover_google_books_enabled, cover_google_books_timeout, "
                "cover_geobib_enabled, cover_geobib_timeout "
                "FROM system_settings WHERE id = 1"
            )
        ).one()

        assert row == (1, 2, 1, 2, 1, 2, 1, 2, 1, 2)

        with Operations.context(context):
            _MIGRATION.downgrade()

        columns = {
            column[1] for column in connection.execute(text("PRAGMA table_info(system_settings)"))
        }

    assert "cover_amazon_timeout" not in columns
    engine.dispose()
