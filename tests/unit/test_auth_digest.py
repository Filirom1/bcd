from unittest.mock import MagicMock

from starlette.requests import Request

from src.bcd_api.core import auth


def request():
    return Request({"type": "http", "method": "GET", "path": "/api"})


def test_digest_auth_valid_without_qop(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_username", "alice")
    monkeypatch.setattr(auth.settings, "auth_password", "secret")
    monkeypatch.setattr(auth, "validate_nonce", lambda value: True)
    nonce = "nonce"
    ha1 = auth.compute_ha1("alice", "secret", auth.REALM)
    response = auth.compute_response(ha1, nonce, auth.compute_ha2("GET", "/api"))
    header = f'Digest username="alice", realm="{auth.REALM}", nonce="{nonce}", uri="/api", response="{response}"'
    assert auth.validate_digest_auth(request(), header) is True


def test_digest_auth_rejects_wrong_user_realm_nonce_and_response(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_username", "alice")
    monkeypatch.setattr(auth.settings, "auth_password", "secret")
    for header in [
        'Digest username="bob", realm="BCD", nonce="n", uri="/api", response="x"',
        'Digest username="alice", realm="wrong", nonce="n", uri="/api", response="x"',
        'Digest username="alice", realm="BCD", nonce="n", uri="/api", response="x"',
    ]:
        monkeypatch.setattr(auth, "validate_nonce", lambda value: False)
        assert auth.validate_digest_auth(request(), header) is False


def test_digest_auth_rejects_missing_fields(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_username", "alice")
    assert auth.validate_digest_auth(request(), 'Digest username="alice"') is False


def test_basic_auth_rejects_missing_separator_and_invalid_encoding(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_username", "alice")
    monkeypatch.setattr(auth.settings, "auth_password", "secret")
    assert auth.validate_basic_auth("Basic YWxpY2U=") is False
    assert auth.validate_basic_auth("Basic !!!") is False
