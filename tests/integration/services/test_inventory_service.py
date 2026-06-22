"""Integration tests for Inventory Service.

Tests for collection inventory operations (récolement/weeding).
All tests use AAA pattern: Arrange-Act-Assert.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import ItemNotFoundException
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.services import inventory_service

# ==================== User Story 1: Barcode Scanning Tests ====================


def test_mark_item_inventoried_success(db_session: Session):
    """Test marking single item as inventoried sets last_inventoried_at."""
    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        target_audience="child"
    )
    db_session.add(record)
    db_session.flush()

    item = Item(
        item_id="0785",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=None
    )
    db_session.add(item)
    db_session.commit()

    assert item.last_inventoried_at is None

    # ACT
    result = inventory_service.mark_item_inventoried(db_session, "0785")

    # ASSERT
    assert result.item_id == "0785"
    assert result.last_inventoried_at is not None
    # Verify timestamp is recent (within 5 seconds)
    # Note: SQLite returns timezone-naive datetimes, so we need to make them comparable
    now = datetime.now(timezone.utc)
    if result.last_inventoried_at.tzinfo is None:
        # Convert naive datetime to UTC-aware for comparison
        result_time = result.last_inventoried_at.replace(tzinfo=timezone.utc)
    else:
        result_time = result.last_inventoried_at
    time_diff = (now - result_time).total_seconds()
    assert time_diff < 5
    # Verify database was updated
    db_session.refresh(item)
    assert item.last_inventoried_at is not None


def test_mark_item_inventoried_not_found(db_session: Session):
    """Test marking non-existent item raises ItemNotFoundException."""
    # ARRANGE
    # No item with ID "9999" exists

    # ACT & ASSERT
    with pytest.raises(ItemNotFoundException) as exc_info:
        inventory_service.mark_item_inventoried(db_session, "9999")

    assert "9999" in str(exc_info.value)


# Placeholder for E2E test (runs in Playwright, not pytest)
# def test_scan_barcode_adds_to_table(page):
#     """
#     E2E test: Scan barcode, verify row appears in working table.
#     This test belongs in tests/e2e/test_inventory_page.py
#     """
#     pass


# ==================== User Story 2: Search-Based Item Discovery Tests ====================


def test_search_with_never_inventoried_filter(db_session: Session):
    """Test search with never_inventoried=True returns only items with NULL last_inventoried_at."""
    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        target_audience="child"
    )
    db_session.add(record)
    db_session.flush()

    # Create 3 items: 2 never inventoried, 1 inventoried
    item1 = Item(
        item_id="0001",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=None
    )
    item2 = Item(
        item_id="0002",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=None
    )
    item3 = Item(
        item_id="0003",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=datetime.now(timezone.utc)
    )
    db_session.add_all([item1, item2, item3])
    db_session.commit()

    # ACT
    result = inventory_service.search_items(db_session, never_inventoried=True)

    # ASSERT
    assert result["total_count"] == 2
    assert result["displayed_count"] == 2
    assert result["capped"] is False
    assert len(result["items"]) == 2
    item_ids = {item["item_id"] for item in result["items"]}
    assert item_ids == {"0001", "0002"}


def test_search_with_rotation_filter(db_session: Session):
    """Test search with rotation filter (max_borrows + since_date) returns items with low circulation."""
    # ARRANGE
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.circulation import CirculationTransaction

    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        target_audience="child"
    )
    db_session.add(record)
    db_session.flush()

    # Create 3 items
    item1 = Item(item_id="0001", bibliographic_record_id=record.id, status="available", condition="good", loanable=True)
    item2 = Item(item_id="0002", bibliographic_record_id=record.id, status="available", condition="good", loanable=True)
    item3 = Item(item_id="0003", bibliographic_record_id=record.id, status="available", condition="good", loanable=True)
    db_session.add_all([item1, item2, item3])
    db_session.flush()

    # Create borrower
    borrower = Borrower(
        borrower_id="B001",
        first_name="Test",
        last_name="Student",
        full_name="Test Student",
        role="student",
        active=True
    )
    db_session.add(borrower)
    db_session.flush()

    # Create circulation transactions in the last 6 months
    since_date = datetime.now(timezone.utc) - timedelta(days=180)

    # Item 1: 0 borrows (never borrowed)
    # Item 2: 1 borrow (low circulation)
    tx1 = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item2.id,
        bibliographic_record_id=record.id,
        checkout_date=since_date + timedelta(days=30),
        due_date=since_date + timedelta(days=44)
    )
    # Item 3: 3 borrows (high circulation)
    tx2 = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item3.id,
        bibliographic_record_id=record.id,
        checkout_date=since_date + timedelta(days=10),
        due_date=since_date + timedelta(days=24)
    )
    tx3 = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item3.id,
        bibliographic_record_id=record.id,
        checkout_date=since_date + timedelta(days=60),
        due_date=since_date + timedelta(days=74)
    )
    tx4 = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item3.id,
        bibliographic_record_id=record.id,
        checkout_date=since_date + timedelta(days=90),
        due_date=since_date + timedelta(days=104)
    )
    db_session.add_all([tx1, tx2, tx3, tx4])
    db_session.commit()

    # ACT - search for items with max_borrows <= 1 in the period
    result = inventory_service.search_items(
        db_session,
        max_borrows=1,
        since_date=since_date.date()
    )

    # ASSERT
    assert result["total_count"] == 2
    assert len(result["items"]) == 2
    item_ids = {item["item_id"] for item in result["items"]}
    assert item_ids == {"0001", "0002"}  # Items with 0 and 1 borrows

    # Verify period_loan_count is included
    for item in result["items"]:
        assert "period_loan_count" in item
        if item["item_id"] == "0001":
            assert item["period_loan_count"] == 0
        elif item["item_id"] == "0002":
            assert item["period_loan_count"] == 1


