from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.bcd_api.api.v1 import catalog


def test_get_shelf_locations_returns_sorted_query_values():
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.distinct.return_value.order_by.return_value.all.return_value = [("A",), ("B",)]
    assert catalog.get_shelf_locations(db) == {"locations": ["A", "B"]}


def test_lookup_isbn_returns_service_data(monkeypatch):
    expected = {"title": "Book", "isbn": "123"}
    monkeypatch.setattr(catalog, "lookup_isbn", lambda db, isbn: expected, raising=False)
    # The endpoint imports the function locally, so patch the service module too.
    monkeypatch.setattr("src.bcd_api.services.catalog_service.lookup_isbn", lambda db, isbn: expected)
    assert catalog.lookup_isbn_endpoint(isbn="123", db=object()) == expected


def test_lookup_isbn_raises_404_when_not_found(monkeypatch):
    monkeypatch.setattr("src.bcd_api.services.catalog_service.lookup_isbn", lambda db, isbn: None)
    with pytest.raises(Exception) as exc:
        catalog.lookup_isbn_endpoint(isbn="missing", db=object())
    assert getattr(exc.value, "status_code", None) == 404


def test_create_bibliographic_record_delegates(monkeypatch):
    expected = SimpleNamespace(id=1, title="Book")
    calls = []
    monkeypatch.setattr(catalog.catalog_service, "create_bibliographic_record", lambda **kwargs: calls.append(kwargs) or expected)
    request = SimpleNamespace(title="Book", isbn="123")
    assert catalog.create_bibliographic_record(request, db="db", isbn_lookup=True) is expected
    assert calls[0]["db"] == "db"
    assert calls[0]["isbn_lookup"] is True
