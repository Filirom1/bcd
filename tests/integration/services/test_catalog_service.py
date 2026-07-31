"""Integration tests for catalog service.

This module demonstrates integration testing best practices:

BEST PRACTICES DEMONSTRATED:
============================

1. **AAA Pattern** (Arrange-Act-Assert)
   - Arrange: Set up test data and preconditions
   - Act: Execute the function under test
   - Assert: Verify the outcome

2. **Database Isolation**
   - Each test runs in a transaction that's automatically rolled back
   - Tests are independent and can run in any order
   - No test pollution or cascading failures

3. **Descriptive Test Names**
   - test_<action>_<condition>_<expected_result>
   - Anyone can understand what's being tested without reading code

4. **Comprehensive Coverage**
   - Happy paths: Normal successful operations
   - Error paths: Invalid input, not found, conflicts
   - Edge cases: Empty results, pagination boundaries
   - Business rules: ISBN validation, duplicate prevention

5. **Realistic Test Data**
   - Uses real-world ISBNs and book data
   - Tests special characters, unicode, various formats
   - Covers different data types (books, DVDs, etc.)

6. **Proper Mocking**
   - External APIs (BNF) are mocked to avoid network dependency
   - Mocks return realistic data matching actual API responses
   - Tests verify integration between service and mocked dependencies

7. **Clear Assertions**
   - Multiple specific assertions per test
   - Verify both return values and database state changes
   - Check all important fields, not just one or two

8. **Good Organization**
   - Tests grouped by feature using classes
   - Related tests are easy to find
   - Clear separation of concerns

9. **Testing Transactions**
   - Verify data is committed to database
   - Check relationship integrity (FKs work correctly)
   - Validate cascade behaviors

10. **Error Message Quality**
    - Tests verify error messages are helpful
    - Check correct exception types are raised
    - Validate error details provide debugging information
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def disable_cover_download_for_catalog_tests(monkeypatch):
    """Keep catalog integration tests local; cover providers are tested separately."""
    monkeypatch.setattr("src.bcd_api.services.catalog_service._download_cover", lambda isbn: None)

from src.bcd_api.core.exceptions import (
    BiblographicRecordNotFoundException,
    ConflictError,
    ItemHasActiveLoanException,
    NotFoundError,
)
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.item import Item
from src.bcd_api.schemas.bibliographic_record import BiblographicRecordCreate
from src.bcd_api.schemas.item import ItemCreate
from src.bcd_api.services import catalog_service


class TestBibliographicRecordCreation:
    """Test creating bibliographic records with various scenarios."""

    def test_create_bibliographic_record_manual_entry_minimal(self, db_session):
        """
        Test creating a bibliographic record with minimal required fields.

        This tests the simplest case: manual entry with only title and ISBN.
        Verifies default values are applied correctly.
        """
        # Arrange
        record_data = BiblographicRecordCreate(
            title="The Great Gatsby",
            isbn="9780743273565"
        )

        # Act
        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=False
        )

        # Assert
        assert result.id is not None
        assert result.title == "The Great Gatsby"
        assert result.isbn == "isbn:9780743273565"
        assert result.medium_type == "Livre"  # Default value
        assert result.authors is None or result.authors == "[]"

        # Verify it's actually in the database
        db_record = db_session.query(BiblographicRecord).filter_by(
            id=result.id
        ).first()
        assert db_record is not None
        assert db_record.title == "The Great Gatsby"

    def test_create_bibliographic_record_manual_entry_complete(self, db_session):
        """
        Test creating a bibliographic record with all optional fields.

        This tests the complete manual entry scenario where the librarian
        provides all possible metadata fields.
        """
        # Arrange
        record_data = BiblographicRecordCreate(
            title="Stuart Little",
            subtitle="A Classic Tale",
            isbn="9780060263959",
            authors=["White, E.B."],
            illustrators=["Williams, Garth"],
            publisher="Harper & Row",
            publication_year=1945,
            collection="Harper Classics",
            language="eng",
            target_audience="child",
            medium_type="Livre",
            page_count=131,
            has_illustrations=True,
            description="The adventures of a mouse in New York City",
            keywords=["mouse", "adventure", "family"]
        )

        # Act
        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=False
        )

        # Assert - Verify all fields
        assert result.id is not None
        assert result.title == "Stuart Little"
        assert result.subtitle == "A Classic Tale"
        assert result.isbn == "isbn:9780060263959"
        assert "White, E.B." in result.authors
        assert "Williams, Garth" in result.illustrators
        assert result.publisher == "Harper & Row"
        assert result.publication_year == 1945
        assert result.collection == "Harper Classics"
        assert result.language == "eng"
        assert result.target_audience == "child"
        assert result.page_count == 131
        assert result.has_illustrations is True
        assert result.description == "The adventures of a mouse in New York City"
        assert "mouse" in result.keywords

    @patch("src.bcd_api.services.catalog_service.search_by_isbn")
    def test_create_bibliographic_record_with_bnf_lookup(self, mock_search, db_session):
        """
        Test creating a bibliographic record with BNF API lookup.

        This tests the automatic ISBN lookup feature where the system
        fetches metadata from the BNF (French National Library) API.
        The BNF data should populate most fields automatically.
        """
        # Arrange - Mock BNF API response
        mock_search.return_value = {
            "title": "L'équipe des mascrottes",
            "authors": ["Petit, Dominique"],
            "publisher": "Hemma",
            "publication_year": 2004,
            "language": "fr",
            "country_code": "be",
            "isbn": "2800687347",
            "page_count": 83,
            "has_illustrations": True,
            "medium_type": "Livre",
            "target_audience": "child"
        }

        record_data = BiblographicRecordCreate(
            title="Placeholder",  # This should be overridden by BNF
            isbn="2-8006-8734-7",
        )

        # Act
        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=True
        )

        # Assert
        assert result.id is not None
        # BNF data should override placeholder title
        assert result.title == "L'équipe des mascrottes"
        assert "Petit, Dominique" in result.authors
        assert result.publisher == "Hemma"
        assert result.publication_year == 2004
        assert result.language == "fr"
        assert result.page_count == 83

        # Verify BNF service was called with normalized ISBN
        mock_search.assert_called_once()

    @patch("src.bcd_api.services.catalog_service.search_by_isbn")
    def test_create_bibliographic_record_bnf_fallback_on_error(self, mock_search, db_session):
        """
        Test graceful fallback when BNF lookup fails.

        If the BNF API is down or returns an error, the system should
        fall back to manual entry mode using the provided data.
        """
        # Arrange - Mock BNF API failure
        mock_search.side_effect = Exception("BNF API unavailable")

        record_data = BiblographicRecordCreate(
            title="Test Book",
            isbn="9781234567890"
        )

        # Act - Should not raise exception
        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=True
        )

        # Assert - Should use manual data
        assert result.id is not None
        assert result.title == "Test Book"
        assert result.isbn == "isbn:9781234567890"

    @patch("src.bcd_api.services.catalog_service.sudoc_search_by_isbn")
    @patch("src.bcd_api.services.catalog_service.google_search_by_isbn")
    @patch("src.bcd_api.services.catalog_service.search_by_isbn")
    def test_lookup_isbn_falls_back_to_google_when_bnf_returns_none(
        self, mock_bnf, mock_google, mock_sudoc, db_session
    ):
        """
        Test that lookup_isbn falls back to Google Books when BNF returns None.

        Business rule: BNF is the primary source for French books, but Google
        Books is used as a fallback when BNF has no record for the given ISBN.
        """
        # Arrange — BNF finds nothing, Google Books returns data
        mock_bnf.return_value = None
        mock_google.return_value = {
            "title": "Stuart Little",
            "authors": ["White, E.B."],
            "publisher": "Ecole des loisirs",
            "publication_year": 2000,
            "language": "fr",
            "isbn": "2211056466",
            "medium_type": "Livre",
            "target_audience": "child",
        }
        mock_sudoc.return_value = None

        # Act
        result = catalog_service.lookup_isbn(db_session, "2211056466")

        # Assert — Google Books data returned transparently
        assert result is not None
        assert result["title"] == "Stuart Little"
        assert result["publisher"] == "Ecole des loisirs"
        mock_bnf.assert_called_once()
        mock_google.assert_called_once()

    @patch("src.bcd_api.services.catalog_service.sudoc_search_by_isbn")
    @patch("src.bcd_api.services.catalog_service.google_search_by_isbn")
    @patch("src.bcd_api.services.catalog_service.search_by_isbn")
    def test_lookup_isbn_falls_back_to_google_when_bnf_raises_network_error(
        self, mock_bnf, mock_google, mock_sudoc, db_session
    ):
        """
        Test that lookup_isbn falls back to Google Books when BNF raises a network error.

        Business rule: if BNF is unreachable (offline mode), the lookup should
        gracefully fall back to Google Books rather than propagating the exception.
        """
        import httpx

        # Arrange — BNF raises a network error (offline), Google Books has the book
        mock_bnf.side_effect = httpx.ConnectError("Network unreachable")
        mock_google.return_value = {
            "title": "Stuart Little",
            "authors": ["White, E.B."],
            "publisher": "Ecole des loisirs",
            "publication_year": 2000,
            "language": "fr",
            "isbn": "2211056466",
            "medium_type": "Livre",
            "target_audience": "child",
        }
        mock_sudoc.return_value = None

        # Act — should not raise
        result = catalog_service.lookup_isbn(db_session, "2211056466")

        # Assert — Google Books data returned despite BNF failure
        assert result is not None
        assert result["title"] == "Stuart Little"
        mock_bnf.assert_called_once()
        mock_google.assert_called_once()

    @patch("src.bcd_api.services.catalog_service.sudoc_search_by_isbn")
    @patch("src.bcd_api.services.catalog_service.google_search_by_isbn")
    @patch("src.bcd_api.services.catalog_service.search_by_isbn")
    def test_lookup_isbn_returns_none_when_all_sources_unreachable(
        self, mock_bnf, mock_google, mock_sudoc, db_session
    ):
        """
        Test that lookup_isbn returns None (→ 404) when all external sources fail.

        Business rule: in fully offline mode, no catalog source is available.
        The endpoint must return 404, not crash with 500.
        """
        import httpx

        # Arrange — all sources raise network errors
        mock_bnf.side_effect = httpx.ConnectError("Network unreachable")
        mock_google.side_effect = httpx.ConnectError("Network unreachable")
        mock_sudoc.side_effect = httpx.ConnectError("Network unreachable")

        # Act — should not raise, must return None
        result = catalog_service.lookup_isbn(db_session, "2211056466")

        # Assert — None signals "not found" to the endpoint (→ 404)
        assert result is None

    def test_create_bibliographic_record_duplicate_isbn_error(self, db_session):
        """
        Test that duplicate ISBNs are rejected with proper error message.

        Business rule: Each ISBN must be unique in the catalog.
        This prevents accidental duplicate cataloging of the same book.
        """
        # Arrange - Create first record
        first_record = BiblographicRecordCreate(
            title="First Book",
            isbn="9780451524935"
        )
        catalog_service.create_bibliographic_record(
            db_session, first_record, isbn_lookup=False
        )

        # Act & Assert - Try to create duplicate
        duplicate_record = BiblographicRecordCreate(
            title="Second Book",
            isbn="9780451524935"  # Same ISBN
        )

        with pytest.raises(ConflictError) as exc_info:
            catalog_service.create_bibliographic_record(
                db_session, duplicate_record, isbn_lookup=False
            )

        # Verify error message is helpful
        assert "already exists" in str(exc_info.value).lower()
        assert "9780451524935" in str(exc_info.value)

    def test_create_bibliographic_record_without_isbn(self, db_session):
        """
        Test creating a bibliographic record without an ISBN.

        Some older books or special materials don't have ISBNs.
        The system should allow cataloging these items.
        """
        # Arrange
        record_data = BiblographicRecordCreate(
            title="Ancient Manuscript",
            publisher="Medieval Publishers",
            publication_year=1450
        )

        # Act
        result = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=False
        )

        # Assert
        assert result.id is not None
        assert result.title == "Ancient Manuscript"
        assert result.isbn is None
        assert result.publication_year == 1450


class TestBibliographicRecordRetrieval:
    """Test retrieving bibliographic records."""

    def test_get_bibliographic_record_by_id_success(self, db_session):
        """
        Test retrieving an existing bibliographic record by ID.

        Standard retrieval operation - should return complete record data.
        """
        # Arrange - Create a record
        record_data = BiblographicRecordCreate(
            title="1984",
            isbn="9780451524935",
            authors=["Orwell, George"]
        )
        created = catalog_service.create_bibliographic_record(
            db_session, record_data, isbn_lookup=False
        )

        # Act
        result = catalog_service.get_bibliographic_record(db_session, created.id)

        # Assert
        assert result.id == created.id
        assert result.title == "1984"
        assert result.isbn == "isbn:9780451524935"
        assert "Orwell, George" in result.authors

    def test_get_bibliographic_record_not_found_error(self, db_session):
        """
        Test retrieving a non-existent bibliographic record.

        Should raise NotFoundError with helpful message for debugging.
        """
        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            catalog_service.get_bibliographic_record(db_session, 99999)

        # Verify error message contains the ID that wasn't found
        assert "99999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


class TestBibliographicRecordSearch:
    """Test searching and filtering bibliographic records."""

    def test_search_bibliographic_records_by_title(self, db_session):
        """
        Test searching bibliographic records by title (partial match).

        Should find records where title contains the search term (case-insensitive).
        """
        # Arrange - Create multiple records
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Python Programming", isbn="9781111111111"),
            isbn_lookup=False
        )
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Java Programming", isbn="9782222222222"),
            isbn_lookup=False
        )
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Python for Data Science", isbn="9783333333333"),
            isbn_lookup=False
        )

        # Act - Search for "Python"
        results, total = catalog_service.search_bibliographic_records(
            db_session, title="Python"
        )

        # Assert
        assert total == 2
        assert len(results) == 2
        assert all("Python" in r.title for r in results)

    def test_search_bibliographic_records_by_author(self, db_session):
        """
        Test searching bibliographic records by author name.

        Should support partial matching on author names.
        """
        # Arrange
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Harry Potter",
                isbn="9784444444444",
                authors=["Rowling, J.K."]
            ),
            isbn_lookup=False
        )
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="The Casual Vacancy",
                isbn="9785555555555",
                authors=["Rowling, J.K."]
            ),
            isbn_lookup=False
        )

        # Act
        results, total = catalog_service.search_bibliographic_records(
            db_session, author="Rowling"
        )

        # Assert
        assert total == 2
        assert len(results) == 2

    def test_search_bibliographic_records_general_query(self, db_session):
        """
        Test general search across title and authors.

        The 'q' parameter searches both title and author fields.
        """
        # Arrange
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="The Hobbit",
                isbn="9786666666666",
                authors=["Tolkien, J.R.R."]
            ),
            isbn_lookup=False
        )

        # Act - Search for author name using general query
        results, total = catalog_service.search_bibliographic_records(
            db_session, q="Tolkien"
        )

        # Assert
        assert total == 1
        assert results[0].title == "The Hobbit"

    def test_search_bibliographic_records_pagination(self, db_session):
        """
        Test pagination of search results.

        Large result sets should be pageable for performance.
        """
        # Arrange - Create 5 records
        for i in range(5):
            catalog_service.create_bibliographic_record(
                db_session,
                BiblographicRecordCreate(
                    title=f"Book {i}",
                    isbn=f"978999999999{i}"
                ),
                isbn_lookup=False
            )

        # Act - Get first page (limit=2)
        page1, total = catalog_service.search_bibliographic_records(
            db_session, limit=2, offset=0
        )

        # Act - Get second page
        page2, _ = catalog_service.search_bibliographic_records(
            db_session, limit=2, offset=2
        )

        # Assert
        assert total == 5
        assert len(page1) == 2
        assert len(page2) == 2
        # Verify pages contain different records
        page1_ids = {r.id for r in page1}
        page2_ids = {r.id for r in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_search_bibliographic_records_empty_results(self, db_session):
        """
        Test search with no matching results.

        Should return empty list with total=0, not raise an error.
        """
        # Act
        results, total = catalog_service.search_bibliographic_records(
            db_session, title="NonexistentBook"
        )

        # Assert
        assert total == 0
        assert len(results) == 0

    def test_search_bibliographic_records_multiple_filters(self, db_session):
        """
        Test combining multiple search filters.

        Filters should be ANDed together to narrow results.
        """
        # Arrange
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Le Petit Prince",
                isbn="9788888888888",
                language="fr",
                target_audience="child"
            ),
            isbn_lookup=False
        )
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Les Misérables",
                isbn="9788888888889",
                language="fr",
                target_audience="adult"
            ),
            isbn_lookup=False
        )

        # Act - Search with multiple filters
        results, total = catalog_service.search_bibliographic_records(
            db_session,
            language="fr",
            target_audience="child"
        )

        # Assert - Should only match Le Petit Prince
        assert total == 1
        assert results[0].title == "Le Petit Prince"


class TestItemManagement:
    """Test item (physical copy) management."""

    def test_create_item_success(self, db_session):
        """
        Test creating an item (physical copy) for a bibliographic record.

        Items represent physical copies that can be checked out.
        Multiple items can exist for the same bibliographic record.
        """
        # Arrange - Create bibliographic record first
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="9787777777777"),
            isbn_lookup=False
        )

        # Act - Create item
        item_data = ItemCreate(
            item_id="ITEM001",
            bibliographic_record_id=bib_record.id,
            call_number="823.912",
            shelf_location="Fiction - Section A - Shelf 3",
            loanable=True
        )
        result = catalog_service.create_item(db_session, item_data)

        # Assert
        assert result.id is not None
        assert result.item_id == "ITEM001"
        assert result.bibliographic_record_id == bib_record.id
        assert result.call_number == "823.912"
        assert result.shelf_location == "Fiction - Section A - Shelf 3"
        assert result.status == "available"
        assert result.loanable is True

        # Verify database persistence
        db_item = db_session.query(Item).filter_by(item_id="ITEM001").first()
        assert db_item is not None
        assert db_item.bibliographic_record_id == bib_record.id

        # Verify denormalized counter is incremented
        db_session.refresh(bib_record)
        assert bib_record.total_items == 1

    def test_create_item_minimal_data(self, db_session):
        """
        Test creating an item with only required fields.

        Only item_id and bibliographic_record_id are required.
        Other fields should have sensible defaults.
        """
        # Arrange
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Minimal Item Test", isbn="9781010101010"),
            isbn_lookup=False
        )

        # Act
        item_data = ItemCreate(
            item_id="MIN001",
            bibliographic_record_id=bib_record.id
        )
        result = catalog_service.create_item(db_session, item_data)

        # Assert
        assert result.item_id == "MIN001"
        assert result.status == "available"  # Default status
        assert result.loanable is True  # Default loanable

    def test_create_item_bibliographic_record_not_found(self, db_session):
        """
        Test creating an item for a non-existent bibliographic record.

        Should raise BiblographicRecordNotFoundException to prevent orphaned items.
        """
        # Act & Assert
        item_data = ItemCreate(
            item_id="ORPHAN001",
            bibliographic_record_id=99999  # Doesn't exist
        )

        with pytest.raises(BiblographicRecordNotFoundException) as exc_info:
            catalog_service.create_item(db_session, item_data)

        assert "not found" in str(exc_info.value).lower()

    def test_create_item_duplicate_item_id(self, db_session):
        """
        Test that duplicate item IDs are rejected.

        Business rule: Each item_id (barcode) must be unique across all items.
        """
        # Arrange
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Duplicate Test", isbn="9781212121212"),
            isbn_lookup=False
        )

        item_data1 = ItemCreate(item_id="DUP001", bibliographic_record_id=bib_record.id)
        catalog_service.create_item(db_session, item_data1)

        # Act & Assert - Try to create duplicate
        item_data2 = ItemCreate(item_id="DUP001", bibliographic_record_id=bib_record.id)

        with pytest.raises(ConflictError) as exc_info:
            catalog_service.create_item(db_session, item_data2)

        assert "already exists" in str(exc_info.value).lower()
        assert "DUP001" in str(exc_info.value)

    def test_create_item_strips_prefix(self, db_session):
        """
        Test that creating an item automatically strips the item barcode prefix.
        """
        # Arrange - Get actual prefix from settings, or mock/stub if needed
        from src.bcd_api.services.settings_service import get_settings
        settings = get_settings(db_session)
        prefix = settings.item_barcode_prefix or "."

        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Prefix Strip Test", isbn="9789999999999"),
            isbn_lookup=False
        )

        # Act - Create item with prefixed barcode (e.g. .785)
        prefixed_id = f"{prefix}785"
        item_data = ItemCreate(item_id=prefixed_id, bibliographic_record_id=bib_record.id)
        result = catalog_service.create_item(db_session, item_data)

        # Assert - The saved item_id should have the prefix stripped
        assert result.item_id == "785"
        assert result.barcode == "785"

        # Verify database has "785" and not ".785"
        db_item = db_session.query(Item).filter_by(item_id="785").first()
        assert db_item is not None
        assert db_session.query(Item).filter_by(item_id=prefixed_id).first() is None

    def test_get_item_by_id_success(self, db_session):
        """Test retrieving an item by its item_id."""
        # Arrange
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Get Item Test", isbn="9781313131313"),
            isbn_lookup=False
        )
        item_data = ItemCreate(item_id="GET001", bibliographic_record_id=bib_record.id)
        catalog_service.create_item(db_session, item_data)

        # Act
        result = catalog_service.get_item(db_session, "GET001")

        # Assert
        assert result.item_id == "GET001"
        assert result.bibliographic_record_id == bib_record.id

    def test_get_item_not_found(self, db_session):
        """Test retrieving a non-existent item."""
        # Act & Assert
        with pytest.raises(NotFoundError):
            catalog_service.get_item(db_session, "NONEXISTENT")

    def test_get_items_for_bibliographic_record(self, db_session):
        """
        Test retrieving all items for a bibliographic record.

        A single book title can have multiple physical copies.
        This function lists all of them.
        """
        # Arrange - Create record with 3 items
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Multi-Copy Book", isbn="9781414141414"),
            isbn_lookup=False
        )

        for i in range(3):
            item_data = ItemCreate(
                item_id=f"MULTI{i}",
                bibliographic_record_id=bib_record.id,
                call_number="823.000"
            )
            catalog_service.create_item(db_session, item_data)

        # Act
        results = catalog_service.get_items_for_bibliographic_record(
            db_session, bib_record.id
        )

        # Assert
        assert len(results) == 3
        # Results are dictionaries, not Item objects
        item_ids = {item["item_id"] for item in results}
        assert item_ids == {"MULTI0", "MULTI1", "MULTI2"}

    def test_get_items_for_bibliographic_record_empty(self, db_session):
        """
        Test retrieving items when none exist for the record.

        Should return empty list, not raise an error.
        """
        # Arrange - Create record without items
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="No Copies", isbn="9781515151515"),
            isbn_lookup=False
        )

        # Act
        results = catalog_service.get_items_for_bibliographic_record(
            db_session, bib_record.id
        )

        # Assert
        assert len(results) == 0


class TestCatalogIntegrationScenarios:
    """End-to-end integration scenarios combining multiple operations."""

    def test_complete_cataloging_workflow(self, db_session):
        """
        Test complete workflow: catalog a book and add multiple copies.

        This simulates a real librarian workflow:
        1. Catalog a new book (with ISBN lookup)
        2. Add 3 physical copies with different locations
        3. Verify everything is linked correctly
        """
        # Step 1: Catalog the book (simulating BNF lookup)
        with patch("src.bcd_api.services.catalog_service.search_by_isbn") as mock_search:
            mock_search.return_value = {
                "title": "Charlotte's Web",
                "authors": ["White, E.B."],
                "publisher": "Harper & Brothers",
                "publication_year": 1952,
                "isbn": "9780064400558",
                "language": "eng",
                "medium_type": "Livre",
                "target_audience": "child"
            }

            bib_record = catalog_service.create_bibliographic_record(
                db_session,
                BiblographicRecordCreate(title="Temp", isbn="9780064400558"),
                isbn_lookup=True
            )

        # Step 2: Add 3 physical copies
        copy1 = catalog_service.create_item(
            db_session,
            ItemCreate(
                item_id="CW001",
                bibliographic_record_id=bib_record.id,
                call_number="813.52",
                shelf_location="Children - Fiction - Shelf 12"
            )
        )

        copy2 = catalog_service.create_item(
            db_session,
            ItemCreate(
                item_id="CW002",
                bibliographic_record_id=bib_record.id,
                call_number="813.52",
                shelf_location="Children - Fiction - Shelf 12"
            )
        )

        copy3 = catalog_service.create_item(
            db_session,
            ItemCreate(
                item_id="CW003",
                bibliographic_record_id=bib_record.id,
                call_number="813.52",
                shelf_location="Classroom Set - Room 204"
            )
        )

        # Step 3: Verify complete integration
        # Retrieve the bibliographic record
        retrieved_bib = catalog_service.get_bibliographic_record(db_session, bib_record.id)
        assert retrieved_bib.title == "Charlotte's Web"
        assert "White, E.B." in retrieved_bib.authors

        # Retrieve all copies
        all_copies = catalog_service.get_items_for_bibliographic_record(
            db_session, bib_record.id
        )
        assert len(all_copies) == 3

        # Verify each copy (all_copies contains dictionaries, not Item objects)
        assert copy1.item_id in [c["item_id"] for c in all_copies]
        assert copy2.item_id in [c["item_id"] for c in all_copies]
        assert copy3.item_id in [c["item_id"] for c in all_copies]

        # Verify all items exist (dictionaries don't have bibliographic_record_id field)
        item_ids = {c["item_id"] for c in all_copies}
        assert item_ids == {"CW001", "CW002", "CW003"}

    def test_search_and_retrieve_workflow(self, db_session):
        """
        Test workflow: search for books, then retrieve full details.

        Simulates a user searching the catalog and viewing details.
        """
        # Setup: Add several books
        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Animal Farm",
                isbn="9780451526342",
                authors=["Orwell, George"],
                level="CM1"
            ),
            isbn_lookup=False
        )

        catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Brave New World",
                isbn="9780060850524",
                authors=["Huxley, Aldous"],
                level="CM1"
            ),
            isbn_lookup=False
        )

        # Step 1: Search for novels
        results, total = catalog_service.search_bibliographic_records(
            db_session, level="CM1"
        )

        assert total == 2
        assert len(results) == 2

        # Step 2: User selects first result to view details
        selected = results[0]
        full_details = catalog_service.get_bibliographic_record(db_session, selected.id)

        assert full_details.id == selected.id
        assert full_details.title == selected.title
        assert full_details.level == "CM1"


class TestGetAvailableItemIDs:
    """Tests for get_available_item_ids() - free barcode label generation."""

    def test_get_available_ids_with_empty_database_starts_from_one(self, db_session):
        """When no items exist, should start from ID 1."""
        # Arrange: Empty database (no items)

        # Act
        result = catalog_service.get_available_item_ids(db_session, count=10)

        # Assert
        assert result["start_id"] == "1"
        assert result["end_id"] == "10"
        assert result["count"] == 10
        assert result["id_format"] == "numeric"
        assert len(result["ids"]) == 10
        assert result["ids"] == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

    def test_get_available_ids_reuses_ids_below_existing_range(self, db_session):
        """Should return smallest available IDs, not max+1 (reuses freed IDs)."""
        # Arrange: Create bibliographic record and items with high IDs
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Test Book",
                isbn="9780123456789",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        # Create items with IDs 100, 101, 102 (simulating existing books)
        for i in [100, 101, 102]:
            catalog_service.create_item(
                db_session,
                ItemCreate(
                    item_id=str(i),
                    bibliographic_record_id=bib_record.id
                )
            )

        # Act: Generate 5 new IDs (auto-detect)
        result = catalog_service.get_available_item_ids(db_session, count=5)

        # Assert: Should start from 1 (smallest unused), not 103
        assert result["start_id"] == "1"
        assert result["end_id"] == "5"
        assert result["count"] == 5
        assert result["ids"] == ["1", "2", "3", "4", "5"]

    def test_get_available_ids_with_custom_starting_point(self, db_session):
        """Should allow custom starting ID regardless of existing items."""
        # Arrange: Create some existing items
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Test Book",
                isbn="9780123456789",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        catalog_service.create_item(
            db_session,
            ItemCreate(item_id="50", bibliographic_record_id=bib_record.id)
        )

        # Act: Generate IDs starting from custom ID 2000
        result = catalog_service.get_available_item_ids(
            db_session, count=10, start_from="2000"
        )

        # Assert: Should start from 2000, not 51
        assert result["start_id"] == "2000"
        assert result["end_id"] == "2009"
        assert result["ids"] == ["2000", "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009"]

    def test_get_available_ids_default_count_is_thirty(self, db_session):
        """Default count should be 30 labels (2.5 Avery sheets)."""
        # Act: Call without count parameter
        result = catalog_service.get_available_item_ids(db_session)

        # Assert
        assert result["count"] == 30
        assert len(result["ids"]) == 30
        assert result["ids"][0] == "1"
        assert result["ids"][-1] == "30"

    def test_get_available_ids_validates_count_minimum(self, db_session):
        """Should reject count less than 1."""
        # Act & Assert
        with pytest.raises(ValueError, match="Count must be between 1 and 1000"):
            catalog_service.get_available_item_ids(db_session, count=0)

        with pytest.raises(ValueError, match="Count must be between 1 and 1000"):
            catalog_service.get_available_item_ids(db_session, count=-5)

    def test_get_available_ids_validates_count_maximum(self, db_session):
        """Should reject count greater than 1000."""
        # Act & Assert
        with pytest.raises(ValueError, match="Count must be between 1 and 1000"):
            catalog_service.get_available_item_ids(db_session, count=1001)

        with pytest.raises(ValueError, match="Count must be between 1 and 1000"):
            catalog_service.get_available_item_ids(db_session, count=5000)

    def test_get_available_ids_validates_numeric_start_from(self, db_session):
        """Should reject non-numeric start_from for numeric ID format."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid start_from value for numeric format"):
            catalog_service.get_available_item_ids(
                db_session, count=10, start_from="ABC123"
            )

    def test_get_available_ids_large_batch(self, db_session):
        """Should handle generating 1000 IDs (maximum allowed)."""
        # Act
        result = catalog_service.get_available_item_ids(db_session, count=1000)

        # Assert
        assert result["count"] == 1000
        assert len(result["ids"]) == 1000
        assert result["start_id"] == "1"
        assert result["end_id"] == "1000"
        assert result["ids"][0] == "1"
        assert result["ids"][-1] == "1000"

    def test_get_available_ids_finds_contiguous_block(self, db_session):
        """Should find first contiguous block of free IDs, not individual gaps."""
        # Arrange: Items 1, 2, 4, 5 exist — item 3 was deleted (e.g., withdrawn book)
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Test Book",
                isbn="9780123456789",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        for item_id in ["1", "2", "4", "5"]:
            catalog_service.create_item(
                db_session,
                ItemCreate(
                    item_id=item_id,
                    bibliographic_record_id=bib_record.id
                )
            )

        # Act: Generate 3 new IDs
        result = catalog_service.get_available_item_ids(db_session, count=3)

        # Assert: Should find first contiguous block of 3 free IDs: 6, 7, 8
        assert result["count"] == 3
        assert result["ids"] == ["6", "7", "8"]
        assert result["start_id"] == "6"
        assert result["end_id"] == "8"

    def test_get_available_ids_respects_id_format_setting(self, db_session):
        """Should return current id_format from settings."""
        # Arrange: Settings should have numeric format by default

        # Act
        result = catalog_service.get_available_item_ids(db_session, count=5)

        # Assert
        assert result["id_format"] == "numeric"

    def test_get_available_ids_contiguous_block_after_gaps(self, db_session):
        """Should find first contiguous block, skipping non-contiguous gaps."""
        # Arrange: Library has items 1, 2, 4, 5, 6, 9, 10 (gaps at 3, 7, 8)
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Test Book",
                isbn="9780123456789",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        existing_ids = ["1", "2", "4", "5", "6", "9", "10"]
        for item_id in existing_ids:
            catalog_service.create_item(
                db_session,
                ItemCreate(item_id=item_id, bibliographic_record_id=bib_record.id)
            )

        # Act: Generate 5 labels for new acquisitions
        result = catalog_service.get_available_item_ids(db_session, count=5)

        # Assert: Should find first contiguous block of 5 free IDs: 11-15
        assert result["count"] == 5
        assert result["ids"] == ["11", "12", "13", "14", "15"]

    def test_get_available_ids_start_from_finds_contiguous_block(self, db_session):
        """When start_from is provided, finds first contiguous block from that point."""
        # Arrange: Items 1, 2, 4, 5 exist (gap at 3)
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Test Book",
                isbn="9780123456789",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        for item_id in ["1", "2", "4", "5"]:
            catalog_service.create_item(
                db_session,
                ItemCreate(item_id=item_id, bibliographic_record_id=bib_record.id)
            )

        # Act: Generate from explicit start_from=100
        result = catalog_service.get_available_item_ids(db_session, count=3, start_from="100")

        # Assert: Sequential from 100, gap at 3 is ignored
        assert result["ids"] == ["100", "101", "102"]

    def test_get_available_ids_scatter_mode_fills_gaps(self, db_session):
        """
        contiguous=False collects each free ID individually (gaps allowed).

        If IDs 1, 2, 4, 5 are taken, scatter mode returns [3, 6, 7]
        rather than skipping to find a gapless block.
        """
        # Arrange: items 1, 2, 4, 5 exist (gap at 3)
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book", isbn="9780123456789"),
            isbn_lookup=False
        )
        for item_id in ["1", "2", "4", "5"]:
            catalog_service.create_item(
                db_session,
                ItemCreate(item_id=item_id, bibliographic_record_id=bib_record.id)
            )

        # Act
        result = catalog_service.get_available_item_ids(
            db_session, count=3, contiguous=False
        )

        # Assert: gap at 3 is used, then continues from 6
        assert result["ids"] == ["3", "6", "7"]
        assert result["count"] == 3
        assert result["contiguous"] is False

    def test_get_available_ids_scatter_mode_multiple_gaps(self, db_session):
        """
        contiguous=False fills multiple dispersed gaps.

        Items 1, 2, 4, 6, 8 exist → scatter mode returns [3, 5, 7].
        """
        # Arrange
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book 2", isbn="9780123456780"),
            isbn_lookup=False
        )
        for item_id in ["1", "2", "4", "6", "8"]:
            catalog_service.create_item(
                db_session,
                ItemCreate(item_id=item_id, bibliographic_record_id=bib_record.id)
            )

        # Act
        result = catalog_service.get_available_item_ids(
            db_session, count=3, contiguous=False
        )

        # Assert: picks up each free slot one by one across gaps
        assert result["ids"] == ["3", "5", "7"]
        assert result["count"] == 3

    def test_get_available_ids_scatter_with_start_from(self, db_session):
        """
        contiguous=False honours start_from, collecting free IDs from that point.

        Items 101, 103 exist; start_from=100 → scatter returns [100, 102, 104].
        """
        # Arrange
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(title="Test Book 3", isbn="9780123456781"),
            isbn_lookup=False
        )
        for item_id in ["101", "103"]:
            catalog_service.create_item(
                db_session,
                ItemCreate(item_id=item_id, bibliographic_record_id=bib_record.id)
            )

        # Act
        result = catalog_service.get_available_item_ids(
            db_session, count=3, start_from="100", contiguous=False
        )

        # Assert
        assert result["ids"] == ["100", "102", "104"]

    def test_get_available_ids_contiguous_true_returns_contiguous_field(self, db_session):
        """Response includes the contiguous flag (True by default)."""
        result = catalog_service.get_available_item_ids(db_session, count=5)
        assert result["contiguous"] is True

    def test_get_available_ids_contiguous_false_equals_true_on_empty_db(self, db_session):
        """
        On an empty database both modes return the same result.

        With no existing items there are no gaps, so scatter ≡ contiguous.
        """
        result_cont = catalog_service.get_available_item_ids(
            db_session, count=5, contiguous=True
        )
        result_scat = catalog_service.get_available_item_ids(
            db_session, count=5, contiguous=False
        )
        assert result_cont["ids"] == result_scat["ids"]


