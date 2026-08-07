from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock

from src.bcd_api.api.v1 import catalog
from src.bcd_api.schemas.bibliographic_record import BiblographicRecordCreate
from src.bcd_api.schemas.item import ItemCreate


def test_get_shelf_locations_endpoint():
    """Test get_shelf_locations endpoint queries DB and returns unique sorted locations."""
    # Setup mock DB query
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_distinct = mock_filter.distinct.return_value
    mock_order = mock_distinct.order_by.return_value
    mock_order.all.return_value = [("Shelf A",), ("Shelf B",)]

    result = catalog.get_shelf_locations(db=mock_db)

    # Verify query structure
    mock_db.query.assert_called_once()
    assert result == {"locations": ["Shelf A", "Shelf B"]}


def test_create_bibliographic_record_endpoint(monkeypatch):
    """Test create_bibliographic_record endpoint delegates to catalog_service."""
    called_args = {}

    def mock_create(db, record_data, isbn_lookup):
        called_args.update({
            "record_data": record_data,
            "isbn_lookup": isbn_lookup
        })
        return SimpleNamespace(
            id=42,
            isbn=record_data.isbn,
            title=record_data.title,
            authors=record_data.authors,
            medium_type=record_data.medium_type,
            total_items=0
        )

    monkeypatch.setattr(catalog.catalog_service, "create_bibliographic_record", mock_create)

    req = BiblographicRecordCreate(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors=["Antoine de Saint-Exupéry"],
        medium_type="Livre"
    )

    result = catalog.create_bibliographic_record(req, isbn_lookup=True, db=object())

    assert called_args["isbn_lookup"] is True
    assert called_args["record_data"].title == "Le Petit Prince"
    assert result.id == 42
    assert result.title == "Le Petit Prince"


def test_create_item_endpoint(monkeypatch):
    """Test create_item endpoint delegates to catalog_service."""
    called_args = {}

    def mock_create_item(db, item):
        called_args.update({"item": item})
        return SimpleNamespace(
            id=101,
            item_id=item.item_id,
            bibliographic_record_id=item.bibliographic_record_id,
            status="available",
            condition="good"
        )

    monkeypatch.setattr(catalog.catalog_service, "create_item", mock_create_item)

    req = ItemCreate(
        item_id="0001",
        bibliographic_record_id=42,
        status="available",
        condition="good"
    )

    result = catalog.create_item(req, db=object())

    assert called_args["item"].item_id == "0001"
    assert called_args["item"].bibliographic_record_id == 42
    assert result.id == 101
    assert result.item_id == "0001"


def test_get_item_endpoint(monkeypatch):
    """Test get_item endpoint delegates to catalog_service."""
    monkeypatch.setattr(catalog.catalog_service, "get_item", lambda db, item_id: SimpleNamespace(
        id=101,
        item_id=item_id,
        status="available"
    ))

    result = catalog.get_item("0001", db=object())
    assert result.item_id == "0001"
    assert result.status == "available"


def test_search_bibliographic_records_endpoint(monkeypatch):
    """Test search_bibliographic_records endpoint."""
    # Mock records returned by service
    mock_record = SimpleNamespace(
        id=42,
        isbn="978-2070408504",
        isbn_value="2070408504",
        identifier_type="ISBN",
        title="Le Petit Prince",
        subtitle=None,
        authors='["Antoine de Saint-Exupéry"]',
        publisher="Gallimard",
        publication_year=1943,
        collection=None,
        series_number=None,
        medium_type="Livre",
        target_audience="child",
        level="easy",
        language="fr",
        binding_type="paperback",
        page_count=96,
        has_illustrations=True,
        cover_image=None
    )

    monkeypatch.setattr(catalog.catalog_service, "search_bibliographic_records", lambda **kwargs: ([mock_record], 1))

    # Mock DB query
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_distinct = mock_filter.distinct.return_value
    mock_order = mock_distinct.order_by.return_value
    
    # Mock database results for counts, holds, and items
    mock_db.query.return_value.filter.return_value.group_by.return_value.all.side_effect = [
        [SimpleNamespace(bibliographic_record_id=42, total=1, available=1)],  # counts_rows
        [SimpleNamespace(bibliographic_record_id=42, holds=0)]                 # holds_rows
    ]
    # For all_items query, return list of items
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        SimpleNamespace(bibliographic_record_id=42, item_id="0001", status="available", shelf_location="Shelf A", call_number="C-EXU")
    ]

    result = catalog.search_bibliographic_records(limit=50, offset=0, db=mock_db)

    assert result.total == 1
    assert result.limit == 50
    assert len(result.items) == 1
    assert result.items[0]["title"] == "Le Petit Prince"
    assert result.items[0]["first_item_id"] == "0001"


