"""
E2E Tests for User Story 5: Bulk Catalog Operations

Tests User Story 5 from specs/006-admin-features/spec.md:
- Select multiple bibliographic records using checkboxes
- Bulk Edit option enabled when 2+ selected
- Bulk Delete with confirmation dialog
- Bulk Edit Fields (publisher, publication year, language, subject tags)
- Atomic transaction rollback
- Success notifications

Test Quality:
- Uses window.__BCD_APP__ for reliable app state detection
- Uses data-testid for stable selectors (never break on CSS changes)
- Uses Playwright built-in matchers
- Function-scoped isolation (fresh database per test)
- Clear AAA pattern (Arrange-Act-Assert)

IMPLEMENTATION STATUS: UI components pending implementation
- BulkCatalogEditModal component needed
- Record selection mechanism needed
- See: src/bcd_web_vue/js/pages/CatalogPage.js line 335 (handleBulkEdit TODO)
"""

import re
import pytest
from playwright.sync_api import expect
from tests.e2e.helpers.wait_for_app import wait_for_vue_app


pytestmark = pytest.mark.skip(reason="US5 UI components not yet implemented - test ready when UI complete")


class TestCatalogRecordSelection:
    """Test catalog record selection with checkboxes."""

    def test_select_single_record_with_checkbox(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Select a single catalog record using checkbox.

        Arrange: Create 3 records
        Act: Check one record's checkbox
        Assert: Selection count = 1
        """
        # Arrange
        item_factory.create_with_record(title="Book 1")
        item_factory.create_with_record(title="Book 2")
        item_factory.create_with_record(title="Book 3")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Act - Select first record (REQUIRES: checkbox implementation)
        first_checkbox = page.locator('[data-testid="record-checkbox"]').first
        first_checkbox.check()
        page.wait_for_timeout(300)

        # Assert - Admin dropdown should show count=1
        # (We can verify by checking if Edit Selected is enabled, Bulk Edit is disabled)
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        edit_selected = page.locator('[data-testid="admin-menu-edit-selected"]')
        expect(edit_selected).not_to_have_class(re.compile(r'disabled'))

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        expect(bulk_edit).to_have_class(re.compile(r'disabled'))

    def test_select_multiple_records(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Select multiple records by checking individual checkboxes.

        Arrange: Create 5 records
        Act: Check 3 records' checkboxes
        Assert: Selection count = 3, Bulk Edit enabled
        """
        # Arrange
        for i in range(5):
            item_factory.create_with_record(title=f"Book {i+1}")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Act - Select first 3 records
        checkboxes = page.locator('[data-testid="record-checkbox"]')
        checkboxes.nth(0).check()
        checkboxes.nth(1).check()
        checkboxes.nth(2).check()
        page.wait_for_timeout(300)

        # Assert - Bulk Edit should be enabled
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        expect(bulk_edit).not_to_have_class(re.compile(r'disabled'))

    def test_select_all_functionality(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Select All checkbox selects all records on current page.

        Arrange: Create 10 records
        Act: Click "Select All" checkbox
        Assert: All records selected
        """
        # Arrange
        for i in range(10):
            item_factory.create_with_record(title=f"Book {i+1}")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Act - Click Select All (REQUIRES: header checkbox implementation)
        select_all_checkbox = page.locator('[data-testid="select-all-checkbox"]')
        select_all_checkbox.check()
        page.wait_for_timeout(500)

        # Assert - All checkboxes should be checked
        checked_count = page.locator('[data-testid="record-checkbox"]:checked').count()
        expect(checked_count).to_be(10)


class TestBulkCatalogDelete:
    """Test bulk delete functionality for catalog records."""

    def test_bulk_delete_shows_confirmation_dialog(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Bulk Delete shows confirmation dialog with record count.

        Arrange: Create records, select 3
        Act: Click Bulk Edit → Delete Records
        Assert: Confirmation dialog appears with count
        """
        # Arrange
        for i in range(5):
            item_factory.create_with_record(title=f"Book {i+1}")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select 3 records
        checkboxes = page.locator('[data-testid="record-checkbox"]')
        checkboxes.nth(0).check()
        checkboxes.nth(1).check()
        checkboxes.nth(2).check()
        page.wait_for_timeout(300)

        # Act - Click Bulk Edit
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        bulk_edit.click()

        # Click Delete Records option (REQUIRES: BulkCatalogEditModal component)
        delete_option = page.locator('[data-testid="bulk-operation-delete"]')
        delete_option.click()

        # Assert - Confirmation dialog should appear
        confirmation_dialog = page.locator('[data-testid="delete-confirmation-dialog"]')
        expect(confirmation_dialog).to_be_visible()

        # Should show count
        expect(confirmation_dialog).to_contain_text('3')

    def test_bulk_delete_removes_records_and_items(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Bulk Delete removes selected records and cascade deletes items.

        Arrange: Create 5 records, select 2
        Act: Confirm bulk delete
        Assert: 2 records removed, 3 remain
        """
        # Arrange
        for i in range(5):
            item_factory.create_with_record(title=f"Book {i+1}")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select first 2 records
        checkboxes = page.locator('[data-testid="record-checkbox"]')
        checkboxes.nth(0).check()
        checkboxes.nth(1).check()
        page.wait_for_timeout(300)

        # Act - Bulk delete
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        bulk_edit.click()

        delete_option = page.locator('[data-testid="bulk-operation-delete"]')
        delete_option.click()

        confirm_button = page.locator('[data-testid="button-confirm-delete"]')
        confirm_button.click()

        # Assert - Wait for success notification
        success_notification = page.locator('[data-testid="success-notification"]')
        expect(success_notification).to_be_visible(timeout=5000)

        # Table should show 3 remaining records
        page.wait_for_timeout(1000)  # Allow table to refresh
        table_rows = page.locator('tbody tr')
        expect(table_rows).to_have_count(3)


class TestBulkCatalogFieldEdit:
    """Test bulk field editing for catalog records."""

    def test_bulk_edit_fields_modal_opens(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Bulk Edit Fields opens modal with editable fields.

        Arrange: Create records, select 3
        Act: Click Bulk Edit → Edit Fields
        Assert: Modal appears with publisher, year, language, tags fields
        """
        # Arrange
        for i in range(5):
            item_factory.create_with_record(title=f"Book {i+1}")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select 3 records
        checkboxes = page.locator('[data-testid="record-checkbox"]')
        checkboxes.nth(0).check()
        checkboxes.nth(1).check()
        checkboxes.nth(2).check()
        page.wait_for_timeout(300)

        # Act - Click Bulk Edit
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        bulk_edit.click()

        # Click Edit Fields option (REQUIRES: BulkCatalogEditModal component)
        edit_fields_option = page.locator('[data-testid="bulk-operation-edit-fields"]')
        edit_fields_option.click()

        # Assert - Modal should appear with fields
        bulk_edit_modal = page.locator('[data-testid="bulk-catalog-edit-modal"]')
        expect(bulk_edit_modal).to_be_visible()

        # Should have publisher, year, language, tags fields
        expect(page.locator('[data-testid="input-publisher"]')).to_be_visible()
        expect(page.locator('[data-testid="input-publication-year"]')).to_be_visible()
        expect(page.locator('[data-testid="select-language"]')).to_be_visible()
        expect(page.locator('[data-testid="input-subject-tags"]')).to_be_visible()

    def test_bulk_edit_publisher_updates_all_selected(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Bulk editing publisher updates all selected records.

        Arrange: Create 5 records, select 3
        Act: Bulk edit publisher to "Penguin Books"
        Assert: 3 records have new publisher, 2 unchanged
        """
        # Arrange
        records = []
        for i in range(5):
            record = item_factory.create_with_record(
                title=f"Book {i+1}",
                publisher="Old Publisher"
            )
            records.append(record)

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select first 3 records
        checkboxes = page.locator('[data-testid="record-checkbox"]')
        checkboxes.nth(0).check()
        checkboxes.nth(1).check()
        checkboxes.nth(2).check()
        page.wait_for_timeout(300)

        # Act - Bulk edit publisher
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        bulk_edit.click()

        edit_fields_option = page.locator('[data-testid="bulk-operation-edit-fields"]')
        edit_fields_option.click()

        # Change publisher
        publisher_input = page.locator('[data-testid="input-publisher"]')
        publisher_input.fill("Penguin Books")

        save_button = page.locator('[data-testid="button-save"]')
        save_button.click()

        # Assert - Success notification
        success_notification = page.locator('[data-testid="success-notification"]')
        expect(success_notification).to_be_visible(timeout=5000)

        # Refresh page to verify changes
        page.reload()
        wait_for_vue_app(page)

        # Should see "Penguin Books" appear in first 3 rows
        table = page.locator('table')
        # Count occurrences (should be 3)
        penguin_cells = page.locator('td:has-text("Penguin Books")')
        expect(penguin_cells).to_have_count(3)


class TestBulkCatalogOperationAtomicity:
    """Test that bulk operations are atomic (all-or-nothing)."""

    def test_bulk_edit_rolls_back_on_error(
        self,
        page,
        server_url,
        item_factory,
        db_session
    ):
        """
        Bulk edit rolls back all changes if any record fails validation.

        Arrange: Create records with valid data
        Act: Bulk edit with invalid data (e.g., invalid year)
        Assert: Error shown, no records updated
        """
        # Arrange
        for i in range(3):
            item_factory.create_with_record(
                title=f"Book {i+1}",
                publication_year=2020
            )

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Select all 3 records
        select_all = page.locator('[data-testid="select-all-checkbox"]')
        select_all.check()
        page.wait_for_timeout(300)

        # Act - Bulk edit with invalid year
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        bulk_edit = page.locator('[data-testid="admin-menu-bulk-edit"]')
        bulk_edit.click()

        edit_fields_option = page.locator('[data-testid="bulk-operation-edit-fields"]')
        edit_fields_option.click()

        # Enter invalid year
        year_input = page.locator('[data-testid="input-publication-year"]')
        year_input.fill("invalid-year")

        save_button = page.locator('[data-testid="button-save"]')
        save_button.click()
        page.wait_for_timeout(500)

        # Assert - Error message should appear
        error_message = page.locator('[data-testid="error-publication-year"]')
        expect(error_message).to_be_visible()

        # Close modal and verify no changes were made
        cancel_button = page.locator('[data-testid="button-cancel"]')
        cancel_button.click()

        # All records should still have year 2020
        page.reload()
        wait_for_vue_app(page)

        table = page.locator('table')
        expect(table).to_contain_text('2020')


# ============================================================================
# IMPLEMENTATION CHECKLIST (for developer implementing US5)
# ============================================================================
"""
To make these tests pass, implement:

1. **BulkCatalogEditModal.js** component:
   - Props: selectedRecords (Array), show (Boolean)
   - Emits: update:show, completed
   - Operations: Delete Records, Edit Fields
   - data-testid attributes:
     * bulk-catalog-edit-modal (modal container)
     * bulk-operation-delete (delete button)
     * bulk-operation-edit-fields (edit fields button)
     * delete-confirmation-dialog
     * button-confirm-delete
     * input-publisher, input-publication-year, select-language, input-subject-tags
     * button-save, button-cancel
     * error-publication-year (validation error)
     * success-notification

2. **CatalogPage.js** updates:
   - Add `selectedRecords` ref (array of selected record IDs)
   - Add checkboxes to table with data-testid="record-checkbox"
   - Add "Select All" checkbox with data-testid="select-all-checkbox"
   - Implement checkbox selection tracking
   - Update `selectedCount` based on `selectedRecords.length`
   - Implement `handleBulkEdit()`:
     ```javascript
     const handleBulkEdit = () => {
       if (selectedRecords.value.length >= 2) {
         showBulkEditModal.value = true;
       }
     };
     ```
   - Add refs: `showBulkEditModal`
   - Import and register BulkCatalogEditModal component

3. **API endpoints**:
   - DELETE /api/v1/bibliographic_records/bulk
     Body: { record_ids: [1, 2, 3] }
     Returns: { deleted_count: 3 }

   - PATCH /api/v1/bibliographic_records/bulk
     Body: {
       record_ids: [1, 2, 3],
       updates: { publisher: "Penguin", publication_year: 2023 }
     }
     Returns: { updated_count: 3 }

4. **Transaction handling** (in service layer):
   - Use database transactions for bulk operations
   - Rollback on any error
   - Return clear error messages

5. **i18n keys** (locales/en.json, locales/fr.json):
   - catalog.bulk.title: "Bulk Edit Catalog"
   - catalog.bulk.delete_confirm: "Delete {count} records?"
   - catalog.bulk.delete_success: "{count} records deleted"
   - catalog.bulk.update_success: "{count} records updated"

6. **Run tests**:
   ```bash
   pytest tests/e2e/test_us5_bulk_catalog_operations.py -v
   ```
"""
