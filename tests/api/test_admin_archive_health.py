import pytest
from fastapi import HTTPException

from src.bcd_api.api.v1 import admin


def test_archive_stats_and_transactions(monkeypatch):
    stats = {"total": 3}
    transactions = [{"id": 1}]
    monkeypatch.setattr(admin.archive_service, "get_archive_stats", lambda db: stats)
    monkeypatch.setattr(admin.archive_service, "get_archived_transactions", lambda **kwargs: transactions)
    assert admin.get_archive_stats(db="db") == stats
    assert admin.get_archived_transactions(borrower_id=2, item_id=3, limit=5, offset=1, db="db") == {"transactions": transactions, "limit": 5, "offset": 1}


def test_archive_transactions_passes_parameters(monkeypatch):
    calls = []
    monkeypatch.setattr(admin.archive_service, "archive_old_transactions", lambda **kwargs: calls.append(kwargs) or {"archived": 2})
    assert admin.archive_transactions(older_than_years=3, dry_run=True, db="db") == {"archived": 2}
    assert calls == [{"db": "db", "older_than_years": 3, "dry_run": True}]


def test_archive_invalid_value_is_400(monkeypatch):
    monkeypatch.setattr(admin.archive_service, "archive_old_transactions", lambda **kwargs: (_ for _ in ()).throw(ValueError("years must be positive")))
    with pytest.raises(HTTPException) as exc:
        admin.archive_transactions(db="db")
    assert exc.value.status_code == 400


def test_health_reports_counts(monkeypatch):
    db = type("DB", (), {})()
    db.execute = lambda query: None
    db.query = lambda model: type("Q", (), {"count": lambda self: 2})()
    result = admin.health_check(db=db)
    assert result["status"] == "healthy"
    assert result["database"] == "connected"
    assert result["counts"]["items"] == 2


def test_health_converts_database_failure():
    class DB:
        def execute(self, query):
            raise RuntimeError("database offline")
    with pytest.raises(HTTPException) as exc:
        admin.health_check(db=DB())
    assert exc.value.status_code == 503
    assert "database offline" in exc.value.detail