def test_get_bibliographic_record_endpoint(monkeypatch):
    """Test get_bibliographic_record endpoint."""
    monkeypatch.setattr(catalog.catalog_service, "get_bibliographic_record_with_counts", lambda db, rid: SimpleNamespace(
        id=rid, title="Test", authors='["A"]', medium_type="Livre", total_items=3
    ))
    
    mock_db = MagicMock()

    result = catalog.get_bibliographic_record(42, db=mock_db)
    assert result.id == 42
    assert result.total_items == 3


def test_export_catalog_endpoint(monkeypatch):
    """Test export_catalog endpoint."""
    # Mock ExportService
    mock_export_service = MagicMock()
    mock_export_service.export_catalog_to_csv.return_value = ("title,barcode\nLe Petit Prince,0001\n", 1, 1)

    monkeypatch.setattr(catalog, "ExportService", lambda db: mock_export_service)

    result = catalog.export_catalog(db=object())
    assert result.status_code == 200
    assert result.headers["X-Record-Count"] == "1"
    assert result.headers["X-Item-Count"] == "1"
    assert b"Le Petit Prince" in result.body


def test_update_record_endpoint(monkeypatch):
    """Test update_record_endpoint."""
    called = []
    monkeypatch.setattr(catalog.catalog_service, "update_record", lambda db, record_id, update_data: called.append((record_id, update_data)) or SimpleNamespace(id=record_id, **update_data))

    result = catalog.update_record_endpoint(42, {"title": "New Title"}, db=object())
    assert called == [(42, {"title": "New Title"})]
    assert result.title == "New Title"


def test_update_item_endpoint(monkeypatch):
    """Test update_item_endpoint."""
    called = []
    monkeypatch.setattr(catalog.catalog_service, "update_item", lambda db, item_id, update_data: called.append((item_id, update_data)) or SimpleNamespace(item_id=item_id, **update_data))

    result = catalog.update_item_endpoint("0001", {"condition": "damaged"}, db=object())
    assert called == [("0001", {"condition": "damaged"})]
    assert result.condition == "damaged"


def test_delete_item_endpoint(monkeypatch):
    """Test delete_item_endpoint."""
    called = []
    monkeypatch.setattr(catalog.catalog_service, "delete_item", lambda db, item_id: called.append(item_id))

    result = catalog.delete_item_endpoint("0001", db=object())
    assert result.status_code == 204
    assert called == ["0001"]


def test_delete_bibliographic_record_endpoint(monkeypatch):
    """Test delete_bibliographic_record endpoint."""
    called = []
    monkeypatch.setattr(catalog.catalog_service, "bulk_delete_records", lambda db, ids: called.extend(ids))

    result = catalog.delete_bibliographic_record(42, db=object())
    assert result is None
    assert called == [42]


def test_update_record_endpoint_error_handling(monkeypatch):
    """Test update_record_endpoint converts service exceptions to HTTPException."""
    from fastapi import HTTPException

    def mock_update_fail(*args, **kwargs):
        raise ValueError("Database record lock failed")

    monkeypatch.setattr(catalog.catalog_service, "update_record", mock_update_fail)

    with pytest.raises(HTTPException) as exc_info:
        catalog.update_record_endpoint(42, {"title": "New Title"}, db=object())

    assert exc_info.value.status_code == 500
    assert "Update record failed" in exc_info.value.detail


def test_update_item_endpoint_error_handling(monkeypatch):
    """Test update_item_endpoint converts service exceptions to HTTPException."""
    from fastapi import HTTPException

    def mock_update_fail(*args, **kwargs):
        raise ValueError("Barcode conflict detected")

    monkeypatch.setattr(catalog.catalog_service, "update_item", mock_update_fail)

    with pytest.raises(HTTPException) as exc_info:
        catalog.update_item_endpoint("0001", {"condition": "damaged"}, db=object())

    assert exc_info.value.status_code == 500
    assert "Update item failed" in exc_info.value.detail

