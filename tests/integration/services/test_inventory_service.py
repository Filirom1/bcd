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


def test_bulk_update_items(db_session: Session):
    """Test bulk update of items and their records."""
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.bcd_api.models.borrower import Borrower

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

    item1 = Item(
        item_id="0001",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        loanable=True,
    )
    item2 = Item(
        item_id="0002",
        bibliographic_record_id=record.id,
        status="on_loan",  # status="on_loan" should skip status update
        condition="good",
        loanable=True,
    )
    db_session.add_all([item1, item2])
    db_session.flush()

    borrower = Borrower(
        borrower_id="B002",
        first_name="Bob",
        last_name="Martin",
        full_name="Bob Martin",
        role="student",
        active=True
    )
    db_session.add(borrower)
    db_session.flush()

    loan = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item2.id,
        bibliographic_record_id=record.id,
        checkout_date=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
        return_date=None
    )
    db_session.add(loan)
    db_session.commit()

    # ACT
    result = inventory_service.bulk_update_items(
        db_session,
        item_ids=["0001", "0002"],
        item_updates={"status": "in_repair", "condition": "damaged"},
        record_updates={"target_audience": "youth", "medium_type": "Livre"}
    )

    # ASSERT
    assert result["items_updated"] == 2
    assert result["items_skipped_on_loan"] == 1
    assert result["records_updated"] == 1
    
    db_session.refresh(item1)
    db_session.refresh(item2)
    db_session.refresh(record)

    # item1 status and condition should be updated
    assert item1.status == "in_repair"
    assert item1.condition == "damaged"

    # item2 is on_loan so its status update should be skipped, but condition should still be updated
    assert item2.status == "on_loan"
    assert item2.condition == "damaged"

    # Record fields should be updated
    assert record.target_audience == "youth"
    assert record.medium_type == "Livre"


def test_delete_items_bulk_and_orphans(db_session: Session):
    """Test bulk deletion of items, skipping on_loan, cancelling holds, and orphan cleanup."""
    from src.bcd_api.models.hold import Hold
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.circulation import CirculationTransaction

    # ARRANGE
    record1 = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
        total_items=2
    )
    record2 = BiblographicRecord(
        isbn="978-2203301160",
        title="Tintin au Tibet",
        authors='["Hergé"]',
        publication_year=1960,
        medium_type="Livre",
        total_items=1
    )
    db_session.add_all([record1, record2])
    db_session.flush()

    item1 = Item(
        item_id="0001",
        bibliographic_record_id=record1.id,
        status="available",
    )
    item2 = Item(
        item_id="0002",
        bibliographic_record_id=record1.id,
        status="on_loan",  # skipped from deletion
    )
    item3 = Item(
        item_id="0003",
        bibliographic_record_id=record2.id,
        status="available",  # will become orphan
    )
    db_session.add_all([item1, item2, item3])
    db_session.flush()

    borrower = Borrower(
        borrower_id="B001",
        first_name="Alice",
        last_name="Dupont",
        full_name="Alice Dupont",
        role="student",
        active=True
    )
    db_session.add(borrower)
    db_session.flush()

    loan = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item2.id,
        bibliographic_record_id=record1.id,
        checkout_date=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
        return_date=None
    )
    db_session.add(loan)
    db_session.flush()

    # Place a hold on record2 (which will be deleted)
    hold = Hold(
        borrower_id=borrower.id,
        bibliographic_record_id=record2.id,
        hold_date=datetime.now(timezone.utc),
        queue_position=1
    )
    db_session.add(hold)
    db_session.commit()

    # ACT 1 - Delete items in bulk
    delete_result = inventory_service.delete_items_bulk(db_session, ["0001", "0002", "0003"])

    # ASSERT 1
    assert delete_result["items_deleted"] == 2  # 0001 and 0003
    assert delete_result["items_skipped_on_loan"] == 1  # 0002
    assert delete_result["holds_cancelled"] == 1  # Hold on record2 cancelled
    assert delete_result["orphan_records_created"] == 1  # record2 total_items became 0

    # Record 1 still has item2, so it's not orphan. Record 2 has 0 items, so it's orphan.
    db_session.refresh(record1)
    db_session.refresh(record2)
    assert record1.total_items == 1
    assert record2.total_items == 0

    # ACT 2 - Get Orphans
    orphans_result = inventory_service.get_orphan_records(db_session)
    assert orphans_result["count"] == 1
    assert orphans_result["records"][0]["id"] == record2.id

    # ACT 3 - Delete Orphans
    cleanup_result = inventory_service.delete_orphan_records(db_session)
    assert cleanup_result["records_deleted"] == 1

    # Record 2 should be gone
    deleted_rec = db_session.query(BiblographicRecord).filter(BiblographicRecord.id == record2.id).first()
    assert deleted_rec is None