def test_search_results_capped_at_200(db_session: Session):
    """Test search returns max 200 items when more exist, with capped=True."""
    # ARRANGE
    from src.bcd_api.models.system_settings import SystemSettings

    # Ensure inventory_search_result_limit is set to 200
    settings = db_session.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db_session.add(settings)
    settings.inventory_search_result_limit = 200
    db_session.commit()

    # Create 1 record
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        target_audience="child"
    )
    db_session.add(record)
    db_session.flush()

    # Create 250 items
    items = [
        Item(
            item_id=f"{i:04d}",
            bibliographic_record_id=record.id,
            status="available",
            condition="good",
            loanable=True
        )
        for i in range(1, 251)
    ]
    db_session.add_all(items)
    db_session.commit()

    # ACT
    result = inventory_service.search_items(db_session)

    # ASSERT
    assert result["total_count"] == 250
    assert result["displayed_count"] == 200
    assert result["capped"] is True
    assert len(result["items"]) == 200


def test_search_with_no_limit_bypasses_cap(db_session: Session):
    """Test search with no_limit=True returns all items without capping."""
    # ARRANGE
    from src.bcd_api.models.system_settings import SystemSettings

    # Ensure inventory_search_result_limit is set to 200
    settings = db_session.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db_session.add(settings)
    settings.inventory_search_result_limit = 200
    db_session.commit()

    # Create 1 record
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        target_audience="child"
    )
    db_session.add(record)
    db_session.flush()

    # Create 250 items (more than the 200 cap)
    items = [
        Item(
            item_id=f"{i:04d}",
            bibliographic_record_id=record.id,
            status="available",
            condition="good",
            loanable=True
        )
        for i in range(1, 251)
    ]
    db_session.add_all(items)
    db_session.commit()

    # ACT - search with no_limit=True
    result = inventory_service.search_items(db_session, no_limit=True)

    # ASSERT
    assert result["total_count"] == 250
    assert result["displayed_count"] == 250  # All items returned
    assert result["capped"] is False  # No capping applied
    assert len(result["items"]) == 250  # All items in result


def test_bulk_mark_inventoried(db_session: Session):
    """Test bulk_mark_inventoried updates all valid items and reports not found."""
    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        target_audience="child"
    )
    db_session.add(record)
    db_session.flush()

    # Create 3 items
    item1 = Item(
        item_id="0001",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=None
    )
    item2 = Item(
        item_id="0002",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=None
    )
    item3 = Item(
        item_id="0003",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
        last_inventoried_at=None
    )
    db_session.add_all([item1, item2, item3])
    db_session.commit()

    # ACT - bulk mark with 3 valid + 2 invalid item IDs
    item_ids = ["0001", "0002", "0003", "9998", "9999"]
    result = inventory_service.bulk_mark_inventoried(db_session, item_ids)

    # ASSERT
    assert result["items_updated"] == 3
    assert set(result["items_not_found"]) == {"9998", "9999"}
    assert result["timestamp"] is not None

    # Verify database was updated
    db_session.refresh(item1)
    db_session.refresh(item2)
    db_session.refresh(item3)
    assert item1.last_inventoried_at is not None
    assert item2.last_inventoried_at is not None
    assert item3.last_inventoried_at is not None

    # Verify all items have same timestamp
    assert item1.last_inventoried_at == item2.last_inventoried_at == item3.last_inventoried_at
