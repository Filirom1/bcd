"""Integration tests for report service."""

from datetime import date, datetime, timedelta

import pytest

from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.hold import Hold, HoldStatus
from src.bcd_api.models.item import Item
from src.bcd_api.services import report_service


class TestOverdueReports:
    """Test overdue items reporting."""

    def test_get_overdue_items_basic(self, db_session):
        """Test getting overdue items."""
        # Create test data
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.flush()

        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        biblio = BibliographicRecord(title="Test Book", authors="Test Author", medium_type="Livre")
        db_session.add(biblio)
        db_session.flush()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.flush()

        # Create overdue circulation
        circulation = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.utcnow() - timedelta(days=20),
            due_date=date.today() - timedelta(days=5),
            checked_out_by="test",
        )
        db_session.add(circulation)
        db_session.commit()

        # Test
        overdue, total = report_service.get_overdue_items(db_session)

        assert len(overdue) == 1
        assert total == 1
        assert overdue[0]["item_id"] == "785"
        assert overdue[0]["days_overdue"] == 5

    def test_get_overdue_items_no_overdue(self, db_session):
        """Test when there are no overdue items."""
        overdue, total = report_service.get_overdue_items(db_session)
        assert len(overdue) == 0
        assert total == 0

    def test_get_overdue_items_filter_by_class(self, db_session):
        """Test filtering overdue items by class."""
        # Create two classes
        class_a = Class(name="CP-A")
        class_b = Class(name="CP-B")
        db_session.add_all([class_a, class_b])
        db_session.flush()

        # Create borrowers in different classes
        borrower_a = Borrower(
            borrower_id="101",
            first_name="Student",
            last_name="A",
            full_name="Student A",
            role="student",
            class_id=class_a.id,
            active=True,
        )
        borrower_b = Borrower(
            borrower_id="102",
            first_name="Student",
            last_name="B",
            full_name="Student B",
            role="student",
            class_id=class_b.id,
            active=True,
        )
        db_session.add_all([borrower_a, borrower_b])
        db_session.flush()

        # Create overdue items for each borrower
        for idx, borrower in enumerate([borrower_a, borrower_b]):
            biblio = BibliographicRecord(title=f"Book {idx}", medium_type="Livre")
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{idx}",
                bibliographic_record_id=biblio.id,
                status="on_loan",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            circulation = CirculationTransaction(
                borrower_id=borrower.id,
                item_id=item.id,
                bibliographic_record_id=biblio.id,
                checkout_date=datetime.utcnow() - timedelta(days=20),
                due_date=date.today() - timedelta(days=5),
                checked_out_by="test",
            )
            db_session.add(circulation)

        db_session.commit()

        # Test filtering by class
        overdue_class_a, total_a = report_service.get_overdue_items(db_session, class_name="CP-A")
        assert len(overdue_class_a) == 1
        assert total_a == 1
        assert overdue_class_a[0]["class_name"] == "CP-A"

        overdue_class_b, total_b = report_service.get_overdue_items(db_session, class_name="CP-B")
        assert len(overdue_class_b) == 1
        assert total_b == 1
        assert overdue_class_b[0]["class_name"] == "CP-B"

    def test_get_overdue_summary_by_class(self, db_session):
        """Test getting overdue summary grouped by class."""
        # Create classes
        class_a = Class(name="CP-A")
        class_b = Class(name="CP-B")
        db_session.add_all([class_a, class_b])
        db_session.flush()

        # Create borrowers
        borrower_a = Borrower(
            borrower_id="101",
            first_name="Student",
            last_name="A",
            full_name="Student A",
            role="student",
            class_id=class_a.id,
            active=True,
        )
        borrower_b = Borrower(
            borrower_id="102",
            first_name="Student",
            last_name="B",
            full_name="Student B",
            role="student",
            class_id=class_b.id,
            active=True,
        )
        db_session.add_all([borrower_a, borrower_b])
        db_session.flush()

        # Create 2 overdue items for class A, 1 for class B
        for idx in range(3):
            borrower = borrower_a if idx < 2 else borrower_b
            biblio = BibliographicRecord(title=f"Book {idx}", medium_type="Livre")
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{idx}",
                bibliographic_record_id=biblio.id,
                status="on_loan",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            circulation = CirculationTransaction(
                borrower_id=borrower.id,
                item_id=item.id,
                bibliographic_record_id=biblio.id,
                checkout_date=datetime.utcnow() - timedelta(days=20),
                due_date=date.today() - timedelta(days=5),
                checked_out_by="test",
            )
            db_session.add(circulation)

        db_session.commit()

        # Test summary
        summary = report_service.get_overdue_summary_by_class(db_session)
        assert len(summary) == 2
        assert summary[0]["class_name"] == "CP-A"
        assert summary[0]["overdue_count"] == 2
        assert summary[1]["class_name"] == "CP-B"
        assert summary[1]["overdue_count"] == 1


