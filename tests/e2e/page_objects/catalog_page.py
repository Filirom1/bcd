"""
Catalog Page Object

Handles catalog search and browse operations.
"""

from playwright.sync_api import Page

from tests.e2e.page_objects.base_page import BasePage


class CatalogPage(BasePage):
    """Page object for catalog search and browse."""

    # Selectors
    SEARCH_INPUT = 'input[type="text"], input[type="search"]'
    SEARCH_BUTTON = 'button:has-text("Search"), button:has-text("Rechercher")'
    RESULTS = 'table tbody tr:visible, .result-item:visible'
    DETAIL_MODAL = '.modal.show'  # Fixed: Only select active modals
    CATALOG_DETAIL_MODAL = '#catalogDetailModal'  # Specific modal
    FILTER_AVAILABLE = 'input[type="checkbox"]'

    def __init__(self, page: Page, server_url: str):
        super().__init__(page, server_url)

    def goto(self):
        """Navigate to catalog page."""
        self.navigate_to('catalog')

    def clear_availability_filter(self):
        """Clear the availability filter to show all items."""
        # Click the "Clear Filters" button
        clear_button = self.page.locator('button:has-text("Clear"), button:has-text("Effacer")')
        if clear_button.count() > 0:
            clear_button.first.click()
            self.page.wait_for_timeout(500)

    def search(self, query: str, wait_for_results=True, clear_filter=True):
        """
        Search catalog.

        Args:
            query: Search term (title, author, ISBN, etc.)
            wait_for_results: Whether to wait for results to load
            clear_filter: Whether to clear availability filter (default True)
        """
        # Clear availability filter by default to show all items in search
        if clear_filter:
            self.clear_availability_filter()

        search_input = self.page.locator(self.SEARCH_INPUT).first
        search_input.fill(query)

        # Click search button if visible, otherwise press Enter
        search_button = self.page.locator(self.SEARCH_BUTTON)
        if search_button.count() > 0:
            search_button.first.click()
        else:
            search_input.press('Enter')

        if wait_for_results:
            self.page.wait_for_timeout(2000)

    def get_results_count(self) -> int:
        """Get number of search results."""
        return self.page.locator(self.RESULTS).count()

    def click_first_result(self):
        """Click on first search result."""
        self.page.locator(self.RESULTS).first.click()
        self.wait_for_detail_modal()

    def wait_for_detail_modal(self, timeout=5000):
        """Wait for detail modal to open."""
        self.wait_for_selector(self.DETAIL_MODAL, timeout=timeout)

    def filter_available_only(self):
        """Apply 'Available only' filter."""
        # Use the select dropdown to filter by availability
        # Wait for the filter to be loaded
        self.page.wait_for_timeout(500)

        # Try to select by value first (more reliable)
        availability_select = self.page.locator('select.form-select').first
        try:
            availability_select.select_option(value='available', timeout=5000)
        except:
            # If that fails, try by label
            try:
                availability_select.select_option(label='Disponible uniquement', timeout=5000)
            except:
                # Last resort - use the index (assuming "available" is option 1)
                availability_select.select_option(index=1, timeout=5000)

        self.page.wait_for_timeout(1000)
