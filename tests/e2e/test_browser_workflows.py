"""Small, high-value browser-to-server workflows.

These tests deliberately cover behavior that component and API tests cannot prove:
the served SPA, real HTTP requests, and the database state after a mutation.
Keep this file short; broader UI contracts belong in tests/js and business rules
belong in service/API tests.
"""

import re

import pytest
from playwright.sync_api import expect

from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.item import Item


@pytest.mark.browser_smoke
def test_real_return_updates_browser_and_database(
    circulation_page, borrower_factory, item_factory, db_session
):
    """Returning a real loan updates the session list and persistent state."""
    borrower = borrower_factory.create(borrower_id="9101")
    item, record, transaction = item_factory.create_on_loan(borrower.id, title="E2E return book")

    circulation_page.goto_return()
    item_input = circulation_page.page.locator(circulation_page.ITEM_INPUT)
    expect(item_input).to_be_visible()
    item_input.fill(item.item_id)
    item_input.press("Enter")

    returned_row = circulation_page.page.locator("table.table-sm tbody tr").filter(
        has_text=item.item_id
    )
    expect(returned_row).to_have_count(1)
    expect(returned_row).to_contain_text(record.title)

    db_session.expire_all()
    assert db_session.get(Item, item.id).status == "available"
    assert db_session.get(CirculationTransaction, transaction.id).status == "returned"


@pytest.mark.browser_smoke
def test_checkout_already_on_loan_displays_real_business_error(
    circulation_page, borrower_factory, item_factory
):
    """The browser renders the structured API error for an unavailable loan."""
    owner = borrower_factory.create(borrower_id="9102", first_name="Current", last_name="Reader")
    borrower = borrower_factory.create(borrower_id="9103")
    item, _, _ = item_factory.create_on_loan(owner.id, title="Already borrowed book")

    circulation_page.goto_checkout()
    circulation_page.enter_borrower_id(borrower.borrower_id)
    circulation_page.scan_item(item.item_id, wait_for_feedback=False)

    error_toast = circulation_page.page.locator(".toast.bg-danger")
    expect(error_toast).to_be_visible()
    expect(error_toast).to_contain_text("déjà emprunté")


@pytest.mark.browser_smoke
def test_class_create_edit_persists_through_real_api(page, server_url, db_session):
    """A representative class administration workflow survives a reload."""
    page.goto(f"{server_url}/#/classes")
    expect(page.locator(".classes-page")).to_be_visible()

    create_button = page.get_by_role(
        "button", name=re.compile(r"Créer une classe|Create Class", re.IGNORECASE)
    )
    expect(create_button).to_be_visible()
    create_button.click()

    modal = page.locator(".modal.show")
    expect(modal).to_be_visible()
    modal.locator("#class-name").fill("E2E-CP")
    modal.locator("#homeroom-teacher").fill("Mme Test")
    modal.get_by_role("button", name=re.compile(r"Enregistrer|Save", re.IGNORECASE)).click()

    created_row = page.locator("table tbody tr").filter(has_text="E2E-CP")
    expect(created_row).to_have_count(1)

    created_row.locator("button").first.click()
    edit_modal = page.locator(".modal.show")
    expect(edit_modal.locator("#class-name")).to_have_value("E2E-CP")
    edit_modal.locator("#class-name").fill("E2E-CE1")
    edit_modal.get_by_role("button", name=re.compile(r"Enregistrer|Save", re.IGNORECASE)).click()

    expect(page.locator("table tbody tr").filter(has_text="E2E-CE1")).to_have_count(1)
    expect(page.locator("table tbody tr").filter(has_text="E2E-CP")).to_have_count(0)
    assert db_session.query(Class).filter_by(name="E2E-CE1").count() == 1


@pytest.mark.browser_smoke
def test_catalog_search_opens_real_record_detail(catalog_page, item_factory):
    """Catalog search and the record detail modal are wired to the real API."""
    item, record = item_factory.create_with_record(
        title="E2E catalog detail book", item_id="E2E-CAT-1"
    )

    catalog_page.goto()
    catalog_page.search(record.title)

    result = catalog_page.page.locator("table tbody tr").filter(has_text=record.title)
    expect(result).to_have_count(1)
    result.click()

    detail = catalog_page.page.locator(".modal.show")
    expect(detail).to_be_visible()
    expect(detail).to_contain_text(record.title)
    expect(detail).to_contain_text(item.item_id)
