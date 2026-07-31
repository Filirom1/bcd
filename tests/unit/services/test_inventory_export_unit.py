from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.bcd_api.services import inventory_service


def test_get_items_csv_formats_item_and_dates():
    record = SimpleNamespace(title="Book", authors='["Author"]')
    item = SimpleNamespace(item_id="I1", bibliographic_record=record, call_number="800", shelf_location="A", status="available", condition="good", last_borrowed_at=datetime(2025, 1, 2, tzinfo=timezone.utc), last_inventoried_at=datetime(2025, 1, 3, tzinfo=timezone.utc))
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.all.return_value = [item]
    csv = inventory_service.get_items_csv(db, ["I1"])
    assert ".I1,Book,Author,800,A,available,good,2025-01-02,2025-01-03" in csv


def test_get_items_csv_handles_invalid_authors():
    record = SimpleNamespace(title="Book", authors="invalid")
    item = SimpleNamespace(item_id="I1", bibliographic_record=record, call_number=None, shelf_location=None, status="available", condition="good", last_borrowed_at=None, last_inventoried_at=None)
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.all.return_value = [item]
    csv = inventory_service.get_items_csv(db, ["I1"])
    assert ".I1,Book,," in csv