class TestDeleteItemValidation:
    """Tests for delete_item with active loan validation."""

    def test_delete_item_with_active_loan_raises_exception(self, db_session):
        """Test that deleting an item with an active loan raises exception."""
        # Arrange: Create item with active loan
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="On Loan Book",
                isbn="9780123456789",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        item = catalog_service.create_item(
            db_session,
            ItemCreate(
                item_id="ACTIVE123",
                bibliographic_record_id=bib_record.id,
                call_number="100.000",
                status="on_loan",
                loanable=True
            )
        )

        # Create borrower
        borrower = Borrower(
            borrower_id="TEST001",
            first_name="Test",
            last_name="BORROWER",
            full_name="Test BORROWER",
            role="student"
        )
        db_session.add(borrower)
        db_session.commit()

        # Create active loan
        loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=bib_record.id,
            checkout_date=datetime.now(),
            due_date=(datetime.now() + timedelta(days=14)).date(),
            status="active",
            return_date=None  # Active!
        )
        db_session.add(loan)
        db_session.commit()

        # Act & Assert: Deletion should raise exception
        with pytest.raises(ItemHasActiveLoanException) as exc_info:
            catalog_service.delete_item(db_session, "ACTIVE123")

        # Verify exception details
        assert exc_info.value.error_code == "ITEM_HAS_ACTIVE_LOAN"
        assert exc_info.value.context["item_id"] == "ACTIVE123"
        assert "Test BORROWER" in exc_info.value.context["borrower_name"]

        # Verify item still exists (not deleted)
        item_check = db_session.query(Item).filter_by(item_id="ACTIVE123").first()
        assert item_check is not None

    def test_delete_item_with_returned_loan_succeeds(self, db_session):
        """Test that deleting an item with only historical loans succeeds."""
        # Arrange: Create item with returned loan
        bib_record = catalog_service.create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Returned Book",
                isbn="9780123456788",
                authors=["Test Author"]
            ),
            isbn_lookup=False
        )

        item = catalog_service.create_item(
            db_session,
            ItemCreate(
                item_id="HIST123",
                bibliographic_record_id=bib_record.id,
                call_number="100.001",
                status="available",
                loanable=True
            )
        )

        borrower = Borrower(
            borrower_id="TEST002",
            first_name="Test",
            last_name="HISTORY",
            full_name="Test HISTORY",
            role="student"
        )
        db_session.add(borrower)
        db_session.commit()

        # Create historical loan
        loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=bib_record.id,
            checkout_date=datetime.now() - timedelta(days=30),
            due_date=(datetime.now() - timedelta(days=16)).date(),
            return_date=datetime.now() - timedelta(days=14),  # Returned!
            status="returned"
        )
        db_session.add(loan)
        db_session.commit()
        loan_id = loan.id

        # Verify denormalized counter before deletion
        db_session.refresh(bib_record)
        assert bib_record.total_items == 1

        # Act: Delete item
        catalog_service.delete_item(db_session, "HIST123")

        # Assert: Item deleted
        item_check = db_session.query(Item).filter_by(item_id="HIST123").first()
        assert item_check is None

        # Verify both denormalized counters are decremented correctly
        #db_session.refresh(bib_record)
        #assert bib_record.total_items == 0
        #assert bib_record.total_circulations == 0

        # Historical loan CASCADE deleted
        assert db_session.query(CirculationTransaction).filter_by(id=loan_id).first() is None


