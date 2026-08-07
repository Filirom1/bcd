"""Unit tests for catalog service."""

import json
from unittest.mock import patch

import pytest

from src.bcd_api.core.exceptions import (
    BiblographicRecordNotFoundException,
    ConflictError,
    NotFoundError,
)
from src.bcd_api.schemas.bibliographic_record import BiblographicRecordCreate
from src.bcd_api.schemas.item import ItemCreate
from src.bcd_api.services import catalog_service


class TestCreateBibliographicRecord:
    """Test bibliographic record creation."""

    def test_create_record_without_bnf_lookup(self, db_session):
        """Test creating record without BNF API lookup."""
        record_data = BiblographicRecordCreate(
            title="Test Book",
            authors=["Smith, John"],
            isbn="9781234567890",
            publisher="Test Publisher",
            publication_year=2024,
        )

        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=False
        )

        assert result.title == "Test Book"
        assert result.isbn == "isbn:9781234567890"
        assert result.publisher == "Test Publisher"
        assert result.publication_year == 2024
        # Authors should be JSON string
        assert isinstance(result.authors, str)
        authors_list = json.loads(result.authors)
        assert authors_list == ["Smith, John"]

    @patch("src.bcd_api.services.external.bnf.search_by_isbn")
    def test_create_record_with_bnf_lookup_success(self, mock_search, db_session):
        """Test creating record with successful BNF lookup."""
        # Mock BNF response
        mock_search.return_value = {
            "title": "BNF Title",
            "authors": ["Author, BNF"],
            "publisher": "BNF Publisher",
            "publication_year": 2023,
            "language": "fre",
            "page_count": 100,
        }

        record_data = BiblographicRecordCreate(
            title="Temp Title",  # Will be overridden by BNF
            isbn="9782800687346",
        )

        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=True
        )

        # Should have BNF data
        assert result.title == "BNF Title"
        assert result.publisher == "BNF Publisher"
        assert result.language == "fre"
        assert result.page_count == 100

    @patch("src.bcd_api.services.catalog.commands._download_cover", return_value=None)
    @patch("src.bcd_api.services.external.bnf.search_by_isbn")
    def test_create_record_bnf_lookup_failed(self, mock_search, mock_download_cover, db_session):
        """Test creating record when BNF lookup fails."""
        mock_search.return_value = None  # Not found

        record_data = BiblographicRecordCreate(
            title="Manual Entry",
            isbn="9999999999999",
            authors=["Manual, Author"],
        )

        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=True
        )

        # Should fall back to manual data
        assert result.title == "Manual Entry"
        authors = json.loads(result.authors)
        assert authors == ["Manual, Author"]

    def test_create_record_duplicate_isbn(self, db_session):
        """Test creating record with duplicate ISBN."""
        # Create first record
        first_data = BiblographicRecordCreate(
            title="First Book",
            isbn="9781111111111",
        )
        catalog_service.create_bibliographic_record(db_session, first_data, isbn_lookup=False)

        # Try to create duplicate
        duplicate_data = BiblographicRecordCreate(
            title="Duplicate Book",
            isbn="9781111111111",
        )

        with pytest.raises(ConflictError) as exc:
            catalog_service.create_bibliographic_record(
                db_session, duplicate_data, isbn_lookup=False
            )
        assert "already exists" in str(exc.value.detail).lower()


class TestGetBibliographicRecord:
    """Test retrieving bibliographic records."""

    def test_get_record_success(self, db_session):
        """Test getting existing record."""
        # Create a record
        record_data = BiblographicRecordCreate(
            title="Test Book",
            isbn="9781234567890",
        )
        created = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=False
        )

        # Retrieve it
        result = catalog_service.get_bibliographic_record(db_session, created.id)

        assert result.id == created.id
        assert result.title == "Test Book"

    def test_get_record_not_found(self, db_session):
        """Test getting non-existent record."""
        with pytest.raises(NotFoundError) as exc:
            catalog_service.get_bibliographic_record(db_session, 99999)
        assert "not found" in str(exc.value.detail).lower()


