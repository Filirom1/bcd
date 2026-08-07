from unittest.mock import MagicMock

from src.bcd_api.core.runner import _parse_args, _get_startup_library_code
from src.bcd_api.core.config import settings


def test_parse_args_defaults():
    args = _parse_args([])
    assert args.ui_mode == settings.ui_mode


def test_parse_args_client_only_flag():
    args = _parse_args(["--client-only"])
    assert args.client_only is True


def test_parse_args_host_port():
    args = _parse_args(["--host", "0.0.0.0", "--port", "9000"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_startup_library_code_reads_database_settings(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr("src.bcd_api.core.database.SessionLocal", lambda: db)
    monkeypatch.setattr("src.bcd_api.services.settings_service.get_settings", lambda session: MagicMock(library_code="BCD"))
    assert _get_startup_library_code() == "BCD"
    db.close.assert_called_once()
