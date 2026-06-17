"""
Integration tests for circulation history pagination and date filtering.

Tests cover:
- US1: Borrower history pagination (T005)
- US2: Item history pagination (T010)
- US3: Date range filtering for both (T015)

All tests use service-layer integration (db_session fixture, AAA pattern).
"""

import pytest
from datetime import date, datetime, timedelta
import json

from src.bcd_api.services import circulation_service
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.item import Item
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.class_model import Class


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

def _make_class(db):
    cls = Class(name="CP-A", homeroom_teacher="Mme Dupont")
    db.add(cls)
    db.flush()
    return cls


def _make_borrower(db, borrower_id, cls_id):
    b = Borrower(
        borrower_id=borrower_id,
        first_name="Test",
        last_name="Borrower",
        full_name=f"Test Borrower {borrower_id}",
        role="student",
        class_id=cls_id,
        active=True,
    )
    db.add(b)
    db.flush()
    return b


def _make_biblio(db, title="Test Book"):
    rec = BiblographicRecord(
        title=title,
        authors=json.dumps(["Author, Test"]),
        publisher="Editions Test",
        publication_year=2020,
        language="fr",
        medium_type="Livre",
    )
    db.add(rec)
    db.flush()
    return rec


def _make_item(db, item_id, biblio_id):
    item = Item(
        item_id=item_id,
        bibliographic_record_id=biblio_id,
        status="available",
        loanable=True,
    )
    db.add(item)
    db.flush()
    return item


def _make_completed_transaction(db, borrower_id_int, item_id_int, biblio_id_int,
                                 checkout_date, due_date, return_date):
    """Create a completed (returned) transaction."""
    tx = CirculationTransaction(
        borrower_id=borrower_id_int,
        item_id=item_id_int,
        bibliographic_record_id=biblio_id_int,
        checkout_date=checkout_date,
        due_date=due_date,
        return_date=return_date,
        status="returned",
    )
    db.add(tx)
    return tx


def _make_active_transaction(db, borrower_id_int, item_id_int, biblio_id_int,
                              checkout_date, due_date):
    """Create an active (not returned) transaction."""
    tx = CirculationTransaction(
        borrower_id=borrower_id_int,
        item_id=item_id_int,
        bibliographic_record_id=biblio_id_int,
        checkout_date=checkout_date,
        due_date=due_date,
        return_date=None,
        status="active",
    )
    db.add(tx)
    return tx


def _build_borrower_with_history(db, count, prefix="BH", biblio=None):
    """
    Create a borrower with `count` completed transactions.
    Returns (borrower, item, biblio_record).
    Checkout dates are spread from 'count' days ago to today.
    """
    cls = _make_class(db)
    borrower = _make_borrower(db, prefix, cls.id)
    if biblio is None:
        biblio = _make_biblio(db)
    item = _make_item(db, prefix + "_ITEM", biblio.id)

    base = datetime.now()
    for i in range(count):
        # Space checkouts: oldest first
        co_date = base - timedelta(days=count - i)
        ret_date = co_date + timedelta(days=10)
        due = (co_date + timedelta(days=14)).date()
        _make_completed_transaction(
            db,
            borrower.id, item.id, biblio.id,
            co_date, due, ret_date,
        )

    db.commit()
    return borrower, item, biblio


def _build_item_with_history(db, count, prefix="IH", borrower=None):
    """
    Create an item with `count` completed transactions.
    Returns (item, biblio_record, borrower).
    """
    cls = _make_class(db)
    if borrower is None:
        borrower = _make_borrower(db, prefix + "_BRW", cls.id)
    biblio = _make_biblio(db, title="Item History Book")
    item = _make_item(db, prefix + "_ITEM", biblio.id)

    base = datetime.now()
    for i in range(count):
        co_date = base - timedelta(days=count - i)
        ret_date = co_date + timedelta(days=10)
        due = (co_date + timedelta(days=14)).date()
        _make_completed_transaction(
            db,
            borrower.id, item.id, biblio.id,
            co_date, due, ret_date,
        )

    db.commit()
    return item, biblio, borrower


# ---------------------------------------------------------------------------
# US1: Borrower history pagination (T005)
# ---------------------------------------------------------------------------