class TestNeverBorrowedReport:
    """Test never borrowed items reporting."""

    def test_get_never_borrowed_items(self, db_session):
        """Test getting items that have never been borrowed."""
        biblio = BibliographicRecord(
            title="Never Borrowed Book",
            authors="Test Author",
            medium_type="Livre",
            publication_year=2020,
        )
        db_session.add(biblio)
        db_session.flush()

        item = Item(
            item_id="999",
            bibliographic_record_id=biblio.id,
            status="available",
            loanable=True,
            call_number="000.000",
        )
        db_session.add(item)
        db_session.commit()

        # Test
        never_borrowed, total = report_service.get_never_borrowed_items(db_session)

        assert len(never_borrowed) == 1
        assert never_borrowed[0]["item_id"] == "999"


class TestMostBorrowedReport:
    """Test most borrowed titles reporting."""

    def test_get_most_borrowed_titles(self, db_session):
        """Test getting most borrowed titles."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        # Create 2 books with different circulation counts
        for idx in [0, 1]:
            biblio = BibliographicRecord(
                title=f"Book {idx}",
                authors="Test Author",
                medium_type="Livre",
                publication_year=2020,
            )
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{idx}",
                bibliographic_record_id=biblio.id,
                status="available",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            # Book 0: 3 circulations, Book 1: 1 circulation
            count = 3 if idx == 0 else 1
            for circ_num in range(count):
                circulation = CirculationTransaction(
                    borrower_id=borrower.id,
                    item_id=item.id,
                    bibliographic_record_id=biblio.id,
                    checkout_date=datetime.utcnow() - timedelta(days=30 * (circ_num + 1)),
                    due_date=date.today() - timedelta(days=30 * (circ_num + 1) - 14),
                    return_date=datetime.utcnow() - timedelta(days=30 * (circ_num + 1) - 14),
                    checked_out_by="test",
                )
                db_session.add(circulation)

        db_session.commit()

        # Test
        most_borrowed, total = report_service.get_most_borrowed_titles(
            db_session, period="all-time", limit=10
        )

        assert len(most_borrowed) == 2
        assert most_borrowed[0]["title"] == "Book 0"
        assert most_borrowed[0]["checkout_count"] == 3
        assert most_borrowed[1]["title"] == "Book 1"
        assert most_borrowed[1]["checkout_count"] == 1


class TestCirculationStatistics:
    """Test circulation statistics reporting."""

    def test_get_circulation_statistics(self, db_session):
        """Test getting overall circulation statistics."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        # Create items and circulations
        for i in range(3):
            biblio = BibliographicRecord(title=f"Book {i}", medium_type="Livre")
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{i}",
                bibliographic_record_id=biblio.id,
                status="available",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            if i == 0:
                # Active loan
                circ = CirculationTransaction(
                    borrower_id=borrower.id,
                    item_id=item.id,
                    bibliographic_record_id=biblio.id,
                    checkout_date=datetime.utcnow() - timedelta(days=5),
                    due_date=date.today() + timedelta(days=9),
                    checked_out_by="test",
                )
            elif i == 1:
                # Overdue loan
                circ = CirculationTransaction(
                    borrower_id=borrower.id,
                    item_id=item.id,
                    bibliographic_record_id=biblio.id,
                    checkout_date=datetime.utcnow() - timedelta(days=20),
                    due_date=date.today() - timedelta(days=6),
                    checked_out_by="test",
                )
            else:
                # Returned on time
                circ = CirculationTransaction(
                    borrower_id=borrower.id,
                    item_id=item.id,
                    bibliographic_record_id=biblio.id,
                    checkout_date=datetime.utcnow() - timedelta(days=30),
                    due_date=date.today() - timedelta(days=16),
                    return_date=datetime.utcnow() - timedelta(days=17),
                    checked_out_by="test",
                )
            db_session.add(circ)

        db_session.commit()

        # Test
        stats = report_service.get_circulation_statistics(db_session, period="year")

        assert stats["total_checkouts"] == 3
        assert stats["items_on_loan"] == 2
        assert stats["overdue_items"] == 1


