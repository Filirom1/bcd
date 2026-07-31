from src.bcd_api.api.v1 import admin
from src.bcd_api.schemas.admin import (
    BulkChangeClassRequest, BulkChangeRoleRequest, BulkDeleteRequest,
    BulkDeleteRecordsRequest, BulkEditRecordsRequest,
)


def result():
    return {"operation": "bulk", "total_count": 2, "successful_count": 2, "failed_count": 0}


def test_bulk_borrower_operations_delegate(monkeypatch):
    monkeypatch.setattr(admin.borrower_service, "bulk_change_class", lambda **kwargs: result())
    monkeypatch.setattr(admin.borrower_service, "bulk_change_role", lambda **kwargs: result())
    monkeypatch.setattr(admin.borrower_service, "bulk_delete_borrowers", lambda **kwargs: result())
    assert admin.bulk_change_class_endpoint(BulkChangeClassRequest(borrower_ids=["A"], target_class_id=2), db="db").total_count == 2
    assert admin.bulk_change_role_endpoint(BulkChangeRoleRequest(borrower_ids=["A"], target_role="teacher"), db="db").successful_count == 2
    assert admin.bulk_delete_borrowers_endpoint(BulkDeleteRequest(borrower_ids=["A"]), db="db").failed_count == 0


def test_bulk_catalog_operations_delegate(monkeypatch):
    calls = []
    monkeypatch.setattr(admin.catalog_service, "bulk_edit_records", lambda **kwargs: calls.append(kwargs) or result())
    monkeypatch.setattr(admin.catalog_service, "bulk_delete_records", lambda **kwargs: calls.append(kwargs) or result())
    edit = BulkEditRecordsRequest(record_ids=[1], language="fr")
    delete = BulkDeleteRecordsRequest(record_ids=[2])
    assert admin.bulk_edit_records_endpoint(edit, db="db").total_count == 2
    assert admin.bulk_delete_records_endpoint(delete, db="db").total_count == 2
    assert calls[0]["language"] == "fr"
    assert calls[1]["record_ids"] == [2]


def test_orphan_endpoints_delegate(monkeypatch):
    data = {"count": 1, "records": [{"id": 1, "title": "Orphan", "isbn": None}]}
    deleted = {"records_deleted": 1}
    monkeypatch.setattr(admin.inventory_service, "get_orphan_records", lambda db: data)
    monkeypatch.setattr(admin.inventory_service, "delete_orphan_records", lambda db: deleted)
    assert admin.get_orphan_records_endpoint(db="db").count == 1
    assert admin.delete_orphan_records_endpoint(db="db").records_deleted == 1