class TestBorrowerHistoryPagination:
    """US1: Borrower can see complete paginated history."""

    def test_borrower_history_returns_first_page(self, db_session):
        """25 completed loans → 20 results on page 1."""
        borrower, _, _ = _build_borrower_with_history(db_session, 25, prefix="BH1")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id, page=1, page_size=20
        )

        assert len(result.history) == 20
        assert result.pagination.page == 1
        assert result.pagination.page_size == 20

    def test_borrower_history_returns_correct_second_page(self, db_session):
        """25 records → page 2 has the remaining 5."""
        borrower, _, _ = _build_borrower_with_history(db_session, 25, prefix="BH2")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id, page=2, page_size=20
        )

        assert len(result.history) == 5
        assert result.pagination.page == 2

    def test_borrower_history_excludes_active_loans(self, db_session):
        """Active loan must not appear in completed history."""
        cls = _make_class(db_session)
        borrower = _make_borrower(db_session, "BH3", cls.id)
        biblio = _make_biblio(db_session)
        item = _make_item(db_session, "BH3_ITEM", biblio.id)

        # One completed, one active
        co = datetime.now() - timedelta(days=20)
        _make_completed_transaction(
            db_session, borrower.id, item.id, biblio.id,
            co, (co + timedelta(days=14)).date(), co + timedelta(days=10)
        )

        item2 = _make_item(db_session, "BH3_ITEM2", biblio.id)
        _make_active_transaction(
            db_session, borrower.id, item2.id, biblio.id,
            datetime.now() - timedelta(days=2),
            date.today() + timedelta(days=12),
        )
        db_session.commit()

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id, page=1, page_size=20
        )

        assert len(result.history) == 1
        assert result.pagination.total_items == 1

    def test_borrower_history_sorted_checkout_date_desc(self, db_session):
        """Most recent checkout appears first."""
        borrower, _, _ = _build_borrower_with_history(db_session, 5, prefix="BH4")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id, page=1, page_size=20
        )

        dates = [item.checkout_date for item in result.history]
        assert dates == sorted(dates, reverse=True), "History must be newest first"

    def test_borrower_history_pagination_meta_correct(self, db_session):
        """25 records, page_size=20 → total_items=25, total_pages=2."""
        borrower, _, _ = _build_borrower_with_history(db_session, 25, prefix="BH5")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id, page=1, page_size=20
        )

        assert result.pagination.total_items == 25
        assert result.pagination.total_pages == 2

    def test_borrower_history_single_page_no_overflow(self, db_session):
        """5 records with page_size=20 → total_pages=1, 5 items returned."""
        borrower, _, _ = _build_borrower_with_history(db_session, 5, prefix="BH6")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id, page=1, page_size=20
        )

        assert len(result.history) == 5
        assert result.pagination.total_pages == 1
        assert result.pagination.total_items == 5


# ---------------------------------------------------------------------------
# US2: Item history pagination (T010)
# ---------------------------------------------------------------------------

class TestItemHistoryPagination:
    """US2: Item circulation history is fully paginated."""

    def test_item_history_first_page(self, db_session):
        """25 completed loans → 20 on page 1."""
        item, _, _ = _build_item_with_history(db_session, 25, prefix="IH1")

        result = circulation_service.get_item_circulation_history(
            db_session, item.item_id, page=1, page_size=20
        )

        assert len(result.history) == 20
        assert result.pagination.total_items == 25

    def test_item_history_shows_current_loan(self, db_session):
        """Active loan appears in current_loan, not in history."""
        item, biblio, borrower = _build_item_with_history(db_session, 2, prefix="IH2")

        # Add an active loan
        _make_active_transaction(
            db_session, borrower.id, item.id, biblio.id,
            datetime.now() - timedelta(days=1),
            date.today() + timedelta(days=13),
        )
        item.status = "on_loan"
        db_session.commit()

        result = circulation_service.get_item_circulation_history(
            db_session, item.item_id, page=1, page_size=20
        )

        assert result.current_loan is not None
        assert result.current_loan.return_date is None
        # Active loan must not be in history
        assert result.pagination.total_items == 2
        assert len(result.history) == 2

    def test_item_history_empty_never_borrowed(self, db_session):
        """Item never borrowed → current_loan=None, history=[], total_items=0."""
        biblio = _make_biblio(db_session)
        item = _make_item(db_session, "IH3_NEW", biblio.id)
        db_session.commit()

        result = circulation_service.get_item_circulation_history(
            db_session, item.item_id, page=1, page_size=20
        )

        assert result.current_loan is None
        assert result.history == []
        assert result.pagination.total_items == 0

    def test_item_history_sorted_checkout_date_desc(self, db_session):
        """Most recent completed transaction appears first."""
        item, _, _ = _build_item_with_history(db_session, 5, prefix="IH4")

        result = circulation_service.get_item_circulation_history(
            db_session, item.item_id, page=1, page_size=20
        )

        dates = [h.checkout_date for h in result.history]
        assert dates == sorted(dates, reverse=True)

    def test_item_history_pagination_meta_correct(self, db_session):
        """21 records, page_size=20 → total_pages=2 (ceiling division)."""
        item, _, _ = _build_item_with_history(db_session, 21, prefix="IH5")

        result = circulation_service.get_item_circulation_history(
            db_session, item.item_id, page=1, page_size=20
        )

        assert result.pagination.total_items == 21
        assert result.pagination.total_pages == 2


