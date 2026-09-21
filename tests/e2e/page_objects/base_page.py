"""
Base Page Object

Provides common functionality for all page objects.
"""

from playwright.sync_api import Page


APP_READY_TIMEOUT = 30_000


def wait_for_app_ready(page: Page, timeout: int = APP_READY_TIMEOUT):
    """Wait for Vue to mount and report bootstrap errors clearly."""
    page.wait_for_function(
        """() => {
            const app = window.__BCD_APP__;
            return app && (app.ready === true || app.error !== null);
        }""",
        timeout=timeout,
    )

    state = page.evaluate(
        """() => {
            const app = window.__BCD_APP__;
            return app ? {ready: app.ready, error: app.error} : null;
        }"""
    )
    if state and state.get("error"):
        error = state["error"]
        raise AssertionError(
            f"Vue application failed to initialize: {error.get('message', error)}"
        )

    page.locator(".sidebar").wait_for(state="visible", timeout=timeout)


def navigate_and_wait_for_app(page: Page, url: str, attempts: int = 2):
    """Load a SPA URL, retrying one transient bootstrap failure."""
    last_error = None
    for _ in range(attempts):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=APP_READY_TIMEOUT)
            wait_for_app_ready(page)
            return
        except Exception as error:
            last_error = error

    raise last_error


class BasePage:
    """Base class for all page objects."""

    def __init__(self, page: Page, server_url: str):
        self.page = page
        self.server_url = server_url

    def navigate_to(self, path: str):
        """Navigate to a specific path and wait for the SPA bootstrap."""
        url = f"{self.server_url}/#/{path}"
        # A transient failed asset/API request can leave the loading screen in
        # place. One clean reload is safer than making every test absorb this
        # race with arbitrary sleeps.
        navigate_and_wait_for_app(self.page, url)

    def wait_for_page_load(self, timeout=APP_READY_TIMEOUT):
        """Wait for Vue to mount and report bootstrap errors clearly."""
        wait_for_app_ready(self.page, timeout=timeout)

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
