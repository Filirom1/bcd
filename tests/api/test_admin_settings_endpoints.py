from types import SimpleNamespace

import pytest

from src.bcd_api.api.v1 import admin


def test_get_and_update_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    monkeypatch.setattr("src.bcd_api.core.config._get_env_file_path", lambda: str(env_file))
    assert admin.get_env_file_content() == {"content": ""}
    assert admin.update_env_file_content({"content": "API_PORT=9000\n"}) == {"content": "API_PORT=9000\n"}
    assert admin.get_env_file_content()["content"] == "API_PORT=9000\n"


def test_get_settings_delegates_to_service(monkeypatch):
    expected = SimpleNamespace(library_code="BCD")
    monkeypatch.setattr(admin.settings_service, "get_settings", lambda db: expected)
    assert admin.get_settings(db=object()) is expected


def test_reset_settings_delegates_to_service(monkeypatch):
    expected = SimpleNamespace(library_code="DEFAULT")
    monkeypatch.setattr(admin.settings_service, "reset_to_defaults", lambda db: expected)
    assert admin.reset_settings(db=object()) is expected


@pytest.mark.asyncio
async def test_update_settings_restarts_mdns_when_library_code_changes(monkeypatch):
    settings = SimpleNamespace(library_code="NEW")
    calls = []
    monkeypatch.setattr(admin.settings_service, "update_settings", lambda db, updates: settings)
    monkeypatch.setattr(admin.mdns_module, "get_server_port", lambda port: 8888)
    async def restart(code, port):
        calls.append((code, port))
    monkeypatch.setattr(admin.mdns_module, "restart_mdns", restart)
    result = await admin.update_settings(admin.SettingsUpdate(updates={"library_code": "NEW"}), db=object())
    assert result is settings
    assert calls == [("NEW", 8888)]


@pytest.mark.asyncio
async def test_update_settings_survives_mdns_failure(monkeypatch):
    settings = SimpleNamespace(library_code="NEW")
    monkeypatch.setattr(admin.settings_service, "update_settings", lambda db, updates: settings)
    monkeypatch.setattr(admin.mdns_module, "get_server_port", lambda port: 8888)
    async def fail(*args):
        raise RuntimeError("mdns unavailable")
    monkeypatch.setattr(admin.mdns_module, "restart_mdns", fail)
    assert await admin.update_settings(admin.SettingsUpdate(updates={"library_code": "NEW"}), db=object()) is settings