def test_get_items_csv(db_session: Session):
    """Test generating CSV for a list of items."""
    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
    )
    db_session.add(record)
    db_session.flush()

    item = Item(
        item_id="0001",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
        call_number="C-EXU",
        shelf_location="Shelf A",
    )
    db_session.add(item)
    db_session.commit()

    # ACT
    csv_str = inventory_service.get_items_csv(db_session, ["0001"])

    # ASSERT
    assert "0001" in csv_str
    assert "Le Petit Prince" in csv_str
    assert "Antoine de Saint-Exupéry" in csv_str
    assert "C-EXU" in csv_str
    assert "Shelf A" in csv_str


# ==================== User Story B.6: New Policy-driven Integration Tests ====================

def test_on_loan_status_without_active_transaction_is_accepted(db_session: Session):
    """Un item avec status=on_loan mais sans transaction active suit la décision item_update_decision."""
    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
    )
    db_session.add(record)
    db_session.flush()

    item = Item(
        item_id="0099",
        bibliographic_record_id=record.id,
        status="on_loan",  # status is "on_loan" but there is NO transaction in DB
        condition="good",
    )
    db_session.add(item)
    db_session.commit()

    # ACT
    result = inventory_service.bulk_update_items(
        db_session,
        item_ids=["0099"],
        item_updates={"status": "available", "condition": "damaged"},
    )

    # ASSERT
    assert result["items_updated"] == 1
    assert result["items_skipped_on_loan"] == 0  # because no active transaction
    db_session.refresh(item)
    assert item.status == "available"
    assert item.condition == "damaged"


def test_item_with_active_transaction_ignored_in_deletion(db_session: Session):
    """Un item avec transaction active (return_date IS NULL) est ignoré en suppression."""
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.circulation import CirculationTransaction

    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
    )
    db_session.add(record)
    db_session.flush()

    item = Item(
        item_id="0098",
        bibliographic_record_id=record.id,
        status="available",  # status says available but we have an active transaction
    )
    db_session.add(item)
    db_session.flush()

    borrower = Borrower(
        borrower_id="B098",
        first_name="Alice",
        last_name="Dupont",
        full_name="Alice Dupont",
        role="student",
        active=True
    )
    db_session.add(borrower)
    db_session.flush()

    loan = CirculationTransaction(
        borrower_id=borrower.id,
        item_id=item.id,
        bibliographic_record_id=record.id,
        checkout_date=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
        return_date=None
    )
    db_session.add(loan)
    db_session.commit()

    # ACT
    delete_result = inventory_service.delete_items_bulk(db_session, ["0098"])

    # ASSERT
    assert delete_result["items_deleted"] == 0
    assert delete_result["items_skipped_on_loan"] == 1


def test_technical_rollback_reverts_batch_mutations(db_session: Session):
    """Rollback technique annule toutes les mutations du batch."""
    # ARRANGE
    record = BiblographicRecord(
        isbn="978-2070408504",
        title="Le Petit Prince",
        authors='["Antoine de Saint-Exupéry"]',
        publication_year=1943,
        medium_type="Livre",
    )
    db_session.add(record)
    db_session.flush()

    item = Item(
        item_id="0097",
        bibliographic_record_id=record.id,
        status="available",
        condition="good",
    )
    db_session.add(item)
    db_session.commit()

    # Let's mock or cause an exception during bulk_update_items to trigger traceback and rollback
    import unittest.mock as mock
    from src.bcd_api.services.inventory.commands import normalize_field_value

    with mock.patch("src.bcd_api.services.inventory.commands.normalize_field_value", side_effect=ValueError("Simulated Error")):
        with pytest.raises(ValueError):
            inventory_service.bulk_update_items(
                db_session,
                item_ids=["0097"],
                item_updates={"condition": "damaged"}
            )

    # ASSERT - should be rolled back to good
    db_session.rollback()  # make sure session is clean
    db_session.refresh(item)
    assert item.condition == "good"

