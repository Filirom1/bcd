from types import SimpleNamespace

from fastapi import HTTPException

from src.bcd_api.api.v1 import catalog


def test_create_and_get_item_delegate_to_service(monkeypatch):
    expected = SimpleNamespace(item_id="I1")
    calls = []
    monkeypatch.setattr(catalog.catalog_service, "create_item", lambda db, item: calls.append((db, item)) or expected)
    monkeypatch.setattr(catalog.catalog_service, "get_item", lambda db, item_id: expected)
    request = SimpleNamespace(item_id="I1", bibliographic_record_id=1)
    assert catalog.create_item(request, db="db") is expected
    assert catalog.get_item("I1", db="db") is expected
    assert calls == [("db", request)]


def test_update_and_delete_item_delegate(monkeypatch):
    expected = SimpleNamespace(item_id="I1")
    calls = []
    monkeypatch.setattr(catalog.catalog_service, "update_item", lambda **kwargs: calls.append(kwargs) or expected)
    monkeypatch.setattr(catalog.catalog_service, "delete_item", lambda db, item_id: calls.append((db, item_id)))
    assert catalog.update_item_endpoint("I1", {"call_number": "800"}, db="db") is expected
    result = catalog.delete_item_endpoint("I1", db="db")
    assert result.status_code == 204
    assert calls[0]["update_data"] == {"call_number": "800"}
    assert calls[1] == ("db", "I1")


def test_available_item_ids_translates_service_errors(monkeypatch):
    monkeypatch.setattr(catalog.catalog_service, "get_available_item_ids", lambda *args: (_ for _ in ()).throw(ValueError("invalid count")))
    try:
        catalog.get_available_item_ids_endpoint(count=2, db=object())
        assert False
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "invalid count" in exc.detail

    monkeypatch.setattr(catalog.catalog_service, "get_available_item_ids", lambda *args: (_ for _ in ()).throw(NotImplementedError("format")))
    try:
        catalog.get_available_item_ids_endpoint(count=2, db=object())
        assert False
    except HTTPException as exc:
        assert exc.status_code == 501
