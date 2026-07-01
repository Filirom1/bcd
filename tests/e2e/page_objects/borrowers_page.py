"""
Borrowers Page Object

Handles borrower management operations.
"""

from playwright.sync_api import Page

from tests.e2e.page_objects.base_page import BasePage


class BorrowersPage(BasePage):
    """Page object for borrowers management."""

    # Selectors
    SEARCH_INPUT = 'input[type="text"]'
    CLASS_FILTER = 'select'
    TABLE = 'table tbody tr:visible'
    BORROWER_ROW = 'table tbody tr:visible'
    BLOCK_BUTTON = 'button:has-text("Block"), button:has-text("Bloquer")'
    UNBLOCK_BUTTON = 'button:has-text("Unblock"), button:has-text("Débloquer")'
    MODAL = '.modal.show'  # Fixed: Only select active modals
    BORROWER_DETAIL_MODAL = '#borrowerDetailModal'  # Specific modal
    RENEW_ALL_BUTTON = 'button:has-text("Renew All"), button:has-text("Renouveler tout")'

    # Selection/Bulk Edit selectors
    CHECKBOX_ALL = 'input[type="checkbox"]#selectAll, th input[type="checkbox"]'
    CHECKBOX_ROW = 'input[type="checkbox"][data-borrower-id]'
    BULK_EDIT_MODAL = '#bulkEditModal'
    ADMIN_DROPDOWN = 'button.btn-danger.dropdown-toggle'
    BULK_EDIT_MENU_ITEM = '[data-testid="admin-menu-bulk-edit"]'

    def __init__(self, page: Page, server_url: str):
        super().__init__(page, server_url)

    def goto(self):
        """Navigate to borrowers page."""
        self.navigate_to('borrowers')
        self.page.reload()
        self.wait_for_table_load()

    def wait_for_table_load(self, timeout=10000):
        """Wait for borrowers table to load."""
        self.wait_for_selector(self.TABLE, timeout=timeout)

    def search(self, query: str):
        """
        Search for borrowers by name.

        Args:
            query: Search term
        """
        search_input = self.page.locator(self.SEARCH_INPUT).first
        search_input.fill(query)
        self.page.wait_for_timeout(1500)  # Wait for debounce

    def filter_by_class(self, class_name: str):
        """
        Filter borrowers by class.

        Args:
            class_name: Class name to filter by
        """
        class_filter = self.page.locator(self.CLASS_FILTER).first
        class_filter.select_option(label=class_name)
        self.page.wait_for_timeout(1000)

    def get_borrower_count(self) -> int:
        """Get number of borrowers displayed."""
        return self.page.locator(self.BORROWER_ROW).count()

    def click_first_borrower(self):
        """Click on first borrower in list."""
        self.page.locator(self.BORROWER_ROW).first.click()
        self.wait_for_modal()

    def wait_for_modal(self, timeout=5000):
        """Wait for modal to open."""
        self.wait_for_selector(self.MODAL, timeout=timeout)

    def click_block_borrower(self):
        """Click block borrower button."""
        self.click(self.BLOCK_BUTTON)

    def click_unblock_borrower(self):
        """Click unblock borrower button."""
        self.click(self.UNBLOCK_BUTTON)

    def select_block_reason(self, reason: str):
        """
        Select blocking reason from dropdown.

        Args:
            reason: Reason text (e.g., "Lost Book")
        """
        # Wait a moment for block modal to appear
        self.page.wait_for_timeout(1000)

        # Find the specific block modal (the last modal shown)
        block_modal = self.page.locator('.modal.show').last

        # Select from dropdown within the modal, using value instead of label
        reason_select = block_modal.locator('select').first
        reason_select.select_option(value=reason)

    def enter_block_notes(self, notes: str):
        """
        Enter blocking notes.

        Args:
            notes: Notes text
        """
        notes_input = self.page.locator('textarea, input[type="text"]').last
        notes_input.fill(notes)

    def confirm_action(self):
        """Confirm modal action (block/unblock)."""
        # Wait for button to become enabled (after selecting reason)
        confirm_button = self.page.locator('.modal.show button.btn-danger:not([disabled]), .modal.show button.btn-success:not([disabled]), .modal.show button.btn-primary:not([disabled])').last
        confirm_button.wait_for(state='visible', timeout=5000)
        confirm_button.click()
        self.page.wait_for_timeout(1000)

    def is_borrower_blocked(self) -> bool:
        """Check if current borrower is marked as blocked."""
        blocked_badge = self.page.locator('.badge:has-text("Bloqué"), .badge:has-text("Blocked")')
        return blocked_badge.count() > 0

    # =========================================================================
    # Selection and Bulk Operations
    # =========================================================================

    def select_borrower(self, borrower_id: str):
        """
        Select a borrower by checking their checkbox.

        Args:
            borrower_id: ID of borrower to select
        """
        checkbox = self.page.locator(f'input[type="checkbox"][data-borrower-id="{borrower_id}"]')
        if checkbox.count() > 0:
            checkbox.first.check()
            self.page.wait_for_timeout(300)

    def select_borrower_by_index(self, index: int = 0):
        """
        Select a borrower by row index (0-based).

        Args:
            index: Row index (default: 0 for first borrower)
        """
        checkboxes = self.page.locator('tbody input[type="checkbox"]')
        if checkboxes.count() > index:
            checkboxes.nth(index).check()
            self.page.wait_for_timeout(300)

    def select_all(self):
        """Click 'Select All' checkbox in table header."""
        select_all_checkbox = self.page.locator(self.CHECKBOX_ALL).first
        select_all_checkbox.check()
        self.page.wait_for_timeout(500)

    def get_selected_count(self) -> int:
        """Get number of selected borrowers."""
        # Count checked checkboxes in table body
        checked_boxes = self.page.locator('tbody input[type="checkbox"]:checked')
        return checked_boxes.count()

    def open_bulk_edit_modal(self):
        """Open bulk edit modal via Admin dropdown."""
        # Open admin dropdown
        admin_dropdown = self.page.locator(self.ADMIN_DROPDOWN)
        admin_dropdown.click()
        self.page.wait_for_timeout(300)

        # Click Bulk Edit menu item
        bulk_edit_item = self.page.locator(self.BULK_EDIT_MENU_ITEM)
        bulk_edit_item.click()
        self.page.wait_for_timeout(500)

    def is_bulk_edit_enabled(self) -> bool:
        """
        Check if Bulk Edit menu item is enabled.

        Returns:
            True if enabled, False if disabled
        """
        # Open admin dropdown
        admin_dropdown = self.page.locator(self.ADMIN_DROPDOWN)
        admin_dropdown.click()
        self.page.wait_for_timeout(300)

        # Check if Bulk Edit has 'disabled' class
        bulk_edit_item = self.page.locator(self.BULK_EDIT_MENU_ITEM).first
        class_attr = bulk_edit_item.get_attribute('class')
        is_disabled = 'disabled' in (class_attr or '')

        # Close dropdown
        admin_dropdown.click()
        self.page.wait_for_timeout(300)

        return not is_disabled
