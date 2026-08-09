import pytest
from fastapi import HTTPException

from src.bcd_api.api.v1 import admin


def ok_result():
    return {"operation": "bulk", "total_count": 1, "successful_count": 1, "failed_count": 0}


def test_bulk_edit_change_class_and_role(monkeypatch):
    calls = []
    monkeypatch.setattr(admin.borrower_service, "bulk_change_class", lambda **kwargs: calls.append(("class", kwargs)) or ok_result())
    monkeypatch.setattr(admin.borrower_service, "bulk_change_role", lambda **kwargs: calls.append(("role", kwargs)) or ok_result())
    assert admin.bulk_edit_borrowers_endpoint("change_class", ["B1"], target_class_id=4, db="db").successful_count == 1
    assert admin.bulk_edit_borrowers_endpoint("change_role", ["B1"], target_role="staff", db="db").successful_count == 1
    assert calls[0][1]["new_class_id"] == 4
    assert calls[1][1]["new_role"] == "staff"


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"operation": "change_class", "borrower_ids": ["B1"]}, "target_class_id"),
        ({"operation": "change_role", "borrower_ids": ["B1"]}, "target_role"),
        ({"operation": "unknown", "borrower_ids": ["B1"]}, "Unknown operation"),
    ],
)
def test_bulk_edit_rejects_invalid_operation(kwargs, message):
    with pytest.raises(HTTPException) as exc:
        admin.bulk_edit_borrowers_endpoint(db="db", **kwargs)
    assert exc.value.status_code == 400
    assert message in exc.value.detail
