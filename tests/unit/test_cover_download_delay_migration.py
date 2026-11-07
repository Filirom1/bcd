"""Tests for the configurable bulk cover download delay migration."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "e2f3a4b5c6d7_add_cover_download_delay_setting.py"
)
_SPEC = importlib.util.spec_from_file_location("cover_download_delay_migration", _MIGRATION_PATH)
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)


def test_upgrade_adds_default_delay_and_downgrade_removes_it():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE system_settings (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO system_settings (id) VALUES (1)"))

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            _MIGRATION.upgrade()

        delay = connection.execute(
            text("SELECT cover_download_delay_seconds FROM system_settings WHERE id = 1")
        ).scalar_one()
        assert delay == 60

        with Operations.context(context):
            _MIGRATION.downgrade()

        columns = {
            column[1] for column in connection.execute(text("PRAGMA table_info(system_settings)"))
        }

    assert "cover_download_delay_seconds" not in columns
    engine.dispose()
