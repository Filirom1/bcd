from src.bcd_api.api.v1 import admin
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.schemas.admin import (
    BulkChangeClassRequest, BulkChangeRoleRequest, BulkDeleteRequest,
    BulkDeleteRecordsRequest, BulkEditRecordsRequest, MergeItemUpdate,
    MergeRecordsRequest,
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


def test_merge_catalog_records_endpoint_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(
        admin.catalog_service,
        "merge_bibliographic_records",
        lambda **kwargs: calls.append(kwargs) or result(),
    )

    request = MergeRecordsRequest(
        target_id=1,
        source_ids=[2, 3],
        item_updates=[MergeItemUpdate(item_id=10, shelf_location="Romans", call_number="R DUP")],
    )
    response = admin.merge_records_endpoint(request, db="db")

    assert response.successful_count == 2
    assert calls == [{
        "db": "db",
        "target_id": 1,
        "source_ids": [2, 3],
        "item_updates": request.item_updates,
    }]


def test_merge_catalog_records_endpoint_runs_real_service(db_session):
    target = BibliographicRecord(title="Target", medium_type="Livre")
    source = BibliographicRecord(title="Source", medium_type="Livre")
    db_session.add_all([target, source])
    db_session.commit()

    response = admin.merge_records_endpoint(
        MergeRecordsRequest(target_id=target.id, source_ids=[source.id]),
        db=db_session,
    )

    assert response.operation == "merge_bibliographic_records"
    assert response.successful_count == 1
    assert db_session.get(BibliographicRecord, source.id) is None
    assert db_session.get(BibliographicRecord, target.id) is not None


def test_orphan_endpoints_delegate(monkeypatch):
    data = {"count": 1, "records": [{"id": 1, "title": "Orphan", "isbn": None}]}
    deleted = {"records_deleted": 1}
    monkeypatch.setattr(admin.inventory_service, "get_orphan_records", lambda db: data)
    monkeypatch.setattr(admin.inventory_service, "delete_orphan_records", lambda db: deleted)
    assert admin.get_orphan_records_endpoint(db="db").count == 1
    assert admin.delete_orphan_records_endpoint(db="db").records_deleted == 1
