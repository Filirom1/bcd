"""
E2E Tests: Contextual Help Panel (Feature 001)

Tests cover:
- Panel opens and closes on the checkout page
- Content is page-specific (not generic)
- Panel closes on button dismiss
- Content updates when locale switches (FR/EN)
- Error state shown when content is missing (not a crash)
- All 8 pages have the help button
- Panel closes when navigating to another page
"""
import pytest
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

    # Click opens the panel
    help_button.click()
    expect(page.locator('.offcanvas.show')).to_be_visible(timeout=5_000)


@pytest.mark.e2e_to_be_removed
def test_help_panel_content_is_checkout_specific(page: Page, server_url: str, db_session):
    """US1 — Panel content on checkout page is specific to the checkout workflow."""
    page.goto(f"{server_url}/#/checkout")
    wait_for_app(page)
    open_help_panel(page)

    panel = page.locator('#bcd-help-offcanvas')

    # Wait for content to load (not loading spinner, not error)
    panel.locator('.help-markdown').wait_for(timeout=5_000)

    # Title must reference checkout section
    offcanvas_title = panel.locator('.offcanvas-title')
    expect(offcanvas_title).to_contain_text('Emprunter')

    # Content must contain checkout-specific step text
    content = panel.locator('.help-markdown')
    expect(content).to_contain_text('Étape')


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


@pytest.mark.e2e_to_be_removed
def test_help_panel_updates_on_language_switch(page: Page, server_url: str, db_session):
    """US3 — Switching locale while the panel is open updates the content."""
    page.goto(f"{server_url}/#/checkout")
    wait_for_app(page)
    open_help_panel(page)

    panel = page.locator('#bcd-help-offcanvas')
    panel.locator('.help-markdown').wait_for(timeout=5_000)

    # Title should be in French by default
    expect(panel.locator('.offcanvas-title')).to_contain_text('Emprunter')

    # Temporarily remove backdrop so Playwright can click the sidebar nav switcher
    page.evaluate("const el = document.querySelector('.offcanvas-backdrop'); if (el) el.remove();")

    # Switch to English using the language switcher button
    page.locator('.language-switcher button', has_text='EN').click()

    # Content should reload in English
    panel.locator('.help-markdown').wait_for(timeout=5_000)
    expect(panel.locator('.offcanvas-title')).to_contain_text('Checking out')

    # Switch back to French
    page.locator('.language-switcher button', has_text='FR').click()
    panel.locator('.help-markdown').wait_for(timeout=5_000)
    expect(panel.locator('.offcanvas-title')).to_contain_text('Emprunter')


@pytest.mark.e2e_to_be_removed
def test_help_panel_shows_error_when_content_missing(page: Page, server_url: str, db_session):
    """US3 — When help content cannot be loaded, an error alert is shown (no crash)."""
    # Intercept help file requests and return 404 for both FR and EN.
    # Must be installed BEFORE the HelpPanel mounts, since fetchHelp runs at mount
    # time (watch immediate:true), not when the panel is opened.
    page.route("**/help/**", lambda route: route.fulfill(status=404, body='Not Found'))

    # The conftest `page` fixture already loaded the SPA, so a hash navigation alone
    # would not re-fire the mount-time fetch. Force a full reload with the route active.
    page.goto(f"{server_url}/#/checkout")
    page.reload()
    wait_for_app(page)
    open_help_panel(page)

    panel = page.locator('#bcd-help-offcanvas')

    # Error alert must appear instead of content
    error_alert = panel.locator('.alert-warning')
    expect(error_alert).to_be_visible(timeout=5_000)

    # No crash — panel is still open with the error message
    expect(page.locator('#bcd-help-offcanvas')).to_be_visible()

    # Unblock requests for subsequent tests
    page.unroute("**/help/**")


@pytest.mark.e2e_to_be_removed
def test_all_8_pages_have_help_button(page: Page, server_url: str, db_session):  # noqa: ARG001
    """US2 — All 8 main pages show an 'Aide' help button in the page header."""
    pages = [
        ('/#/checkout',   'Aide'),
        ('/#/return',     'Aide'),
        ('/#/catalog',    'Aide'),
        ('/#/cataloging', 'Aide'),
        ('/#/borrowers',  'Aide'),
        ('/#/classes',    'Aide'),
        ('/#/reports',    'Aide'),
        ('/#/settings',   'Aide'),
    ]

    for route, expected_text in pages:
        page.goto(f"{server_url}{route}")
        wait_for_app(page)
        page.wait_for_timeout(500)  # let Vue render

        help_button = page.locator(
            f'button[data-bs-toggle="offcanvas"]:has-text("{expected_text}")'
        ).first
        expect(help_button).to_be_visible(timeout=5_000)


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
