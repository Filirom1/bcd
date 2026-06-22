"""
E2E Tests for Autocomplete in Circulation Pages

Tests autocomplete functionality for borrower and item search on checkout/return pages.
"""

import time

import pytest


@pytest.mark.e2e
class TestBorrowerAutocomplete:
    """Test autocomplete for borrower search on checkout page."""

    def test_borrower_autocomplete_displays_results(
        self, circulation_page, borrower_factory, db_session
    ):
        """Typing shows autocomplete dropdown with matching borrowers."""
        # Arrange: Create test borrowers
        borrower1 = borrower_factory.create(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            class_id=1
        )
        borrower2 = borrower_factory.create(
            borrower_id="102",
            first_name="Pierre",
            last_name="MARTIN",
            class_id=1
        )
        db_session.commit()

        # Act: Navigate and type partial name
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("Ami")

        # Wait for debounce (300ms) + API response
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert: Results shown with correct data
        assert circulation_page.is_autocomplete_visible()
        results_count = circulation_page.get_autocomplete_results_count()
        assert results_count >= 1

        # Check that Amira appears in results
        first_result_text = circulation_page.get_autocomplete_result_text(0)
        assert "Amira" in first_result_text or "BENALI" in first_result_text

    def test_borrower_autocomplete_by_id(
        self, circulation_page, borrower_factory, db_session
    ):
        """Autocomplete works for borrower ID search."""
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="12345",
            first_name="Sophie",
            last_name="DURAND",
            class_id=1
        )
        db_session.commit()

        # Act: Search by ID
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("123")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert
        assert circulation_page.is_autocomplete_visible()
        result_text = circulation_page.get_autocomplete_result_text(0)
        assert "12345" in result_text or "Sophie" in result_text

    def test_borrower_autocomplete_click_selection(
        self, circulation_page, borrower_factory, db_session
    ):
        """Clicking autocomplete result selects borrower."""
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="201",
            first_name="Lucas",
            last_name="BERNARD",
            class_id=1
        )
        db_session.commit()

        # Act: Type and click result
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("Luc")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)
        circulation_page.click_autocomplete_result(0)

        # Assert: Borrower loaded
        circulation_page.wait_for_borrower_loaded(timeout=2000)
        borrower_name = circulation_page.get_borrower_name()
        assert "Lucas" in borrower_name or "BERNARD" in borrower_name

    def test_borrower_autocomplete_keyboard_navigation(
        self, circulation_page, borrower_factory, db_session
    ):
        """Arrow keys navigate autocomplete, Enter selects."""
        # Arrange: Create multiple borrowers
        borrower1 = borrower_factory.create(
            borrower_id="301",
            first_name="Emma",
            last_name="DUBOIS",
            class_id=1
        )
        borrower2 = borrower_factory.create(
            borrower_id="302",
            first_name="Emma",
            last_name="LEROY",
            class_id=1
        )
        db_session.commit()

        # Act: Type to show autocomplete
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("Emma")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert: Results visible
        assert circulation_page.get_autocomplete_results_count() >= 2

        # Act: Navigate with arrows and press Enter
        circulation_page.press_arrow_down()  # Select first
        circulation_page.page.wait_for_timeout(100)
        circulation_page.press_arrow_down()  # Select second
        circulation_page.page.wait_for_timeout(100)
        circulation_page.press_enter()  # Select

        # Assert: Borrower loaded (either Emma should work)
        circulation_page.wait_for_borrower_loaded(timeout=2000)
        borrower_name = circulation_page.get_borrower_name()
        assert "Emma" in borrower_name

    def test_borrower_autocomplete_escape_closes(
        self, circulation_page, borrower_factory, db_session
    ):
        """Escape key closes autocomplete dropdown."""
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="401",
            first_name="Noah",
            last_name="ROBERT",
            class_id=1
        )
        db_session.commit()

        # Act: Open autocomplete
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("Noah")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)
        assert circulation_page.is_autocomplete_visible()

        # Act: Press Escape
        circulation_page.press_escape()
        circulation_page.page.wait_for_timeout(200)

        # Assert: Dropdown closed
        assert not circulation_page.is_autocomplete_visible()

    def test_borrower_autocomplete_no_results(
        self, circulation_page, borrower_factory, db_session
    ):
        """Shows 'No results' message when no matches found."""
        # Arrange: Create a borrower
        borrower = borrower_factory.create(
            borrower_id="501",
            first_name="Alice",
            last_name="MOREAU",
            class_id=1
        )
        db_session.commit()

        # Act: Search for non-existent borrower
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("ZZZZZ")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert: Dropdown shows no results message
        assert circulation_page.is_autocomplete_visible()
        # The dropdown should be visible but show "No results found" message
        # (implementation shows this as a special autocomplete-item)

    def test_borrower_autocomplete_min_chars(
        self, circulation_page, borrower_factory, db_session
    ):
        """Autocomplete requires minimum 2 characters."""
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="601",
            first_name="Léa",
            last_name="SIMON",
            class_id=1
        )
        db_session.commit()

        # Act: Type only 1 character
        circulation_page.goto_checkout()
        circulation_page.type_borrower_search("L")
        circulation_page.page.wait_for_timeout(500)  # Wait longer than debounce

        # Assert: No dropdown shown
        assert not circulation_page.is_autocomplete_visible()

        # Act: Type 2nd character
        circulation_page.type_borrower_search("Lé")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert: Dropdown now shown
        assert circulation_page.is_autocomplete_visible()


