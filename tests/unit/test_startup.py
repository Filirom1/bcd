from unittest.mock import MagicMock, patch
import pytest

from src.bcd_api.core import startup
from src.bcd_api import main


@pytest.mark.asyncio
async def test_init_system_settings_caches_library_code(monkeypatch):
    db_mock = MagicMock()
    monkeypatch.setattr("src.bcd_api.core.database.SessionLocal", lambda: db_mock)
    settings_mock = MagicMock(library_code="STARTUP_TEST")
    monkeypatch.setattr("src.bcd_api.services.settings_service.get_settings", lambda db: settings_mock)
    monkeypatch.setattr("src.bcd_api.services.settings_service.initialize_default_settings", lambda db: None)

    from src.bcd_api.core.spa import get_library_code
    code = await startup.init_system_settings()
    assert code == "STARTUP_TEST"
    assert get_library_code() == "STARTUP_TEST"


@pytest.mark.asyncio
async def test_auto_backup_skipped_when_recent(monkeypatch):
    backup_mock = MagicMock()
    backup_mock.age_days = 2
    backup_mock.created_at = "some-date"

    list_backups_mock = MagicMock(return_value=[backup_mock])
    create_backup_mock = MagicMock()

    monkeypatch.setattr("src.bcd_api.services.backup_service.list_backups", list_backups_mock)
    monkeypatch.setattr("src.bcd_api.services.backup_service.create_backup", create_backup_mock)

    await startup.auto_backup_if_needed()

    list_backups_mock.assert_called_once()
    create_backup_mock.assert_not_called()


@pytest.mark.asyncio
async def test_auto_backup_created_when_old(monkeypatch):
    backup_mock = MagicMock()
    backup_mock.age_days = 10
    backup_mock.created_at = "some-date"

    list_backups_mock = MagicMock(return_value=[backup_mock])
    create_backup_mock = MagicMock()

    monkeypatch.setattr("src.bcd_api.services.backup_service.list_backups", list_backups_mock)
    monkeypatch.setattr("src.bcd_api.services.backup_service.create_backup", create_backup_mock)

    await startup.auto_backup_if_needed()

    list_backups_mock.assert_called_once()
    create_backup_mock.assert_called_once()


def test_expire_ready_holds_non_fatal_on_error(monkeypatch):
    db_mock = MagicMock()
    monkeypatch.setattr("src.bcd_api.core.database.SessionLocal", lambda: db_mock)
    
    def raise_err(*args, **kwargs):
        raise Exception("Database down")
        
    monkeypatch.setattr("src.bcd_api.services.holds.commands.expire_ready_holds", raise_err)

    # Should not raise an exception
    startup.expire_ready_holds_on_startup()


def test_migrate_covers_non_fatal_on_error(monkeypatch):
    db_mock = MagicMock()
    monkeypatch.setattr("src.bcd_api.core.database.SessionLocal", lambda: db_mock)

    def raise_err(*args, **kwargs):
        raise Exception("Disk full")

    monkeypatch.setattr("src.bcd_api.services.external.cover.migrate_covers_to_isbn13", raise_err)

    # Should not raise an exception
    startup._migrate_covers()
