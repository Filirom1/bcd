"""
Base Page Object

Provides common functionality for all page objects.
"""

from playwright.sync_api import Page


class BasePage:
    """Base class for all page objects."""

    def __init__(self, page: Page, server_url: str):
        self.page = page
        self.server_url = server_url

    def navigate_to(self, path: str):
        """Navigate to a specific path."""
        url = f"{self.server_url}/#/{path}"
        self.page.goto(url)
        self.wait_for_page_load()

    def wait_for_page_load(self, timeout=10000):
        """Wait for Vue app to be ready."""
        self.page.wait_for_selector('.sidebar', timeout=timeout)

    def wait_for_selector(self, selector: str, timeout=5000):
        """Wait for element to be visible."""
        self.page.wait_for_selector(selector, state='visible', timeout=timeout)

    def click(self, selector: str):
        """Click an element."""
        self.page.locator(selector).click()

    def fill(self, selector: str, value: str):
        """Fill an input field."""
        self.page.locator(selector).fill(value)

    def get_text(self, selector: str) -> str:
        """Get text content of an element."""
        return self.page.locator(selector).inner_text()

    def is_visible(self, selector: str) -> bool:
        """Check if element is visible."""
        return self.page.locator(selector).is_visible()

    def wait_for_notification(self, timeout=5000):
        """Wait for notification toast to appear."""
        self.page.wait_for_selector('.toast, .alert', timeout=timeout)

    def get_notification_text(self) -> str:
        """Get notification message text."""
        return self.page.locator('.toast, .alert').first.inner_text()

    def switch_language(self, lang: str):
        """Switch language (FR or EN)."""
        button = self.page.locator(f'button:has-text("{lang.upper()}")')
        button.click()
        self.page.wait_for_timeout(500)  # Wait for i18n to update
