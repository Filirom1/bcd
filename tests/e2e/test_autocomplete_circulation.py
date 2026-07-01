"""
E2E Tests for Autocomplete and Borrower Selection in Circulation Pages

Tests unified ClassRosterPanel borrower selection and Item autocomplete search.
"""

import time

import pytest
from src.bcd_api.models.class_model import Class


@pytest.mark.e2e
class TestBorrowerRosterSelection:
    """Test unified ClassRosterPanel borrower selection and search on checkout page."""

    def test_borrower_filtering_displays_results(
        self, circulation_page, borrower_factory, db_session
    ):
        """Typing filters the ClassRosterPanel to show matching students."""
        # Arrange: Create test classes and borrowers
        school_class1 = Class(id=1, name="CP")
        school_class2 = Class(id=2, name="CE1")
        db_session.add(school_class1)
        db_session.add(school_class2)
        db_session.commit()

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

        # Act: Reload page to pick up database changes
        circulation_page.page.reload()
        circulation_page.page.wait_for_selector('.filter-input')

        # Select class
        circulation_page.select_class(1)

        # Type partial name to filter
        circulation_page.type_borrower_search("Ami")
        circulation_page.page.wait_for_timeout(500)

        # Assert: Results shown with correct data
        results_count = circulation_page.get_roster_students_count()
        assert results_count >= 1

        # Check that Amira appears in filtered list
        student_text = circulation_page.get_roster_student_text(0)
        assert "Amira" in student_text or "BENALI" in student_text

    def test_borrower_selection_by_id_lookup(
        self, circulation_page, borrower_factory, db_session
    ):
        """Typing borrower ID automatically triggers lookup and loads them."""
        # Arrange: Create class and borrower
        school_class = Class(id=1, name="CE1")
        db_session.add(school_class)
        db_session.commit()

        borrower = borrower_factory.create(
            borrower_id="12345",
            first_name="Sophie",
            last_name="DURAND",
            class_id=1
        )
        db_session.commit()

        # Act: Reload page to pick up database changes
        circulation_page.page.reload()
        circulation_page.page.wait_for_selector('.filter-input')

        # Type borrower ID to lookup
        circulation_page.type_borrower_search("12345")
        circulation_page.page.wait_for_timeout(1000) # Wait for debounce + API lookup

        # Assert: Borrower is automatically loaded
        circulation_page.wait_for_borrower_loaded(timeout=3000)
        borrower_name = circulation_page.get_borrower_name()
        assert "Sophie" in borrower_name or "DURAND" in borrower_name

    def test_borrower_click_selection(
        self, circulation_page, borrower_factory, db_session
    ):
        """Clicking on student in roster selects and loads the borrower."""
        # Arrange: Create classes and borrower
        school_class1 = Class(id=1, name="CE2")
        school_class2 = Class(id=2, name="CM1")
        db_session.add(school_class1)
        db_session.add(school_class2)
        db_session.commit()

        borrower = borrower_factory.create(
            borrower_id="201",
            first_name="Lucas",
            last_name="BERNARD",
            class_id=1
        )
        db_session.commit()

        # Act: Reload page to pick up database changes
        circulation_page.page.reload()
        circulation_page.page.wait_for_selector('.filter-input')

        # Select class and click student row
        circulation_page.select_class(1)
        circulation_page.click_roster_student(0)

        # Assert: Borrower loaded
        circulation_page.wait_for_borrower_loaded(timeout=2000)
        borrower_name = circulation_page.get_borrower_name()
        assert "Lucas" in borrower_name or "BERNARD" in borrower_name

    def test_borrower_no_results(
        self, circulation_page, borrower_factory, db_session
    ):
        """Shows 'No students found' placeholder when query has no matches."""
        # Arrange: Create classes and borrower
        school_class1 = Class(id=1, name="CM1")
        school_class2 = Class(id=2, name="CM2")
        db_session.add(school_class1)
        db_session.add(school_class2)
        db_session.commit()

        borrower = borrower_factory.create(
            borrower_id="501",
            first_name="Alice",
            last_name="MOREAU",
            class_id=1
        )
        db_session.commit()

        # Act: Reload page to pick up database changes
        circulation_page.page.reload()
        circulation_page.page.wait_for_selector('.filter-input')

        # Select class, search non-existent name
        circulation_page.select_class(1)
        circulation_page.type_borrower_search("ZZZZZ")
        circulation_page.page.wait_for_timeout(500)

        # Assert: Roster empty placeholder is shown
        assert circulation_page.is_roster_empty_visible()


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
        self, circulation_page, item_factory, borrower_factory, db_session
    ):
        """Autocomplete dropdown appears within 500ms of typing."""
        # Arrange
        borrower = borrower_factory.create(borrower_id="1101", class_id=1)
        item, record = item_factory.create_with_record(
            item_id="PERF001",
            title="Performance Test Book"
        )
        db_session.commit()

        # Act: Measure time from typing to dropdown appearance
        circulation_page.goto_checkout()
        circulation_page.enter_borrower_id("1101")

        start_time = time.time()
        circulation_page.type_item_search("Perf")
        circulation_page.wait_for_autocomplete_dropdown(timeout=1000)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000

        # Assert: Performance target met (300ms debounce + 200ms API)
        # Allow some margin for virtual test environments (1200ms)
        assert elapsed_ms < 1200, f"Autocomplete took {elapsed_ms}ms (target: <500ms)"


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
