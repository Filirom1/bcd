from types import SimpleNamespace
from unittest.mock import patch
import pytest

from src.bcd_api.services.borrower.import_ import import_borrowers_from_csv
from src.bcd_api.core.exceptions import NotFoundError, ValidationError


def test_import_borrowers_reports_validation_rows():
    csv_text = "borrower_id,first_name,last_name,role\n,NoId,Name,student\nB2,,Name,student\nB3,First,,student\nB4,First,Name,parent\n"
    result = import_borrowers_from_csv(db=object(), csv_text=csv_text)
    assert result["total_rows"] == 4
    assert result["failed_rows"] == 4
    assert result["successful_rows"] == 0
    assert len(result["errors"]) == 4


def test_import_borrowers_creates_and_updates(monkeypatch):
    created = []
    updated = []

    # Mock borrower_service functions used inside import_borrowers_from_csv
    from src.bcd_api.services.borrower import import_ as import_module
    monkeypatch.setattr(import_module, "get_borrower_by_id", lambda db, value: (_ for _ in ()).throw(NotFoundError("Borrower", value)) if value == "NEW" else SimpleNamespace())
    monkeypatch.setattr(import_module, "create_borrower", lambda **kwargs: created.append(kwargs))
    monkeypatch.setattr(import_module, "update_borrower", lambda **kwargs: updated.append(kwargs))

    csv_text = "StudentID,FirstName,LastName,Class,Role,Active\nNEW,Zo\xC3\xAB,Nom,CM1,student,oui\nOLD,Alice,Existing,,teacher,false\n"
    result = import_borrowers_from_csv(db=object(), csv_text=csv_text)
    assert result["borrowers_created"] == 1
    assert result["borrowers_updated"] == 1
    assert created[0]["borrower_id"] == "NEW"
    assert updated[0]["active"] is False


def test_import_borrowers_accepts_latin1_and_class_creation_failure(monkeypatch):
    from src.bcd_api.services.borrower import import_ as import_module
    monkeypatch.setattr(import_module, "get_borrower_by_id", lambda *args: (_ for _ in ()).throw(NotFoundError("Borrower", "B1")))
    monkeypatch.setattr(import_module, "create_borrower", lambda **kwargs: None)

    # Use decoded string from latin-1 for import_borrowers_from_csv
    csv_text = "StudentID,FirstName,LastName,Class\nB1,Élise,École,CM1\n"
    result = import_borrowers_from_csv(db=object(), csv_text=csv_text)
    assert result["successful_rows"] == 1
