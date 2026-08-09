from types import SimpleNamespace

from src.bcd_api.api.v1 import catalog


def test_update_record_delegates_payload(monkeypatch):
    expected = SimpleNamespace(id=4, title="Updated")
    calls = []
    monkeypatch.setattr(catalog.catalog_service, "update_record", lambda **kwargs: calls.append(kwargs) or expected)
    payload = {"title": "Updated"}
    assert catalog.update_record_endpoint(4, payload, db="db") is expected
    assert calls == [{"db": "db", "record_id": 4, "update_data": payload}]


def test_delete_record_uses_bulk_service(monkeypatch):
    calls = []
    monkeypatch.setattr(catalog.catalog_service, "bulk_delete_records", lambda db, ids: calls.append((db, ids)))
    assert catalog.delete_bibliographic_record(4, db="db") is None
    assert calls == [("db", [4])]


def test_get_items_for_record_verifies_record_before_listing(monkeypatch):
    record = SimpleNamespace(id=4)
    items = [SimpleNamespace(item_id="I1")]
    calls = []
    monkeypatch.setattr(catalog.catalog_service, "get_bibliographic_record", lambda db, record_id: calls.append(("record", record_id)) or record)
    monkeypatch.setattr(catalog.catalog_service, "get_items_for_bibliographic_record", lambda db, record_id: calls.append(("items", record_id)) or items)
    assert catalog.get_items_for_bibliographic_record(4, db="db") == items
    assert calls == [("record", 4), ("items", 4)]