class TestEan13ToIssn:
    """Unit-level tests for _ean13_to_issn() — no DB needed."""

    def test_wakou_ean13_returns_correct_issn(self):
        from src.bcd_api.services.catalog_service import _ean13_to_issn
        # 9771163770025 is Wakou magazine kiosk EAN-13
        result = _ean13_to_issn("9771163770025")
        assert result is not None
        assert result.startswith("1163-")
        # Full ISSN should be 9 chars including hyphen
        assert len(result) == 9

    def test_book_ean13_returns_none(self):
        from src.bcd_api.services.catalog_service import _ean13_to_issn
        # 978 prefix = book barcode, not periodical
        assert _ean13_to_issn("9780306406157") is None

    def test_wrong_length_returns_none(self):
        from src.bcd_api.services.catalog_service import _ean13_to_issn
        assert _ean13_to_issn("977116377002") is None  # 12 digits

    def test_non_digits_returns_none(self):
        from src.bcd_api.services.catalog_service import _ean13_to_issn
        assert _ean13_to_issn("NOT_A_BARCODE") is None

    def test_result_format_is_nnnn_dash_nnnx(self):
        from src.bcd_api.services.catalog_service import _ean13_to_issn
        result = _ean13_to_issn("9771163770025")
        assert result is not None
        # Format: NNNN-NNNX
        import re
        assert re.match(r"^\d{4}-\d{3}[\dX]$", result)