class TestSearchBibliographicRecords:
    """Test bibliographic record search."""

    def test_search_by_title(self, db_session):
        """Test searching by title."""
        # Create test records
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Harry Potter", isbn="111"),
            isbn_lookup=False,
        )
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Lord of the Rings", isbn="222"),
            isbn_lookup=False,
        )

        # Search
        results, total = catalog_service.search_bibliographic_records(
            db_session, title="Potter"
        )

        assert total == 1
        assert results[0].title == "Harry Potter"

    def test_search_by_author(self, db_session):
        """Test searching by author."""
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Book 1", authors=["Rowling, J.K."], isbn="111"
            ),
            isbn_lookup=False,
        )
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Book 2", authors=["Tolkien, J.R.R."], isbn="222"
            ),
            isbn_lookup=False,
        )

        results, total = catalog_service.search_bibliographic_records(
            db_session, author="Rowling"
        )

        assert total == 1
        assert "Rowling" in results[0].authors

    def test_search_by_isbn(self, db_session):
        """Test searching by ISBN."""
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test", isbn="9781234567890"),
            isbn_lookup=False,
        )

        results, total = catalog_service.search_bibliographic_records(
            db_session, isbn="isbn:9781234567890"
        )

        assert total == 1
        assert results[0].isbn == "isbn:9781234567890"

    def test_search_general_query(self, db_session):
        """Test general search query."""
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Python Programming", authors=["Lutz, Mark"], isbn="111"
            ),
            isbn_lookup=False,
        )

        # Search in title
        _, total = catalog_service.search_bibliographic_records(db_session, q="Python")
        assert total == 1

        # Search in authors
        _, total = catalog_service.search_bibliographic_records(db_session, q="Lutz")
        assert total == 1

    def test_search_pagination(self, db_session):
        """Test pagination."""
        # Create 5 records
        for i in range(5):
            catalog_service.create_bibliographic_record(
                db_session,
                BiblographicRecordCreate(title=f"Book {i}", isbn=f"11{i}"),
                isbn_lookup=False,
            )

        # Get first page
        results, total = catalog_service.search_bibliographic_records(
            db_session, limit=2, offset=0
        )
        assert len(results) == 2
        assert total == 5

        # Get second page
        results, total = catalog_service.search_bibliographic_records(
            db_session, limit=2, offset=2
        )
        assert len(results) == 2
        assert total == 5


class TestCreateItem:
    """Test item (copy) creation."""

    def test_create_item_success(self, db_session):
        """Test creating item successfully."""
        # Create bibliographic record first
        record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="111"),
            isbn_lookup=False,
        )

        # Create item
        item_data = ItemCreate(
            item_id="ITEM001",
            bibliographic_record_id=record.id,
            call_number="800.000",
            loanable=True,
        )

        result = catalog_service.create_item(db_session, item_data)

        assert result.item_id == "ITEM001"
        assert result.bibliographic_record_id == record.id
        assert result.call_number == "800.000"
        assert result.loanable is True
        assert result.status == "available"

    def test_create_item_bibliographic_not_found(self, db_session):
        """Test creating item for non-existent bibliographic record."""
        item_data = ItemCreate(
            item_id="ITEM001",
            bibliographic_record_id=99999,
        )

        with pytest.raises(BiblographicRecordNotFoundException) as exc:
            catalog_service.create_item(db_session, item_data)
        assert "not found" in str(exc.value.detail).lower()

    def test_create_item_duplicate_id(self, db_session):
        """Test creating item with duplicate ID."""
        # Create bibliographic record
        record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="111"),
            isbn_lookup=False,
        )

        # Create first item
        item_data = ItemCreate(item_id="ITEM001", bibliographic_record_id=record.id)
        catalog_service.create_item(db_session, item_data)

        # Try duplicate
        duplicate_data = ItemCreate(item_id="ITEM001", bibliographic_record_id=record.id)

        with pytest.raises(ConflictError) as exc:
            catalog_service.create_item(db_session, duplicate_data)
        assert "already exists" in str(exc.value.detail).lower()


class TestGetItem:
    """Test item retrieval."""

    def test_get_item_success(self, db_session):
        """Test getting existing item."""
        # Create record and item
        record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="111"),
            isbn_lookup=False,
        )
        item_data = ItemCreate(item_id="ITEM001", bibliographic_record_id=record.id)
        catalog_service.create_item(db_session, item_data)

        # Retrieve item
        result = catalog_service.get_item(db_session, "ITEM001")

        assert result.item_id == "ITEM001"

    def test_get_item_not_found(self, db_session):
        """Test getting non-existent item."""
        with pytest.raises(NotFoundError) as exc:
            catalog_service.get_item(db_session, "NONEXISTENT")
        assert "not found" in str(exc.value.detail).lower()


class TestGetItemsForBibliographicRecord:
    """Test getting all items for a bibliographic record."""

    def test_get_items_success(self, db_session):
        """Test getting items for a record."""
        # Create record
        record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="111"),
            isbn_lookup=False,
        )

        # Create multiple items
        for i in range(3):
            item_data = ItemCreate(
                item_id=f"ITEM00{i}",
                bibliographic_record_id=record.id,
            )
            catalog_service.create_item(db_session, item_data)

        # Get all items (returns dictionaries, not Item objects)
        items = catalog_service.get_items_for_bibliographic_record(db_session, record.id)

        assert len(items) == 3
        # Verify all items are present by checking item_id
        item_ids = {item["item_id"] for item in items}
        assert item_ids == {"ITEM000", "ITEM001", "ITEM002"}

    def test_get_items_empty(self, db_session):
        """Test getting items when none exist."""
        record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="111"),
            isbn_lookup=False,
        )

        items = catalog_service.get_items_for_bibliographic_record(db_session, record.id)

        assert len(items) == 0
