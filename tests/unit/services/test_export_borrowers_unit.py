from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.bcd_api.core.exceptions import ExportTooLargeException
from src.bcd_api.services.export_service import ExportService


def test_borrower_to_dict_with_class_and_blocked_reason():
    borrower = SimpleNamespace(
        borrower_id="B1", first_name="Alice", last_name="Doe", role="student",
        class_=SimpleNamespace(name="CM1"), barcode="BC1", active=True, blocked_reason="late",
    )
    row = ExportService(None)._borrower_to_dict(borrower)
    assert row["class"] == "CM1"
    assert row["active"] == "true"
    assert row["blocked"] == "true"
    assert row["blocked_reason"] == "late"


def test_export_borrowers_empty_catalog():
    db = MagicMock()
    db.query.return_value.options.return_value.all.return_value = []
    content, count = ExportService(db).export_borrowers_to_csv()
    assert count == 0
    assert "borrower_id" in content


def test_export_borrowers_translates_unexpected_error():
    db = MagicMock()
    db.query.side_effect = RuntimeError("database offline")
    with pytest.raises(Exception) as exc:
        ExportService(db).export_borrowers_to_csv()
    assert "database offline" in str(exc.value)


def test_export_borrowers_enforces_limit(monkeypatch):
    borrower = SimpleNamespace(class_=None, borrower_id="B1")
    db = MagicMock()
    db.query.return_value.options.return_value.all.return_value = [borrower]
    monkeypatch.setattr("src.bcd_api.services.export_service.MAX_BORROWER_ROWS", 0)
    with pytest.raises(ExportTooLargeException):
        ExportService(db).export_borrowers_to_csv()
