"""
E2E Tests for User Story 6: Single Catalog Record/Item Editing

Tests User Story 6 from specs/006-admin-features/spec.md:
- Edit individual bibliographic records (title, author, ISBN, etc.)
- Edit individual items (barcode, status, location, notes)
- Validate ISBN format and uniqueness
- Validate barcode uniqueness
- Update fields and verify changes persist

Test Quality:
- Uses window.__BCD_APP__ for reliable app state detection
- Uses data-testid for stable selectors (never break on CSS changes)
- Uses Playwright built-in matchers
- Function-scoped isolation (fresh database per test)
- Clear AAA pattern (Arrange-Act-Assert)

IMPLEMENTATION STATUS: UI components pending implementation
- CatalogRecordEditForm component needed
- Item selection mechanism needed
- See: src/bcd_web_vue/js/pages/CatalogPage.js line 343 (handleEditSelected TODO)
"""

import re

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers.wait_for_app import wait_for_vue_app

pytestmark = pytest.mark.skip(reason="US6 UI components not yet implemented - test ready when UI complete")


class TestCatalogRecordEditModalOpening:
    """Test opening the edit catalog record modal."""

    def test_edit_selected_button_disabled_when_no_selection(
        self,
        page,
        server_url,
        db_session
    ):
        """
        Edit Selected is disabled when no records selected.

        Arrange: Navigate to Catalog page
        Act: Open admin dropdown
        Assert: Edit Selected menu item is disabled
        """
        # Arrange
        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Act - Click admin dropdown
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        expect(admin_button).to_be_visible()
        admin_button.click()

        # Assert - Edit Selected should be disabled
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        expect(edit_selected).to_be_visible()
        expect(edit_selected).to_have_class(re.compile(r'disabled'))

    def test_edit_selected_button_enabled_when_exactly_one_selected(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Edit Selected is enabled when exactly 1 record selected.

        Arrange: Create records, select 1
        Act: Open admin dropdown
        Assert: Edit Selected menu item is enabled
        """
        # Arrange - Create records with items
        item_factory.create_with_record(title="Test Book 1")
        item_factory.create_with_record(title="Test Book 2")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select first record (REQUIRES: checkbox implementation in CatalogPage)
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        # Act - Open admin dropdown
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        # Assert - Edit Selected should NOT be disabled
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        expect(edit_selected).not_to_have_class(re.compile(r'disabled'))

    def test_clicking_edit_selected_opens_modal(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Clicking Edit Selected opens the catalog record edit modal.

        Arrange: Create record, select it
        Act: Click Admin → Edit Selected
        Assert: Edit modal appears with record data
        """
        # Arrange
        record_item = item_factory.create_with_record(
            title="Test Book",
            author="Test Author",
            isbn="978-0-123456-78-9"
        )

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select record (REQUIRES: checkbox implementation)
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        # Act - Click Admin → Edit Selected
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Assert - Modal should appear (REQUIRES: CatalogRecordEditForm component)
        modal = page.locator('[data-testid="catalog-record-edit-modal"]')
        expect(modal).to_be_visible()

        # Verify modal title
        modal_title = page.locator('[data-testid="modal-title"]')
        expect(modal_title).to_contain_text('Edit', ignore_case=True)


class TestCatalogRecordEditFormFields:
    """Test catalog record edit form field behavior."""

    def test_edit_form_displays_current_record_data(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Edit form pre-fills with current record data.

        Arrange: Create record with known data
        Act: Open edit form
        Assert: Form shows current title, author, ISBN, etc.
        """
        # Arrange
        record_item = item_factory.create_with_record(
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
            isbn="978-0-7432-7356-5",
            publisher="Scribner",
            publication_year=1925
        )

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Open edit modal (REQUIRES: UI implementation)
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Assert - Form fields should show current data
        title_input = page.locator('[data-testid="input-title"]')
        expect(title_input).to_have_value("The Great Gatsby")

        author_input = page.locator('[data-testid="input-author"]')
        expect(author_input).to_have_value("F. Scott Fitzgerald")

        isbn_input = page.locator('[data-testid="input-isbn"]')
        expect(isbn_input).to_have_value("978-0-7432-7356-5")

        publisher_input = page.locator('[data-testid="input-publisher"]')
        expect(publisher_input).to_have_value("Scribner")

    def test_edit_record_title_updates_successfully(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Editing record title saves successfully.

        Arrange: Create record
        Act: Change title and save
        Assert: Title updated in database and UI
        """
        # Arrange
        record_item = item_factory.create_with_record(title="Old Title")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Open edit modal
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Act - Change title
        title_input = page.locator('[data-testid="input-title"]')
        title_input.fill("New Updated Title")

        save_button = page.locator('[data-testid="button-save"]')
        save_button.click()

        # Assert - Modal should close
        modal = page.locator('[data-testid="catalog-record-edit-modal"]')
        expect(modal).not_to_be_visible(timeout=3000)

        # Verify table shows new title
        page.wait_for_timeout(1000)  # Allow table to refresh
        table = page.locator('table')
        expect(table).to_contain_text("New Updated Title")


class TestCatalogRecordEditValidation:
    """Test validation in catalog record edit form."""

    def test_invalid_isbn_format_shows_error(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Invalid ISBN format triggers validation error.

        Arrange: Create record
        Act: Enter invalid ISBN and save
        Assert: Error message displayed, record not saved
        """
        # Arrange
        record_item = item_factory.create_with_record(
            title="Test Book",
            isbn="978-1-234567-89-0"
        )

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Open edit modal
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Act - Enter invalid ISBN
        isbn_input = page.locator('[data-testid="input-isbn"]')
        isbn_input.fill("invalid-isbn")

        save_button = page.locator('[data-testid="button-save"]')
        save_button.click()
        page.wait_for_timeout(500)

        # Assert - Error message should appear
        error_message = page.locator('[data-testid="error-isbn"]')
        expect(error_message).to_be_visible()

        # Modal should still be open
        modal = page.locator('[data-testid="catalog-record-edit-modal"]')
        expect(modal).to_be_visible()


class TestCatalogRecordEditCancelBehavior:
    """Test cancel/close behavior in edit form."""

    def test_clicking_cancel_closes_modal_without_saving(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Clicking Cancel closes modal without saving changes.

        Arrange: Create record, open edit modal
        Act: Change title, click Cancel
        Assert: Modal closes, title unchanged
        """
        # Arrange
        record_item = item_factory.create_with_record(title="Original Title")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Open edit modal
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()
        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        edit_selected.click()

        # Act - Change title but cancel
        title_input = page.locator('[data-testid="input-title"]')
        title_input.fill("Changed Title")

        cancel_button = page.locator('[data-testid="button-cancel"]')
        cancel_button.click()

        # Assert - Modal should close
        modal = page.locator('[data-testid="catalog-record-edit-modal"]')
        expect(modal).not_to_be_visible(timeout=3000)

        # Title should still be original
        table = page.locator('table')
        expect(table).to_contain_text("Original Title")
        expect(table).not_to_contain_text("Changed Title")


# ============================================================================
# IMPLEMENTATION CHECKLIST (for developer implementing US6)
# ============================================================================
"""
To make these tests pass, implement:

1. **CatalogRecordEditForm.js** component (similar to BorrowerEditForm.js):
   - Props: record (Object), show (Boolean)
   - Emits: update:show, saved
   - Fields: title*, author, isbn, publisher, publication_year, language, subject_tags, description
   - Validation: ISBN format (optional), required fields
   - data-testid attributes:
     * catalog-record-edit-modal (modal container)
     * modal-title
     * input-title, input-author, input-isbn, input-publisher, input-publication-year
     * error-isbn (validation error)
     * button-save, button-cancel

2. **CatalogPage.js** updates:
   - Add `selectedRecords` ref (array of selected record IDs)
   - Add checkboxes to table rows with data-testid="record-checkbox"
   - Implement checkbox selection tracking
   - Update `selectedCount` based on `selectedRecords.length`
   - Implement `handleEditSelected()`:
     ```javascript
     const handleEditSelected = () => {
       if (selectedRecords.value.length === 1) {
         const recordId = selectedRecords.value[0];
         const record = results.value.find(r => r.id === recordId);
         showEditModal.value = true;
         editingRecord.value = record;
       }
     };
     ```
   - Add refs: `showEditModal`, `editingRecord`
   - Import and register CatalogRecordEditForm component

3. **API endpoint** (if not exists):
   - PATCH /api/v1/bibliographic_records/{id}
   - Body: { title, author, isbn, publisher, publication_year, language, subject_tags, description }
   - Returns updated record

4. **i18n keys** (locales/en.json, locales/fr.json):
   - catalog.edit.title: "Edit Catalog Record"
   - catalog.edit.save: "Save Changes"
   - catalog.edit.cancel: "Cancel"
   - catalog.edit.error: "Failed to update record"

5. **Run tests**:
   ```bash
   pytest tests/e2e/test_us6_single_catalog_edit.py -v
   ```
"""