# ---------------------------------------------------------------------------
# US3: Date range filtering (T015)
# ---------------------------------------------------------------------------

class TestHistoryDateFilters:
    """US3: Date filters narrow results on both history endpoints."""

    def _make_dated_history(self, db, prefix):
        """Create borrower and item with transactions in 2023, 2024, 2025."""
        cls = _make_class(db)
        borrower = _make_borrower(db, prefix, cls.id)
        biblio = _make_biblio(db)
        item = _make_item(db, prefix + "_ITEM", biblio.id)

        for year in [2023, 2024, 2025]:
            co = datetime(year, 3, 1, 10, 0)
            ret = co + timedelta(days=10)
            due = (co + timedelta(days=14)).date()
            _make_completed_transaction(db, borrower.id, item.id, biblio.id, co, due, ret)

        db.commit()
        return borrower, item, biblio

    def test_borrower_history_date_from_filter(self, db_session):
        """Only transactions on/after date_from returned."""
        borrower, _, _ = self._make_dated_history(db_session, "BDF1")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id,
            page=1, page_size=20,
            date_from=date(2024, 1, 1),
        )

        assert result.pagination.total_items == 2
        for item in result.history:
            assert item.checkout_date.year >= 2024

    def test_borrower_history_date_to_filter(self, db_session):
        """Only transactions on/before date_to returned."""
        borrower, _, _ = self._make_dated_history(db_session, "BDF2")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id,
            page=1, page_size=20,
            date_to=date(2024, 12, 31),
        )

        assert result.pagination.total_items == 2
        for item in result.history:
            assert item.checkout_date.year <= 2024

    def test_borrower_history_date_range_filter(self, db_session):
        """Both date_from and date_to applied together."""
        borrower, _, _ = self._make_dated_history(db_session, "BDF3")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id,
            page=1, page_size=20,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
        )

        assert result.pagination.total_items == 1
        assert result.history[0].checkout_date.year == 2024

    def test_borrower_history_empty_for_period(self, db_session):
        """Date range with no transactions → total_items=0."""
        borrower, _, _ = self._make_dated_history(db_session, "BDF4")

        result = circulation_service.get_borrower_circulation_history(
            db_session, borrower.borrower_id,
            page=1, page_size=20,
            date_from=date(2020, 1, 1),
            date_to=date(2020, 12, 31),
        )

        assert result.pagination.total_items == 0
        assert result.history == []

    def test_item_history_date_filter(self, db_session):
        """Date filter applies only to completed transactions, not current_loan."""
        cls = _make_class(db_session)
        borrower = _make_borrower(db_session, "IDF1_BRW", cls.id)
        biblio = _make_biblio(db_session)
        item = _make_item(db_session, "IDF1_ITEM", biblio.id)

        # Two old completed loans (2023)
        for i in range(2):
            co = datetime(2023, 3 + i, 1, 10, 0)
            ret = co + timedelta(days=10)
            _make_completed_transaction(
                db_session, borrower.id, item.id, biblio.id,
                co, (co + timedelta(days=14)).date(), ret
            )

        # One recent active loan (today) — must not be filtered
        _make_active_transaction(
            db_session, borrower.id, item.id, biblio.id,
            datetime.now() - timedelta(days=1),
            date.today() + timedelta(days=13),
        )
        item.status = "on_loan"
        db_session.commit()

        result = circulation_service.get_item_circulation_history(
            db_session, item.item_id,
            page=1, page_size=20,
            date_from=date(2025, 1, 1),
        )

        # Filter on completed only → 0 completed matches; current_loan unaffected
        assert result.pagination.total_items == 0
        assert result.history == []
        assert result.current_loan is not None
