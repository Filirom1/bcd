from types import SimpleNamespace
import pytest
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.bcd_api.api.v1 import borrowers
from src.bcd_api.schemas.borrower import BorrowerCreate, BorrowerUpdate


class MockBorrower:
    def __init__(self):
        self.id = 123
        self.borrower_id = "1001"
        self.first_name = "Alice"
        self.last_name = "Dupont"
        self.full_name = "Alice Dupont"
        self.role = "student"
        self.class_id = None
        self.email = "alice@school.com"
        self.phone = "0123456789"
        self.notes = "Some notes"
        self.active = True
        self.blocked = False
        self.blocked_reason = None
        self.created_at = datetime(2025, 1, 1)
        self.updated_at = datetime(2025, 1, 1)

    @property
    def barcode(self):
        return ".1001"

    @property
    def __dict__(self):
        return {
            "id": self.id,
            "borrower_id": self.borrower_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "role": self.role,
            "class_id": self.class_id,
            "email": self.email,
            "phone": self.phone,
            "notes": self.notes,
            "active": self.active,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


def test_create_borrower_endpoint_delegation(monkeypatch):
    """Test that create_borrower route handler delegates to borrower_service correctly."""
    called_args = {}

    def mock_create_borrower(db, borrower_id, first_name, last_name, role, **kwargs):
        called_args.update({
            "borrower_id": borrower_id,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            **kwargs
        })
        # Return a mock borrower model
        return SimpleNamespace(
            id=123,
            borrower_id=borrower_id,
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            role=role,
            class_id=kwargs.get("class_id"),
            email=kwargs.get("email"),
            phone=kwargs.get("phone"),
            notes=kwargs.get("notes"),
            barcode=f".{borrower_id}",
            active=True,
            blocked=False,
            blocked_reason=None,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )

    monkeypatch.setattr(borrowers.borrower_service, "create_borrower", mock_create_borrower)

    # Request schema
    request = BorrowerCreate(
        borrower_id="1001",
        first_name="Alice",
        last_name="Dupont",
        role="student",
        class_id=2,
        email="alice@school.com",
        phone="0123456789",
        notes="Some notes"
    )

    result = borrowers.create_borrower(request, db=object())

    # Verify delegation and return value matching schema
    assert called_args["borrower_id"] == "1001"
    assert called_args["first_name"] == "Alice"
    assert called_args["last_name"] == "Dupont"
    assert called_args["role"] == "student"
    assert called_args["class_id"] == 2
    assert called_args["email"] == "alice@school.com"
    assert called_args["phone"] == "0123456789"
    assert called_args["notes"] == "Some notes"

    assert result.id == 123
    assert result.borrower_id == "1001"
    assert result.full_name == "Alice Dupont"


def test_get_next_available_id_endpoint_delegation(monkeypatch):
    """Test that get_next_available_id route handler delegates to borrower_service."""
    monkeypatch.setattr(borrowers.borrower_service, "get_next_available_id", lambda db: "42")
    
    result = borrowers.get_next_available_id(db=object())
    assert result == {"next_id": "42"}


def test_get_borrower_endpoint(monkeypatch):
    """Test get_borrower route handler."""
    mock_data = {
        "id": 1,
        "borrower_id": "1001",
        "first_name": "Test",
        "last_name": "User",
        "full_name": "Test User",
        "role": "student",
        "active": True,
        "blocked": False,
        "barcode": "1001",
        "current_loans_count": 1,
        "total_checkouts": 5,
        "overdue_count": 0,
        "loan_limit": 2,
        "loan_limit_warning": 1,
        "class_name": "CP",
        "homeroom_teacher": "M. Dupont",
    }
    monkeypatch.setattr(borrowers.borrower_service, "get_detailed_borrower", lambda db, b_id, include_loans=False: mock_data)

    result = borrowers.get_borrower("1001", detail=False, db=object())
    assert result["borrower_id"] == "1001"
    assert result["current_loans_count"] == 1
    assert result["total_checkouts"] == 5


def test_update_borrower_endpoint(monkeypatch):
    """Test update_borrower route handler."""
    called = []
    def mock_update(db, borrower_id, **kwargs):
        called.append((borrower_id, kwargs))
        return SimpleNamespace(id=123, borrower_id=borrower_id, **kwargs)

    monkeypatch.setattr(borrowers.borrower_service, "update_borrower", mock_update)

    update_data = BorrowerUpdate(
        borrower_id="1002",
        first_name="Alice",
        last_name="Dupont",
        role="student",
        class_id=2,
        email="new@school.com",
        phone="0987654321",
        notes="Updated notes",
        active=True,
        blocked_reason="Reason"
    )

    result = borrowers.update_borrower("1001", update_data, db=object())
    assert len(called) == 1
    assert called[0][0] == "1001"
    assert called[0][1]["new_borrower_id"] == "1002"
    assert result.email == "new@school.com"


def test_block_and_unblock_borrower_endpoints(monkeypatch):
    """Test block_borrower and unblock_borrower route handlers."""
    block_called = []
    unblock_called = []

    monkeypatch.setattr(borrowers.borrower_service, "block_borrower", lambda db, b_id, reason: block_called.append((b_id, reason)) or SimpleNamespace(id=123, borrower_id=b_id, blocked_reason=reason))
    monkeypatch.setattr(borrowers.borrower_service, "unblock_borrower", lambda db, b_id: unblock_called.append(b_id) or SimpleNamespace(id=123, borrower_id=b_id, blocked_reason=None))

    res_block = borrowers.block_borrower("1001", reason="No return", db=object())
    assert block_called == [("1001", "No return")]
    assert res_block.blocked_reason == "No return"

    res_unblock = borrowers.unblock_borrower("1001", db=object())
    assert unblock_called == ["1001"]
    assert res_unblock.blocked_reason is None


def test_delete_borrower_endpoint(monkeypatch):
    """Test delete_borrower route handler."""
    deleted = []
    monkeypatch.setattr(borrowers.borrower_service, "bulk_delete_borrowers", lambda db, ids: deleted.extend(ids))

    result = borrowers.delete_borrower("1001", db=object())
    assert result is None
    assert deleted == ["1001"]
