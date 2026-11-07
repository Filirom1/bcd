import sys
from unittest.mock import MagicMock

from src.bcd_api.core.config import settings
from src.bcd_api.core.runner import (
    _get_startup_library_code,
    _kids_client_environment,
    _parse_args,
)


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
    monkeypatch.setattr(
        "src.bcd_api.services.settings_service.get_settings",
        lambda session: MagicMock(library_code="BCD"),
    )
    assert _get_startup_library_code() == "BCD"
    db.close.assert_called_once()


def test_kids_client_environment_restores_original_library_path(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/bcd/_internal:/usr/lib")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib")

    env = _kids_client_environment(proxy_port=8889)

    assert env["LD_LIBRARY_PATH"] == "/usr/lib"
    assert "LD_LIBRARY_PATH_ORIG" not in env
    assert env["BCD_MDNS_PROXY_PORT"] == "8889"


def test_kids_client_environment_removes_bundled_library_path_if_original_empty(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/bcd/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "")

    env = _kids_client_environment()

    assert "LD_LIBRARY_PATH" not in env
    assert "LD_LIBRARY_PATH_ORIG" not in env


def test_portable_linux_kids_environment_removes_bundle_path_without_original(monkeypatch):
    import src.bcd_api.core.runner as runner

    monkeypatch.setattr(runner, "is_portable", lambda: True)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/bcd/_internal")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)

    env = _kids_client_environment()

    assert "LD_LIBRARY_PATH" not in env
