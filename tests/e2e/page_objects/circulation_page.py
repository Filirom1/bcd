"""
Circulation Page Object

Handles checkout and return workflows.
"""

from playwright.sync_api import Page
from tests.e2e.page_objects.base_page import BasePage


class CirculationPage(BasePage):
    """Page object for circulation operations (checkout/return)."""

    # Selectors
    BORROWER_INPUT = 'input[role="combobox"]'  # Updated for autocomplete
    SEARCH_BUTTON = 'button:has-text("Rechercher"), button:has-text("Search")'
    BORROWER_CARD = '.card-header h5, .card-header'
    ITEM_INPUT = 'input.font-monospace[role="combobox"]'  # Updated for autocomplete
    CHECKOUT_BUTTON = 'button.btn-success:has-text("Emprunter"), button:has-text("Checkout")'
    RETURN_BUTTON = 'button.btn-info:has-text("Retourner"), button:has-text("Return")'
    SCANNED_ITEMS_LIST = '.list-group-item'
    RENEW_ALL_BUTTON = 'button:has-text("Renouveler tout"), button:has-text("Renew All")'
    AUTOCOMPLETE_DROPDOWN = '#autocomplete-dropdown'
    AUTOCOMPLETE_ITEM = '.autocomplete-item'

    def __init__(self, page: Page, server_url: str):
        super().__init__(page, server_url)

    def goto_checkout(self):
        """Navigate to checkout page."""
        self.navigate_to('checkout')

    def goto_return(self):
        """Navigate to return page."""
        self.navigate_to('return')

    def enter_borrower_id(self, borrower_id: str, wait_for_load=True):
        """
        Enter borrower ID and search.

        Args:
            borrower_id: Borrower ID to search for
            wait_for_load: Whether to wait for borrower card to load
        """
        borrower_input = self.page.locator(self.BORROWER_INPUT)
        borrower_input.fill(borrower_id)
        borrower_input.press('Enter')

        if wait_for_load:
            self.wait_for_borrower_loaded()

    def wait_for_borrower_loaded(self, timeout=5000):
        """Wait for borrower card to appear."""
        self.wait_for_selector(self.BORROWER_CARD, timeout=timeout)

    def get_borrower_name(self) -> str:
        """Get displayed borrower name."""
        return self.page.locator(self.BORROWER_CARD).first.inner_text()

    def scan_item(self, barcode: str, wait_for_feedback=True):
        """
        Scan/enter item barcode.

        Args:
            barcode: Item barcode to scan
            wait_for_feedback: Whether to wait for visual feedback
        """
        # Fill the input and press Enter to submit the form
        item_input = self.page.locator(self.ITEM_INPUT)
        item_input.fill(barcode)
        item_input.press('Enter')

        if wait_for_feedback:
            # Wait for item to appear in list or notification
            self.page.wait_for_timeout(1000)

    def return_item(self, barcode: str, wait_for_confirmation=True):
        """
        Return an item.

        Args:
            barcode: Item barcode to return
            wait_for_confirmation: Whether to wait for confirmation
        """
        # Fill the input and press Enter to submit the form
        item_input = self.page.locator(self.ITEM_INPUT)
        item_input.fill(barcode)
        item_input.press('Enter')

        if wait_for_confirmation:
            self.page.wait_for_timeout(1000)

    def get_scanned_items_count(self) -> int:
        """Get number of items in scanned list."""
        return self.page.locator(self.SCANNED_ITEMS_LIST).count()

    def click_renew_all(self):
        """Click Renew All button."""
        self.click(self.RENEW_ALL_BUTTON)
        self.page.wait_for_timeout(1000)  # Wait for renewal processing

    def has_overdue_warning(self) -> bool:
        """Check if overdue warning is displayed."""
        warning = self.page.locator('.alert-danger, .text-danger:has-text("retard"), .text-danger:has-text("overdue")')
        return warning.count() > 0

    def get_loan_count_text(self) -> str:
        """Get loan count display (e.g., '1/2')."""
        # Look for pattern like "1/2" in borrower card
        text = self.page.locator('.borrower-card').inner_text()
        import re
        match = re.search(r'\d+/\d+', text)
        return match.group(0) if match else ""

    # Autocomplete methods
    def type_borrower_search(self, text: str):
        """Type into borrower input without submitting."""
        borrower_input = self.page.locator(self.BORROWER_INPUT).first
        borrower_input.fill(text)

    def type_item_search(self, text: str):
        """Type into item input without submitting."""
        item_input = self.page.locator(self.ITEM_INPUT)
        item_input.fill(text)

    def wait_for_autocomplete_dropdown(self, timeout: int = 1000):
        """Wait for autocomplete dropdown to appear."""
        self.wait_for_selector(self.AUTOCOMPLETE_DROPDOWN, timeout=timeout)

    def is_autocomplete_visible(self) -> bool:
        """Check if autocomplete dropdown is visible."""
        return self.page.locator(self.AUTOCOMPLETE_DROPDOWN).is_visible()

    def get_autocomplete_results(self):
        """Get autocomplete result elements."""
        return self.page.locator(self.AUTOCOMPLETE_ITEM).all()

    def get_autocomplete_results_count(self) -> int:
        """Get number of autocomplete results."""
        return self.page.locator(self.AUTOCOMPLETE_ITEM).count()

    def get_autocomplete_result_text(self, index: int = 0) -> str:
        """Get text of autocomplete result by index."""
        return self.page.locator(self.AUTOCOMPLETE_ITEM).nth(index).inner_text()

    def click_autocomplete_result(self, index: int = 0):
        """Click autocomplete result by index."""
        self.page.locator(self.AUTOCOMPLETE_ITEM).nth(index).click()
        self.page.wait_for_timeout(300)  # Wait for selection to process

    def press_arrow_down(self):
        """Press ArrowDown key in active input."""
        self.page.keyboard.press('ArrowDown')

    def press_arrow_up(self):
        """Press ArrowUp key in active input."""
        self.page.keyboard.press('ArrowUp')

    def press_escape(self):
        """Press Escape key."""
        self.page.keyboard.press('Escape')

    def press_enter(self):
        """Press Enter key."""
        self.page.keyboard.press('Enter')
