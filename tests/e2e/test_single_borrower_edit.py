"""
E2E Tests for User Story 4: Single Borrower Editing (Updated with Testability Improvements)

...
"""

import re

from playwright.sync_api import Page, expect

from tests.e2e.helpers.wait_for_app import wait_for_vue_app


class TestEditBorrowerModalOpening:
    """Test opening the edit borrower modal with improved selectors."""





class TestEditBorrowerFormFields:
    """Test form field pre-population and editing."""


    def test_edit_borrower_name_updates_successfully(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Editing borrower name saves successfully.

        Arrange: Create borrower, open edit modal
        Act: Change first and last name, save
        Assert: Success notification shown, modal closes
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="303",
            first_name="Pierre",
            last_name="Dupont",
            role="student"
        )

        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Open edit modal
        first_checkbox = page.locator('tbody input[type="checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        modal = page.locator('[data-testid="borrower-edit-modal"]')
        expect(modal).to_be_visible()

        # Act - Change names using stable selectors
        first_name_input = page.locator('[data-testid="input-first-name"]')
        first_name_input.fill("Jean")

        last_name_input = page.locator('[data-testid="input-last-name"]')
        last_name_input.fill("Martin")

        # Save
        save_button = page.locator('[data-testid="button-save"]')
        save_button.click()

        # Assert - Modal closes (indicates success)
        expect(modal).not_to_be_visible(timeout=5000)

        # TODO: Verify changes in database or reload page and check


class TestEditBorrowerValidation:
    """Test form validation and error handling."""

    def test_duplicate_borrower_id_shows_error(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Changing borrower ID to duplicate value shows error.

        Arrange: Create 2 borrowers, edit first
        Act: Change borrower_id to match second borrower
        Assert: Error message displayed on field
        """
        # Arrange - Create two borrowers
        borrower1 = borrower_factory.create(borrower_id="401", first_name="First", last_name="One")
        borrower2 = borrower_factory.create(borrower_id="402", first_name="Second", last_name="Two")

        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Select first borrower and open edit
        first_checkbox = page.locator('tbody input[type="checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        modal = page.locator('[data-testid="borrower-edit-modal"]')
        expect(modal).to_be_visible()

        # Act - Change ID to duplicate
        borrower_id_input = page.locator('[data-testid="input-borrower-id"]')
        borrower_id_input.fill("402")

        # Save
        save_button = page.locator('[data-testid="button-save"]')
        save_button.click()

        page.wait_for_timeout(500)  # Allow API call to complete

        # Assert - Error message displayed using stable selector
        error_message = page.locator('[data-testid="error-borrower-id"]')
        expect(error_message).to_be_visible(timeout=3000)
        expect(error_message).to_contain_text(re.compile(r"not available|déjà attribué"))
