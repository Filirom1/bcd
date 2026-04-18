"""
Settings Page Object

Handles system settings configuration.
"""

from playwright.sync_api import Page
from tests.e2e.page_objects.base_page import BasePage


class SettingsPage(BasePage):
    """Page object for settings management."""

    # Selectors
    FORM = 'form, .settings-form'
    SAVE_BUTTON = 'button[type="submit"], button:has-text("Save"), button:has-text("Enregistrer")'
    TEXT_INPUT = 'input[type="text"]'
    NUMBER_INPUT = 'input[type="number"]'

    def __init__(self, page: Page, server_url: str):
        super().__init__(page, server_url)

    def goto(self):
        """Navigate to settings page."""
        self.navigate_to('settings')
        self.wait_for_form_load()

    def wait_for_form_load(self, timeout=10000):
        """Wait for settings form to load."""
        self.wait_for_selector(self.FORM, timeout=timeout)

    def set_library_name(self, name: str):
        """Set library name."""
        library_input = self.page.locator(self.TEXT_INPUT).first
        library_input.clear()
        library_input.fill(name)

    def set_loan_duration(self, days: int):
        """Set loan duration in days."""
        loan_input = self.page.locator(self.NUMBER_INPUT).first
        loan_input.clear()
        loan_input.fill(str(days))

    def save(self, wait_for_confirmation=True):
        """Save settings."""
        self.click(self.SAVE_BUTTON)

        if wait_for_confirmation:
            self.page.wait_for_timeout(2000)

    def get_library_name(self) -> str:
        """Get current library name value."""
        return self.page.locator(self.TEXT_INPUT).first.input_value()

    def get_loan_duration(self) -> int:
        """Get current loan duration value."""
        value = self.page.locator(self.NUMBER_INPUT).first.input_value()
        return int(value) if value else 0
