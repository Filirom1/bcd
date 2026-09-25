"""
E2E Tests: Contextual Help Panel (Feature 001)

Tests cover the browser-specific part of the help workflow:
- The checkout panel opens with section-specific content.
- The panel closes through the Bootstrap dismiss action.
"""
from playwright.sync_api import Page, expect

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def wait_for_app(page: Page):
    """Wait for Vue SPA to be ready."""
    page.wait_for_selector('.sidebar, #app', timeout=10_000)


def open_help_panel(page: Page):
    """Click the help button and wait for offcanvas to be visible."""
    help_button = page.locator('button[data-bs-toggle="offcanvas"]').first
    help_button.click()
    page.wait_for_selector('.offcanvas.show', timeout=5_000)


def close_help_panel(page: Page):
    """Click the offcanvas close button."""
    page.locator('.offcanvas .btn-close').first.click()
    page.wait_for_timeout(400)  # Bootstrap transition


# ─────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────

def test_help_panel_opens_on_checkout_page(page: Page, server_url: str, db_session):
    """US1 — Help button on the checkout page opens the offcanvas panel."""
    page.goto(f"{server_url}/#/checkout")
    wait_for_app(page)

    # The help button must be visible in the page header
    help_button = page.locator('button[data-bs-toggle="offcanvas"]').first
    expect(help_button).to_be_visible()

    # Click opens the panel and loads the section-specific resource.
    help_button.click()
    panel = page.locator('.offcanvas.show')
    expect(panel).to_be_visible(timeout=5_000)
    expect(panel.locator('.help-markdown')).to_contain_text('Étape', timeout=5_000)




def test_help_panel_closes_on_dismiss(page: Page, server_url: str, db_session):
    """US1 — Clicking the close button (×) hides the offcanvas panel."""
    page.goto(f"{server_url}/#/checkout")
    wait_for_app(page)
    open_help_panel(page)

    expect(page.locator('.offcanvas.show')).to_be_visible()

    # Dismiss with close button
    close_help_panel(page)

    # Panel must no longer be shown
    offcanvas = page.locator('.offcanvas')
    # After closing, offcanvas should not have class 'show'
    expect(offcanvas).not_to_have_class('show', timeout=2_000)








def test_help_panel_closes_on_navigation(page: Page, server_url: str, db_session):
    """US3 — Navigating away from a page with an open panel closes the panel."""
    page.goto(f"{server_url}/#/checkout")
    wait_for_app(page)
    open_help_panel(page)

    expect(page.locator('.offcanvas.show')).to_be_visible()

    # Navigate to catalog page (this unmounts CirculationPage and mounts CatalogPage)
    page.goto(f"{server_url}/#/catalog")
    wait_for_app(page)
    page.wait_for_timeout(500)

    # The offcanvas from the previous page must not be visible
    # (it is unmounted with its parent component)
    offcanvas_showing = page.locator('.offcanvas.show')
    expect(offcanvas_showing).to_have_count(0, timeout=2_000)