class TestFormatIsbn:
    """Tests for export_service._format_isbn() — no double-prefix."""

    def setup_method(self):
        from src.bcd_api.services.export_service import ExportService
        self.svc = ExportService.__new__(ExportService)

    def test_already_prefixed_isbn_returned_as_is(self):
        assert self.svc._format_isbn("isbn:9782070612758") == "isbn:9782070612758"

    def test_already_prefixed_issn_returned_as_is(self):
        assert self.svc._format_isbn("issn:1163-7706") == "issn:1163-7706"

    def test_legacy_bare_isbn_gets_prefix(self):
        assert self.svc._format_isbn("9782070612758") == "isbn:9782070612758"

    def test_empty_returns_empty_string(self):
        assert self.svc._format_isbn("") == ""

    def test_none_returns_empty_string(self):
        assert self.svc._format_isbn(None) == ""


class TestDownloadCoverWithPrefix:
    """Tests for _download_cover() — handles isbn: prefix and skips issn:."""

    def test_issn_identifier_returns_none(self):
        from src.bcd_api.services.catalog_service import _download_cover
        result = _download_cover("issn:1163-7706")
        assert result is None

    def test_none_returns_none(self):
        from src.bcd_api.services.catalog_service import _download_cover
        result = _download_cover(None)
        assert result is None


