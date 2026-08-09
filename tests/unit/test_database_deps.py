from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from src.bcd_api.core import database, deps


def test_get_db_closes_session():
    session = MagicMock()
    with patch("src.bcd_api.core.deps.SessionLocal", return_value=session):
        yielded = next(deps.get_db())
        assert yielded is session
        # Generator finalization closes the injected session.
        generator = deps.get_db()
        next(generator)
        generator.close()
    session.close.assert_called()


def test_get_settings_returns_existing():
    settings = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = settings
    assert deps.get_settings(db) is settings
    db.add.assert_not_called()


def test_get_settings_raises_when_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    from src.bcd_api.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        deps.get_settings(db)

    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_database_engine_supports_sqlite_queries():
    with database.engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar() == 1
