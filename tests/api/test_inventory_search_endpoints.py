from src.bcd_api.api.v1 import inventory


def test_search_inventory_forwards_filters(monkeypatch):
    result = {"items": [], "total_count": 0, "displayed_count": 0, "capped": False, "archive_cutoff_date": None}
    calls = []
    monkeypatch.setattr(inventory.inventory_service, "search_items", lambda **kwargs: calls.append(kwargs) or result)
    response = inventory.search_items_endpoint(db="db", q="book", status="available", no_limit=True)
    assert response.total_count == 0
    assert calls[0]["q"] == "book"
    assert calls[0]["no_limit"] is True