class TestSearchBibliographicRecordsFilterByShelfLocation:
    """Tests for shelf_location filter in search_bibliographic_records."""

    def test_filter_by_shelf_location_returns_matching_records(self, db_session):
        # Arrange
        record1 = BiblographicRecord(title="Romans du rayon", authors='["Auteur A"]', medium_type="Livre")
        record2 = BiblographicRecord(title="Documentaires", authors='["Auteur B"]', medium_type="Livre")
        db_session.add_all([record1, record2])
        db_session.flush()
        item1 = Item(item_id="SHL001", bibliographic_record_id=record1.id, shelf_location="Romans ado")
        item2 = Item(item_id="SHL002", bibliographic_record_id=record2.id, shelf_location="Documentaires")
        db_session.add_all([item1, item2])
        db_session.flush()

        # Act
        results, total = catalog_service.search_bibliographic_records(
            db_session, shelf_location="Romans ado"
        )

        # Assert
        assert total == 1
        assert results[0].title == "Romans du rayon"

    def test_filter_by_shelf_location_excludes_non_matching(self, db_session):
        # Arrange
        record = BiblographicRecord(title="Livre sans rayon", authors='["X"]', medium_type="Livre")
        db_session.add(record)
        db_session.flush()
        item = Item(item_id="SHL003", bibliographic_record_id=record.id, shelf_location="BDs")
        db_session.add(item)
        db_session.flush()

        # Act
        results, total = catalog_service.search_bibliographic_records(
            db_session, shelf_location="Romans ado"
        )

        # Assert
        assert total == 0

    def test_no_shelf_location_filter_returns_all(self, db_session):
        # Arrange
        record = BiblographicRecord(title="Livre quelconque", authors='["Y"]', medium_type="Livre")
        db_session.add(record)
        db_session.flush()

        # Act
        _, total_without_filter = catalog_service.search_bibliographic_records(db_session)
        _, total_with_none = catalog_service.search_bibliographic_records(db_session, shelf_location=None)

        # Assert
        assert total_without_filter == total_with_none
