"""Browser boundary coverage for the complete periodical cataloging flow."""

import pytest

from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item


@pytest.mark.browser_smoke
def test_find_notice_adds_one_periodical_copy_after_unknown_barcode(
    page, server_url, db_session, item_factory
):
    """Scan press barcode, find Wapiti locally, then add issue 440 once."""
    record = item_factory.create_record(
        title="Wapiti", isbn="issn:0984-2314", medium_type="Périodique", publisher="Milan"
    )
    existing = item_factory.create(bibliographic_record_id=record.id, item_id="BCD-OLD")
    existing.call_number = "414"
    db_session.commit()

    page.goto(f"{server_url}/#/cataloging")
    page.locator("#notice-search-input").fill("3780237306003")
    page.locator("#notice-search-input").press("Enter")
    page.locator('[data-testid="unsupported-barcode-message"]').wait_for()

    page.locator("#title-search-input").fill("Wapiti")
    page.locator("#title-search-input").press("Enter")
    page.locator('[data-testid="local-notice-results"]').wait_for()
    page.get_by_role("button", name="Utiliser cette notice").click()

    item_form = page.locator(".item-barcode-input")
    item_form.locator("input").nth(0).fill("440")
    item_form.locator("#item-barcode-input").fill("BCD-440")
    item_form.locator("button[type=submit]").click()

    item_form.get_by_text("BCD-440", exact=True).wait_for()
    assert db_session.query(BibliographicRecord).filter_by(title="Wapiti").count() == 1
    assert db_session.query(Item).filter_by(item_id="BCD-440").count() == 1
    assert db_session.query(Item).filter_by(item_id="BCD-440").one().call_number == "440"
