from src.bcd_api.core.config import Settings


def test_auto_update_defaults_to_true():
    """Verify that auto_update defaults to True if not specified in env."""
    settings = Settings()
    assert settings.auto_update is True


def test_auto_update_can_be_disabled_via_env(monkeypatch):
    """Verify that auto_update can be set to False via environment variable."""
    monkeypatch.setenv("AUTO_UPDATE", "False")
    settings = Settings()
    assert settings.auto_update is False


def test_auto_update_can_be_enabled_explicitly_via_env(monkeypatch):
    """Verify that auto_update can be set to True via environment variable."""
    monkeypatch.setenv("AUTO_UPDATE", "True")
    settings = Settings()
    assert settings.auto_update is True
