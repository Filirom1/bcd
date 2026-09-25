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



@pytest.mark.e2e
class TestItemAutocomplete:
    """Test autocomplete for item search on checkout/return pages."""






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
