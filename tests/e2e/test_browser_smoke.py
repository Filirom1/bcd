"""Small browser boundary suite for the Web UI.

The page and component contracts live in ``tests/js``. These checks deliberately
keep only behavior that JSDOM cannot prove: the built SPA booting in Chromium,
client-side navigation, and one real browser-to-API circulation transaction.
"""

import pytest
from playwright.sync_api import expect

from tests.e2e.page_objects.base_page import navigate_and_wait_for_app


@pytest.mark.browser_smoke
def test_spa_boots_and_navigates_core_routes(page, server_url):
    """The served SPA boots and can mount the main lazy-loaded pages."""
    for route in ("checkout", "catalog", "borrowers", "classes", "settings/general"):
        navigate_and_wait_for_app(page, f"{server_url}/#/{route}")
        expect(page.locator(".sidebar")).to_be_visible()
        expect(page.locator(".page-header")).to_be_visible()


@pytest.mark.browser_smoke
def test_checkout_scanner_completes_one_real_transaction(
    circulation_page, borrower_factory, item_factory
):
    """One real scanner path protects browser/API wiring without duplicating JS tests."""
    borrower = borrower_factory.create(
        borrower_id="9001", first_name="Smoke", last_name="Test"
    )
    item, _ = item_factory.create_with_record(
        item_id="9002", title="Smoke test book"
    )

    circulation_page.goto_checkout()
    circulation_page.enter_borrower_id(borrower.borrower_id)
    circulation_page.scan_item(item.item_id, wait_for_feedback=False)

    expect(circulation_page.page.locator("table tbody tr")).not_to_have_count(0)
    expect(circulation_page.page.locator("table.table-sm")).to_contain_text("9002")
    expect(circulation_page.page.locator(".borrower-strip")).to_contain_text("Smoke")
