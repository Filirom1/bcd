"""
Helper functions for waiting for Vue app to be ready in E2E tests.

Uses window.__BCD_APP__ global state for reliable app initialization detection.
"""
from playwright.sync_api import Page


def wait_for_vue_app(page: Page, timeout: int = 10000):
    """
    Wait for Vue app to fully initialize and be ready for interaction.

    Checks window.__BCD_APP__.ready flag and throws descriptive error if init fails.

    Args:
        page: Playwright page instance
        timeout: Maximum wait time in milliseconds (default: 10s)

    Raises:
        AssertionError: If app fails to initialize with error details
        TimeoutError: If app doesn't initialize within timeout
    """
    # Wait for global app state to exist
    page.wait_for_function(
        "window.__BCD_APP__ !== undefined",
        timeout=timeout
    )

    # Wait for app to be ready OR error to occur
    page.wait_for_function(
        "window.__BCD_APP__.ready === true || window.__BCD_APP__.error !== null",
        timeout=timeout
    )

    # Check if initialization failed
    error = page.evaluate("window.__BCD_APP__.error")
    if error:
        raise AssertionError(
            f"Vue app failed to initialize: {error['message']}\n"
            f"Stack: {error.get('stack', 'No stack trace')}"
        )

    # Verify app is actually ready
    ready = page.evaluate("window.__BCD_APP__.ready")
    assert ready, "Vue app not ready after timeout"


def navigate_via_router(page: Page, path: str):
    """
    Navigate using Vue Router (avoids full page reload).

    Args:
        page: Playwright page instance
        path: Route path (e.g., "/borrowers", "/catalog")
    """
    page.evaluate(f"window.__BCD_APP__.navigate('{path}')")
    page.wait_for_timeout(300)  # Allow router transition


def set_app_locale(page: Page, locale: str):
    """
    Change application locale for i18n testing.

    Args:
        page: Playwright page instance
        locale: Locale code ("en" or "fr")
    """
    page.evaluate(f"window.__BCD_APP__.setLocale('{locale}')")
    page.wait_for_timeout(100)  # Allow i18n to update


def get_current_route(page: Page) -> str:
    """
    Get current Vue Router path.

    Returns:
        Current route path (e.g., "/borrowers")
    """
    return page.evaluate("window.__BCD_APP__.router.currentRoute.value.path")


def is_app_ready(page: Page) -> bool:
    """
    Check if Vue app is ready without waiting.

    Returns:
        True if app is ready, False otherwise
    """
    try:
        return page.evaluate("window.__BCD_APP__ && window.__BCD_APP__.ready === true")
    except Exception:
        return False
