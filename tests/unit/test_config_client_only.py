from src.bcd_api.core.config import Settings


def test_client_only_defaults_to_false():
    """Verify that client_only defaults to False if not specified in env."""
    settings = Settings()
    assert settings.client_only is False


def test_client_only_can_be_enabled_via_env(monkeypatch):
    """Verify that client_only can be set to True via environment variable."""
    monkeypatch.setenv("CLIENT_ONLY", "True")
    settings = Settings()
    assert settings.client_only is True


def test_client_only_can_be_disabled_explicitly_via_env(monkeypatch):
    """Verify that client_only can be set to False via environment variable."""
    monkeypatch.setenv("CLIENT_ONLY", "False")
    settings = Settings()
    assert settings.client_only is False
