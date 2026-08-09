from types import SimpleNamespace
from datetime import datetime
import pytest
from unittest.mock import MagicMock

from src.bcd_api.api.v1 import inventory
from src.bcd_api.schemas.inventory import (
    BulkDeleteRequest,
    BulkInventoryRequest,
    BulkUpdateRequest,
    ItemUpdates,
    RecordUpdates
)


def test_mark_item_inventoried_endpoint(monkeypatch):
    """Test mark_item_inventoried_endpoint delegates to inventory_service."""
    mock_item = SimpleNamespace(
        item_id="0001",
        bibliographic_record_id=42,
        status="available",
        condition="good",
        loanable=True,
        shelf_location="Shelf A",
        call_number="C-EXU",
        last_inventoried_at=datetime(2025, 1, 1),
        bibliographic_record=SimpleNamespace(
            title="Le Petit Prince",
            level="easy",
            target_audience="child",
            language="fr",
            medium_type="Livre"
        )
    )

    monkeypatch.setattr(inventory.inventory_service, "mark_item_inventoried", lambda db, item_id: mock_item)

    result = inventory.mark_item_inventoried_endpoint("0001", db=object())
    assert result.item_id == "0001"
    assert result.title == "Le Petit Prince"
    assert result.condition == "good"


def test_bulk_mark_inventoried_endpoint(monkeypatch):
    """Test bulk_mark_inventoried_endpoint delegates to inventory_service."""
    called_ids = []
    
    def mock_bulk(db, item_ids):
        called_ids.extend(item_ids)
        return {
            "items_updated": len(item_ids),
            "items_not_found": [],
            "timestamp": datetime(2025, 1, 1)
        }

    monkeypatch.setattr(inventory.inventory_service, "bulk_mark_inventoried", mock_bulk)

    req = BulkInventoryRequest(item_ids=["0001", "0002"])
    result = inventory.bulk_mark_inventoried_endpoint(req, db=object())

    assert called_ids == ["0001", "0002"]
    assert result.items_updated == 2


def test_bulk_update_items_endpoint(monkeypatch):
    """Test bulk_update_items_endpoint delegates to inventory_service."""
    called = []

    def mock_update(db, item_ids, item_updates, record_updates):
        called.append((item_ids, item_updates, record_updates))
        return {
            "items_updated": len(item_ids),
            "items_skipped_on_loan": 0,
            "records_updated": 1,
            "other_copies_affected": 0
        }

    monkeypatch.setattr(inventory.inventory_service, "bulk_update_items", mock_update)

    req = BulkUpdateRequest(
        item_ids=["0001"],
        item_updates=ItemUpdates(status="in_repair", condition="damaged"),
        record_updates=RecordUpdates(level="easy")
    )

    result = inventory.bulk_update_items_endpoint(req, db=object())

    assert len(called) == 1
    assert called[0][0] == ["0001"]
    assert called[0][1]["status"] == "in_repair"
    assert called[0][2]["level"] == "easy"
    assert result.items_updated == 1


def test_delete_items_bulk_endpoint(monkeypatch):
    """Test delete_items_bulk_endpoint delegates to inventory_service."""
    called_ids = []

    def mock_delete(db, item_ids):
        called_ids.extend(item_ids)
        return {
            "items_deleted": len(item_ids),
            "items_skipped_on_loan": 0,
            "holds_cancelled": 0,
            "orphan_records_created": 0
        }

    monkeypatch.setattr(inventory.inventory_service, "delete_items_bulk", mock_delete)

    req = BulkDeleteRequest(item_ids=["0001", "0002"])
    result = inventory.delete_items_bulk_endpoint(req, db=object())

    assert called_ids == ["0001", "0002"]
    assert result.items_deleted == 2