class TestBorrowerStatistics:
    """Test borrower-specific statistics."""

    def test_get_borrower_statistics(self, db_session):
        """Test getting statistics for a borrower."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        # Create items
        for i in range(2):
            biblio = BibliographicRecord(title=f"Book {i}", medium_type="Livre")
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{i}",
                bibliographic_record_id=biblio.id,
                status="available",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            if i == 0:
                # Current loan
                circ = CirculationTransaction(
                    borrower_id=borrower.id,
                    item_id=item.id,
                    bibliographic_record_id=biblio.id,
                    checkout_date=datetime.utcnow() - timedelta(days=5),
                    due_date=date.today() + timedelta(days=9),
                    checked_out_by="test",
                )
            else:
                # Returned
                circ = CirculationTransaction(
                    borrower_id=borrower.id,
                    item_id=item.id,
                    bibliographic_record_id=biblio.id,
                    checkout_date=datetime.utcnow() - timedelta(days=30),
                    due_date=date.today() - timedelta(days=16),
                    return_date=datetime.utcnow() - timedelta(days=17),
                    checked_out_by="test",
                )
            db_session.add(circ)

        db_session.commit()

        # Test
        stats = report_service.get_borrower_statistics(db_session, borrower.id)

        assert stats["total_checkouts"] == 2
        assert stats["current_loans"] == 1


class TestHoldsReport:
    """Test holds/reservations reporting."""

    def test_get_holds_report_all(self, db_session):
        """Test getting active holds (excludes fulfilled/cancelled by default)."""
        # Create test data
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.flush()

        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        biblio = BibliographicRecord(
            title="Reserved Book",
            authors="Test Author",
            medium_type="Livre"
        )
        db_session.add(biblio)
        db_session.flush()

        # Create holds with different statuses (active + completed)
        hold_waiting = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.WAITING,
            hold_date=datetime.utcnow(),
            queue_position=1,
        )
        hold_ready = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.READY,
            hold_date=datetime.utcnow() - timedelta(days=2),
            queue_position=1,
            available_date=datetime.utcnow(),
            expiration_date=date.today() + timedelta(days=15),
        )
        hold_fulfilled = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.FULFILLED,
            hold_date=datetime.utcnow() - timedelta(days=10),
            queue_position=1,
        )
        hold_cancelled = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.CANCELLED,
            hold_date=datetime.utcnow() - timedelta(days=5),
            queue_position=1,
        )
        db_session.add_all([hold_waiting, hold_ready, hold_fulfilled, hold_cancelled])
        db_session.commit()

        # Test - by default, should only return active holds (waiting, ready, expired)
        # and exclude completed holds (fulfilled, cancelled)
        holds = report_service.get_holds_report(db_session)

        assert len(holds) == 2  # Only waiting and ready
        assert holds[0]["borrower_name"] == "Test User"
        assert holds[0]["class_name"] == "CP-A"
        assert holds[0]["title"] == "Reserved Book"
        # Verify no fulfilled or cancelled in results
        statuses = [h["status"] for h in holds]
        assert "fulfilled" not in statuses
        assert "cancelled" not in statuses

    def test_get_holds_report_filter_by_status(self, db_session):
        """Test filtering holds by status."""
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.flush()

        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        biblio = BibliographicRecord(title="Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.flush()

        # Create holds with different statuses
        hold_waiting = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.WAITING,
            hold_date=datetime.utcnow(),
            queue_position=1,
        )
        hold_ready = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.READY,
            hold_date=datetime.utcnow() - timedelta(days=2),
            queue_position=1,
            available_date=datetime.utcnow(),
            expiration_date=date.today() + timedelta(days=15),
        )
        hold_cancelled = Hold(
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.CANCELLED,
            hold_date=datetime.utcnow() - timedelta(days=5),
            queue_position=1,
        )
        db_session.add_all([hold_waiting, hold_ready, hold_cancelled])
        db_session.commit()

        # Test filtering by status
        waiting_holds = report_service.get_holds_report(db_session, status="waiting")
        assert len(waiting_holds) == 1
        assert waiting_holds[0]["status"] == "waiting"

        ready_holds = report_service.get_holds_report(db_session, status="ready")
        assert len(ready_holds) == 1
        assert ready_holds[0]["status"] == "ready"
        assert "expiration_date" in ready_holds[0]
        assert "days_until_expiration" in ready_holds[0]

        cancelled_holds = report_service.get_holds_report(db_session, status="cancelled")
        assert len(cancelled_holds) == 1
        assert cancelled_holds[0]["status"] == "cancelled"

    def test_get_holds_report_filter_by_class(self, db_session):
        """Test filtering holds by class."""
        # Create two classes
        class_a = Class(name="CP-A")
        class_b = Class(name="CP-B")
        db_session.add_all([class_a, class_b])
        db_session.flush()

        # Create borrowers in different classes
        borrower_a = Borrower(
            borrower_id="101",
            first_name="Student",
            last_name="A",
            full_name="Student A",
            role="student",
            class_id=class_a.id,
            active=True,
        )
        borrower_b = Borrower(
            borrower_id="102",
            first_name="Student",
            last_name="B",
            full_name="Student B",
            role="student",
            class_id=class_b.id,
            active=True,
        )
        db_session.add_all([borrower_a, borrower_b])
        db_session.flush()

        biblio = BibliographicRecord(title="Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.flush()

        # Create holds for each borrower
        hold_a = Hold(
            borrower_id=borrower_a.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.WAITING,
            hold_date=datetime.utcnow(),
            queue_position=1,
        )
        hold_b = Hold(
            borrower_id=borrower_b.id,
            bibliographic_record_id=biblio.id,
            status=HoldStatus.WAITING,
            hold_date=datetime.utcnow(),
            queue_position=2,
        )
        db_session.add_all([hold_a, hold_b])
        db_session.commit()

        # Test filtering by class
        holds_class_a = report_service.get_holds_report(db_session, class_name="CP-A")
        assert len(holds_class_a) == 1
        assert holds_class_a[0]["class_name"] == "CP-A"

        holds_class_b = report_service.get_holds_report(db_session, class_name="CP-B")
        assert len(holds_class_b) == 1
        assert holds_class_b[0]["class_name"] == "CP-B"


class TestActiveLoansReport:
    """Test active loans reporting."""

    def test_get_active_loans_all(self, db_session):
        """Test getting all active loans."""
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.flush()

        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        # Create active loan
        biblio = BibliographicRecord(title="Checked Out Book", authors="Test Author", medium_type="Livre")
        db_session.add(biblio)
        db_session.flush()

        item = Item(
            item_id="123",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.flush()

        circulation = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.utcnow() - timedelta(days=5),
            due_date=date.today() + timedelta(days=9),
            checked_out_by="test",
        )
        db_session.add(circulation)
        db_session.commit()

        # Test
        active_loans = report_service.get_active_loans(db_session)

        assert len(active_loans) == 1
        assert active_loans[0]["item_id"] == "123"
        assert active_loans[0]["borrower_name"] == "Test User"
        assert active_loans[0]["class_name"] == "CP-A"
        assert active_loans[0]["title"] == "Checked Out Book"
        assert active_loans[0]["days_until_due"] == 9
        assert active_loans[0]["is_overdue"] is False

    def test_get_active_loans_filter_by_class(self, db_session):
        """Test filtering active loans by class."""
        # Create two classes
        class_a = Class(name="CP-A")
        class_b = Class(name="CP-B")
        db_session.add_all([class_a, class_b])
        db_session.flush()

        # Create borrowers in different classes
        borrower_a = Borrower(
            borrower_id="101",
            first_name="Student",
            last_name="A",
            full_name="Student A",
            role="student",
            class_id=class_a.id,
            active=True,
        )
        borrower_b = Borrower(
            borrower_id="102",
            first_name="Student",
            last_name="B",
            full_name="Student B",
            role="student",
            class_id=class_b.id,
            active=True,
        )
        db_session.add_all([borrower_a, borrower_b])
        db_session.flush()

        # Create active loans for each borrower
        for idx, borrower in enumerate([borrower_a, borrower_b]):
            biblio = BibliographicRecord(title=f"Book {idx}", medium_type="Livre")
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{idx}",
                bibliographic_record_id=biblio.id,
                status="on_loan",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            circulation = CirculationTransaction(
                borrower_id=borrower.id,
                item_id=item.id,
                bibliographic_record_id=biblio.id,
                checkout_date=datetime.utcnow() - timedelta(days=5),
                due_date=date.today() + timedelta(days=9),
                checked_out_by="test",
            )
            db_session.add(circulation)

        db_session.commit()

        # Test filtering by class
        loans_class_a = report_service.get_active_loans(db_session, class_name="CP-A")
        assert len(loans_class_a) == 1
        assert loans_class_a[0]["class_name"] == "CP-A"

        loans_class_b = report_service.get_active_loans(db_session, class_name="CP-B")
        assert len(loans_class_b) == 1
        assert loans_class_b[0]["class_name"] == "CP-B"

    def test_get_active_loans_excludes_returned(self, db_session):
        """Test that returned items are excluded from active loans."""
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.flush()

        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        # Create one active loan and one returned loan
        for idx, is_returned in enumerate([False, True]):
            biblio = BibliographicRecord(title=f"Book {idx}", medium_type="Livre")
            db_session.add(biblio)
            db_session.flush()

            item = Item(
                item_id=f"78{idx}",
                bibliographic_record_id=biblio.id,
                status="available" if is_returned else "on_loan",
                loanable=True,
            )
            db_session.add(item)
            db_session.flush()

            circulation = CirculationTransaction(
                borrower_id=borrower.id,
                item_id=item.id,
                bibliographic_record_id=biblio.id,
                checkout_date=datetime.utcnow() - timedelta(days=20),
                due_date=date.today() - timedelta(days=6),
                return_date=datetime.utcnow() - timedelta(days=1) if is_returned else None,
                checked_out_by="test",
            )
            db_session.add(circulation)

        db_session.commit()

        # Test - should only return the active loan
        active_loans = report_service.get_active_loans(db_session)

        assert len(active_loans) == 1
        assert active_loans[0]["item_id"] == "780"  # The non-returned one
        assert active_loans[0]["is_overdue"] is True


class TestAdditionalReports:
    """Test get_collection_stats and advanced report filtering."""

    def test_get_collection_stats_various(self, db_session):
        """Test getting collection statistics with different filters."""
        # Create records
        rec1 = BibliographicRecord(
            title="Book A", isbn="111", medium_type="Livre", target_audience="child", publication_year=2020
        )
        rec2 = BibliographicRecord(
            title="Periodical B", isbn="222", medium_type="Périodique", target_audience="youth", publication_year=2021
        )
        db_session.add_all([rec1, rec2])
        db_session.flush()

        # Create items
        item1 = Item(
            item_id="1111", bibliographic_record_id=rec1.id, condition="good", acquisition_date=date(2025, 1, 1)
        )
        item2 = Item(
            item_id="2222", bibliographic_record_id=rec2.id, condition="damaged", acquisition_date=date(2020, 6, 1)
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        # Call stats - excluding periodicals (only rec1/item1)
        stats1 = report_service.get_collection_stats(
            db_session, crew_method="never_inventoried", min_age_years=0.1, exclude_periodicals=True
        )
        assert stats1["total_count"] == 1
        assert len(stats1["breakdowns"]["medium_type"]) == 1
        assert stats1["breakdowns"]["medium_type"][0]["value"] == "Livre"

        # Call stats - including periodicals (rec1 & rec2)
        stats2 = report_service.get_collection_stats(
            db_session, crew_method="never_inventoried", min_age_years=0, exclude_periodicals=False
        )
        assert stats2["total_count"] == 2
        # Check condition breakdown
        cond_breakdown = {b["value"]: b["count"] for b in stats2["breakdowns"]["condition"]}
        assert cond_breakdown.get("good") == 1
        assert cond_breakdown.get("damaged") == 1

        # Test damaged_old crew method
        stats_damaged = report_service.get_collection_stats(
            db_session, crew_method="damaged_old", min_age_years=0, exclude_periodicals=False
        )
        assert stats_damaged["total_count"] == 1  # item2 is damaged and old

    def test_get_never_borrowed_items_filters(self, db_session):
        """Test getting never borrowed items with all filters applied."""
        rec = BibliographicRecord(
            title="Never Borrowed Book",
            isbn="333",
            medium_type="Livre",
            target_audience="child",
            level="easy",
            publication_year=2022
        )
        db_session.add(rec)
        db_session.flush()

        item = Item(
            item_id="3333",
            bibliographic_record_id=rec.id,
            acquisition_date=date(2025, 9, 15)  # matches 2025-2026 academic year
        )
        db_session.add(item)
        db_session.commit()

        # Query with filters
        items, total = report_service.get_never_borrowed_items(
            db_session,
            academic_year="2025-2026",
            level="easy",
            target_audience="child",
            medium_type="Livre",
            min_age_days=1,
            limit=5
        )

        assert len(items) == 1
        assert total == 1
        assert items[0]["item_id"] == "3333"
        assert items[0]["title"] == "Never Borrowed Book"

    def test_get_most_borrowed_titles_filters(self, db_session):
        """Test get_most_borrowed_titles with month/week periods and criteria filters."""
        # Create classes/borrowers
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.flush()

        borrower = Borrower(
            borrower_id="201",
            first_name="Alice",
            last_name="B",
            full_name="Alice B",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.flush()

        rec = BibliographicRecord(
            title="Popular Book",
            isbn="444",
            medium_type="Livre",
            target_audience="youth"
        )
        db_session.add(rec)
        db_session.flush()

        item = Item(item_id="4444", bibliographic_record_id=rec.id)
        db_session.add(item)
        db_session.flush()

        # Add recent loan (3 days ago)
        tx = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=rec.id,
            checkout_date=datetime.utcnow() - timedelta(days=3),
            due_date=date.today() + timedelta(days=10)
        )
        db_session.add(tx)
        db_session.commit()

        # Get most borrowed - week
        titles_week, total_week = report_service.get_most_borrowed_titles(
            db_session, period="week", medium_type="Livre", target_audience="youth"
        )
        assert len(titles_week) == 1
        assert total_week == 1
        assert titles_week[0]["title"] == "Popular Book"

        # Get most borrowed - month
        titles_month, total_month = report_service.get_most_borrowed_titles(
            db_session, period="month"
        )
        assert len(titles_month) == 1
        assert total_month == 1

    def test_get_circulation_statistics_periods(self, db_session):
        """Test get_circulation_statistics with monthly and all-time periods."""
        # Just run queries to cover period blocks
        stats_month = report_service.get_circulation_statistics(db_session, period="month")
        assert stats_month["period"] == "Last 30 days"

        stats_all = report_service.get_circulation_statistics(db_session, period="all-time")
        assert stats_all["period"] == "All time"

