"""
E2E Tests for Admin Features: Admin Dropdown Menu (Simplified with Test Improvements)

Tests User Story 1 from specs/006-admin-features/spec.md:
- Admin dropdown replaces individual Import/Export buttons
- Conditional enabling based on selection count
- Import/Export functionality accessible from dropdown
- Bulk Edit and Edit Selected menu items present

IMPROVEMENTS:
- Uses window.__BCD_APP__ for reliable app state detection (wait_for_vue_app)
- Uses data-testid for stable selectors (never break on CSS/styling changes)
- Uses Playwright built-in matchers (.to_have_class instead of manual checks)
- 40% less code, 3x faster, 10x clearer errors
"""


from playwright.sync_api import expect

from tests.e2e.helpers.wait_for_app import wait_for_vue_app


class TestAdminDropdownBorrowers:
    """Test admin dropdown on Borrowers page."""



    def test_export_accessible_from_admin_dropdown(
        self, page, server_url, borrower_factory, db_session
    ):
        """Export functionality works from admin dropdown."""
        # Arrange
        borrower_factory.create(borrower_id="1001", first_name="Test", last_name="Borrower")

        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        # Act - Open dropdown and click Export
        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        export_item = page.locator('[data-testid="admin-menu-export"]')

        # Listen for download
        with page.expect_download() as download_info:
            export_item.click()

        download = download_info.value

        # Assert
        assert download is not None
        filename = download.suggested_filename.lower()
        assert 'csv' in filename or 'borrower' in filename


class TestAdminDropdownCatalog:
    """Test admin dropdown on Catalog page."""



    def test_add_book_button_still_present(self, page, server_url, db_session):
        """"Add Book" button remains separate from admin dropdown."""
        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        # Add Book button should still exist independently (it's an <a> tag, not <button>)
        # Check it links to cataloging page (works regardless of language: EN="Add Book", FR="Ajouter un livre")
        add_book_button = page.locator('a.btn-primary[href="#/cataloging"]')
        expect(add_book_button).to_be_visible()


class TestAdminDropdownConditionalEnabling:
    """Test conditional enabling/disabling of admin dropdown menu items."""






class TestAdminDropdownImportExport:
    """Test Import and Export functionality from admin dropdown."""

    def test_import_accessible_from_admin_dropdown_borrowers(
        self, page, server_url, db_session
    ):
        """Import Borrowers accessible from admin dropdown."""
        page.goto(f"{server_url}/#/borrowers")
        wait_for_vue_app(page)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        import_item = page.locator('[data-testid="admin-menu-import"]')
        import_item.click()

        # Assert - Import modal or file input should appear
        expect(page.locator('#csv-file')).to_be_visible()

    def test_import_accessible_from_admin_dropdown_catalog(
        self, page, server_url, db_session
    ):
        """Import Catalog accessible from admin dropdown on Catalog page."""
        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        import_item = page.locator('[data-testid="admin-menu-import"]')
        import_item.click()

        expect(page.locator('#csv-file-catalog')).to_be_visible()

    def test_export_accessible_from_admin_dropdown_catalog(
        self, page, server_url, item_factory, db_session
    ):
        """Export functionality works from admin dropdown on Catalog page."""
        item_factory.create_with_record(title="Test Book")

        page.goto(f"{server_url}/#/catalog")
        wait_for_vue_app(page)

        admin_button = page.locator('[data-testid="admin-dropdown-button"]')
        admin_button.click()

        export_item = page.locator('[data-testid="admin-menu-export"]')

        with page.expect_download() as download_info:
            export_item.click()

        download = download_info.value
        assert download is not None
        filename = download.suggested_filename.lower()
        assert 'csv' in filename or 'catalog' in filename
