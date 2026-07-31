from src.bcd_api.api.v1 import inventory
from src.bcd_api.schemas.inventory import BulkDeleteRequest, BulkUpdateRequest


def test_bulk_update_inventory_serializes_nested_updates(monkeypatch):
    calls = []
    result = {"items_updated": 1, "records_updated": 1, "items_not_found": [], "errors": [], "items_skipped_on_loan": 0, "other_copies_affected": 0}
    monkeypatch.setattr(inventory.inventory_service, "bulk_update_items", lambda **kwargs: calls.append(kwargs) or result)
    request = BulkUpdateRequest(item_ids=["I1"], item_updates={"shelf_location": "A"}, record_updates={"level": "CP"})
    response = inventory.bulk_update_items_endpoint(request, db="db")
    assert response.items_updated == 1
    assert calls[0]["item_updates"] == {"shelf_location": "A"}
    assert calls[0]["record_updates"] == {"level": "CP"}


def test_delete_inventory_bulk_delegates(monkeypatch):
    result = {"items_deleted": 1, "items_skipped_on_loan": 0, "holds_cancelled": 0, "orphan_records_created": 0}
    monkeypatch.setattr(inventory.inventory_service, "delete_items_bulk", lambda db, ids: result)
    response = inventory.delete_items_bulk_endpoint(BulkDeleteRequest(item_ids=["I1"]), db="db")
    assert response.items_deleted == 1
