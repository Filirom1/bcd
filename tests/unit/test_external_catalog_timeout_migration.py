"""Tests for the external catalog timeout defaults migration."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "a1b2c3d4e5f6_shorten_external_catalog_timeout_defaults.py"
)
_SPEC = importlib.util.spec_from_file_location("external_timeout_migration", _MIGRATION_PATH)
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)


def test_upgrade_shortens_only_unchanged_default_timeouts():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE system_settings ("
                "bnf_timeout INTEGER, google_books_timeout INTEGER, sudoc_timeout INTEGER)"
            )
        )
        connection.execute(text("INSERT INTO system_settings VALUES " "(4, 4, 5), (11, 12, 13)"))

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            _MIGRATION.upgrade()

        rows = connection.execute(
            text(
                "SELECT bnf_timeout, google_books_timeout, sudoc_timeout "
                "FROM system_settings ORDER BY bnf_timeout"
            )
        ).all()

    assert rows == [(2, 2, 3), (11, 12, 13)]
    engine.dispose()