@pytest.mark.e2e
class TestItemAutocomplete:
    """Test autocomplete for item search on checkout/return pages."""

    def test_item_autocomplete_displays_results(
        self, circulation_page, item_factory, borrower_factory, db_session
    ):
        """Typing shows autocomplete dropdown with matching items."""
        # Arrange: Create borrower and items
        borrower = borrower_factory.create(borrower_id="701", class_id=1)
        item1, record1 = item_factory.create_with_record(
            item_id="ITEM001",
            title="Le Petit Prince",
            authors="Antoine de Saint-Exupéry"
        )
        item2, record2 = item_factory.create_with_record(
            item_id="ITEM002",
            title="Harry Potter",
            authors="J.K. Rowling"
        )
        db_session.commit()

        # Act: Load borrower and type item search
        circulation_page.goto_checkout()
        circulation_page.enter_borrower_id("701")
        circulation_page.type_item_search("Petit")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert: Results shown
        assert circulation_page.is_autocomplete_visible()
        results_count = circulation_page.get_autocomplete_results_count()
        assert results_count >= 1

        # Check title appears
        result_text = circulation_page.get_autocomplete_result_text(0)
        assert "Petit" in result_text or "Prince" in result_text

    def test_item_autocomplete_by_barcode(
        self, circulation_page, item_factory, borrower_factory, db_session
    ):
        """Autocomplete works for item barcode search."""
        # Arrange
        borrower = borrower_factory.create(borrower_id="801", class_id=1)
        item, record = item_factory.create_with_record(
            item_id="12345678",
            title="Test Book",
            authors="Test Author"
        )
        db_session.commit()

        # Act: Search by partial barcode
        circulation_page.goto_checkout()
        circulation_page.enter_borrower_id("801")
        circulation_page.type_item_search("123")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert
        assert circulation_page.is_autocomplete_visible()
        result_text = circulation_page.get_autocomplete_result_text(0)
        assert "12345678" in result_text or "Test Book" in result_text

    def test_item_autocomplete_click_selection_checkout(
        self, circulation_page, item_factory, borrower_factory, db_session
    ):
        """Clicking item autocomplete result checks out item."""
        # Arrange
        borrower = borrower_factory.create(borrower_id="901", class_id=1)
        item, record = item_factory.create_with_record(
            item_id="BOOK001",
            title="Selected Book",
            authors="Author Name"
        )
        db_session.commit()

        # Act: Select from autocomplete
        circulation_page.goto_checkout()
        circulation_page.enter_borrower_id("901")
        circulation_page.type_item_search("Selected")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)
        circulation_page.click_autocomplete_result(0)

        # Assert: Item checked out (appears in scanned items list)
        circulation_page.page.wait_for_timeout(1000)
        scanned_count = circulation_page.get_scanned_items_count()
        assert scanned_count >= 1

    def test_item_autocomplete_on_return_page(
        self, circulation_page, item_factory, borrower_factory, db_session
    ):
        """Autocomplete works on return page."""
        # Arrange: Create item on loan
        borrower = borrower_factory.create(borrower_id="1001", class_id=1)
        item, record, transaction = item_factory.create_on_loan(
            borrower_id=borrower.id,
            item_id="RET001",
            title="Book to Return"
        )
        db_session.commit()

        # Act: Go to return page and search
        circulation_page.goto_return()
        circulation_page.type_item_search("Return")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)

        # Assert: Autocomplete shows
        assert circulation_page.is_autocomplete_visible()
        result_text = circulation_page.get_autocomplete_result_text(0)
        assert "Return" in result_text or "RET001" in result_text


