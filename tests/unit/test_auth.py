import base64

from src.bcd_api.core import auth


def test_auth_disabled_without_credentials(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_username", "")
    monkeypatch.setattr(auth.settings, "auth_password", "")
    assert auth.is_auth_enabled() is False


def test_basic_auth_validation(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_username", "alice")
    monkeypatch.setattr(auth.settings, "auth_password", "secret")
    token = base64.b64encode(b"alice:secret").decode()
    assert auth.validate_basic_auth(f"Basic {token}") is True
    assert auth.validate_basic_auth("Basic invalid") is False
    assert auth.validate_basic_auth("Digest abc") is False


def test_digest_helpers_are_deterministic():
    ha1 = auth.compute_ha1("alice", "secret")
    ha2 = auth.compute_ha2("GET", "/api")
    response = auth.compute_response(ha1, "nonce", ha2)
    assert len(ha1) == 32
    assert len(ha2) == 32
    assert len(response) == 32


def test_parse_digest_header():
    parsed = auth.parse_digest_header('username="alice", nonce="n1", uri="/api", response="r1"')
    assert parsed["username"] == "alice"
    assert parsed["nonce"] == "n1"
    assert parsed["uri"] == "/api"
    assert parsed["response"] == "r1"


def test_create_challenge_respects_auth_scheme(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_scheme", "basic")
    assert auth.create_auth_challenge().startswith("Basic")
    monkeypatch.setattr(auth.settings, "auth_scheme", "digest")
    challenge = auth.create_auth_challenge()
    assert challenge.startswith("Digest")
    assert "realm=" in challenge
    assert "nonce=" in challenge
