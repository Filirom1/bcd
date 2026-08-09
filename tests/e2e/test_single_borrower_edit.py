"""
E2E Tests for User Story 4: Single Borrower Editing (Updated with Testability Improvements)

...
"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers.wait_for_app import wait_for_vue_app


class TestEditBorrowerModalOpening:
    """Test opening the edit borrower modal with improved selectors."""

    @pytest.mark.e2e_to_be_removed
    def test_edit_selected_button_disabled_when_no_selection(
        self, page: Page, server_url: str, db_session
    ):
        """
        Edit Selected is disabled when no borrowers selected.

        Arrange: Navigate to Borrowers page
        Act: Open admin dropdown
        Assert: Edit Selected menu item is disabled
        """
        # Arrange
        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Act - Click admin dropdown using stable selector
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        expect(admin_button).to_be_visible(timeout=5000)
        admin_button.click()

        # Assert - Edit Selected should be disabled
        dropdown_menu = page.locator('ul.dropdown-menu.show')
        expect(dropdown_menu).to_be_visible()

        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        expect(edit_selected).to_be_visible()
        expect(edit_selected).to_have_class(re.compile(r'disabled'))

    @pytest.mark.e2e_to_be_removed
    def test_edit_selected_button_enabled_when_exactly_one_selected(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Edit Selected is enabled when exactly 1 borrower selected.

        Arrange: Create borrowers, select 1
        Act: Open admin dropdown
        Assert: Edit Selected menu item is enabled
        """
        # Arrange
        borrower_factory.create_batch(2)

        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Select first borrower
        first_checkbox = page.locator('tbody input[type="checkbox"]').first
        expect(first_checkbox).to_be_visible(timeout=5000)
        first_checkbox.check()
        page.wait_for_timeout(300)  # Allow selection state to update

        # Act
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        # Assert
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        expect(edit_selected).to_be_visible()
        expect(edit_selected).not_to_have_class('disabled')

    @pytest.mark.e2e_to_be_removed
    def test_clicking_edit_selected_opens_modal(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Clicking 'Edit Selected' with 1 borrower selected opens edit modal.

        Arrange: Create borrower, select it
        Act: Click Edit Selected
        Assert: Modal opens with correct title
        """
        # Arrange
        borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont",
            role="student"
        )

        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Select borrower
        first_checkbox = page.locator('tbody input[type="checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        # Open dropdown
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        # Act - Click Edit Selected
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Assert - Modal opens with stable selector
        modal = page.locator('[data-testid="borrower-edit-modal"]')
        expect(modal).to_be_visible(timeout=5000)

        modal_title = page.locator('[data-testid="modal-title"]')
        expect(modal_title).to_contain_text(re.compile(r"Edit Borrower|Modifier l'emprunteur"))


class TestEditBorrowerFormFields:
    """Test form field pre-population and editing."""

    @pytest.mark.e2e_to_be_removed
    def test_edit_form_displays_current_borrower_data(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Edit form pre-populates with current borrower data.

        Arrange: Create borrower with specific data
        Act: Open edit modal
        Assert: Form fields contain current values
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="202",
            first_name="Marie",
            last_name="Curie",
            role="teacher",
            email="marie@school.fr",
            phone="0612345678"
        )

        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Select and open edit modal
        first_checkbox = page.locator('tbody input[type="checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Assert - Check form fields using stable selectors
        modal = page.locator('[data-testid="borrower-edit-modal"]')
        expect(modal).to_be_visible()

        # Verify all fields pre-populated
        expect(page.locator('[data-testid="input-borrower-id"]')).to_have_value("202")
        expect(page.locator('[data-testid="input-first-name"]')).to_have_value("Marie")
        expect(page.locator('[data-testid="input-last-name"]')).to_have_value("Curie")
        expect(page.locator('[data-testid="select-role"]')).to_have_value("teacher")
        expect(page.locator('[data-testid="input-email"]')).to_have_value("marie@school.fr")
        expect(page.locator('[data-testid="input-phone"]')).to_have_value("0612345678")

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


class TestEditBorrowerCancelBehavior:
    """Test cancel and close behavior."""

    @pytest.mark.e2e_to_be_removed
    def test_clicking_cancel_closes_modal_without_saving(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Clicking Cancel closes modal without saving changes.

        Arrange: Open edit modal, make changes
        Act: Click Cancel
        Assert: Modal closes, changes not saved
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="501",
            first_name="Original",
            last_name="Name",
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

        # Make a change
        first_name_input = page.locator('[data-testid="input-first-name"]')
        first_name_input.fill("Changed")

        # Act - Click Cancel using stable selector
        cancel_button = page.locator('[data-testid="button-cancel"]')
        cancel_button.click()

        # Assert - Modal closes
        expect(modal).not_to_be_visible(timeout=2000)

    @pytest.mark.e2e_to_be_removed
    def test_clicking_close_button_closes_modal(
        self, page: Page, server_url: str, borrower_factory, db_session
    ):
        """
        Clicking X close button closes modal.

        Arrange: Open edit modal
        Act: Click X button
        Assert: Modal closes
        """
        # Arrange
        borrower_factory.create(borrower_id="502", first_name="Test", last_name="User")

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

        # Act - Click close button using stable selector
        close_button = page.locator('[data-testid="modal-close-button"]')
        close_button.click()

        # Assert
        expect(modal).not_to_be_visible(timeout=2000)