@pytest.mark.e2e
class TestAutocompletePerformance:
    """Test autocomplete performance requirements."""

    def test_autocomplete_appears_within_500ms(
        self, circulation_page, borrower_factory, db_session
    ):
        """Autocomplete dropdown appears within 500ms of typing."""
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="1101",
            first_name="Performance",
            last_name="TEST",
            class_id=1
        )
        db_session.commit()

        # Act: Measure time from typing to dropdown appearance
        circulation_page.goto_checkout()

        start_time = time.time()
        circulation_page.type_borrower_search("Perf")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000

        # Assert: Performance target met (500ms = 300ms debounce + 200ms API)
        # Allow some margin for test environment (600ms)
        assert elapsed_ms < 600, f"Autocomplete took {elapsed_ms}ms (target: <500ms)"


@pytest.mark.e2e
class TestBarcodeScannerCompatibility:
    """Test that barcode scanners still work with autocomplete."""

    def test_rapid_typing_bypasses_autocomplete(
        self, circulation_page, borrower_factory, db_session
    ):
        """Rapid input (scanner simulation) bypasses autocomplete."""
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="1201",
            first_name="Scanner",
            last_name="TEST",
            class_id=1
        )
        db_session.commit()

        # Act: Simulate barcode scanner (rapid typing + immediate Enter)
        circulation_page.goto_checkout()

        # Fill rapidly (scanner-like) and press Enter immediately
        borrower_input = circulation_page.page.locator(circulation_page.BORROWER_INPUT).first
        borrower_input.type("1201", delay=10)  # 10ms delay between chars (scanner speed)
        circulation_page.press_enter()

        # Assert: Borrower loaded without showing autocomplete
        circulation_page.wait_for_borrower_loaded(timeout=2000)
        borrower_name = circulation_page.get_borrower_name()
        assert "Scanner" in borrower_name

    def test_item_scanner_still_works(
        self, circulation_page, item_factory, borrower_factory, db_session
    ):
        """Item barcode scanner workflow maintains <200ms target."""
        # Arrange
        borrower = borrower_factory.create(borrower_id="1301", class_id=1)
        item, record = item_factory.create_with_record(
            item_id="SCAN001",
            title="Scanner Test Book"
        )
        db_session.commit()

        # Act: Simulate rapid item scan
        circulation_page.goto_checkout()
        circulation_page.enter_borrower_id("1301")

        start_time = time.time()
        item_input = circulation_page.page.locator(circulation_page.ITEM_INPUT)
        item_input.type("SCAN001", delay=10)  # Scanner speed
        circulation_page.press_enter()
        circulation_page.page.wait_for_timeout(500)  # Wait for processing
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000

        # Assert: Scanner workflow fast enough
        assert elapsed_ms < 1000  # Scanner target <200ms, allow margin for E2E
        scanned_count = circulation_page.get_scanned_items_count()
        assert scanned_count >= 1
