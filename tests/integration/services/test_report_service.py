"""Integration tests for report service."""

import pytest
from datetime import datetime, timedelta, date

from src.bcd_api.services import report_service
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.hold import Hold, HoldStatus


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

        biblio = BiblographicRecord(title="Test Book", authors="Test Author", medium_type="Livre")
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
        overdue = report_service.get_overdue_items(db_session)

        assert len(overdue) == 1
        assert overdue[0]["item_id"] == "785"
        assert overdue[0]["days_overdue"] == 5

    def test_get_overdue_items_no_overdue(self, db_session):
        """Test when there are no overdue items."""
        overdue = report_service.get_overdue_items(db_session)
        assert len(overdue) == 0

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
            biblio = BiblographicRecord(title=f"Book {idx}", medium_type="Livre")
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
        overdue_class_a = report_service.get_overdue_items(db_session, class_name="CP-A")
        assert len(overdue_class_a) == 1
        assert overdue_class_a[0]["class_name"] == "CP-A"

        overdue_class_b = report_service.get_overdue_items(db_session, class_name="CP-B")
        assert len(overdue_class_b) == 1
        assert overdue_class_b[0]["class_name"] == "CP-B"

    @pytest.mark.skip(reason="academic_year field removed from Class model in admin features implementation")
    def test_get_overdue_items_filter_by_academic_year(self, db_session):
        """Test filtering overdue items by academic year."""
        # NOTE: This test is skipped because academic_year field was removed from Class model
        # Create classes in different academic years
        class_2025 = Class(name="CP-A")
        class_2026 = Class(name="CE1-A")
        db_session.add_all([class_2025, class_2026])
        db_session.flush()

        # Create borrowers
        borrower_2025 = Borrower(
            borrower_id="101",
            first_name="Student",
            last_name="2025",
            full_name="Student 2025",
            role="student",
            class_id=class_2025.id,
            active=True,
        )
        borrower_2026 = Borrower(
            borrower_id="102",
            first_name="Student",
            last_name="2026",
            full_name="Student 2026",
            role="student",
            class_id=class_2026.id,
            active=True,
        )
        db_session.add_all([borrower_2025, borrower_2026])
        db_session.flush()

        # Create overdue circulations
        for idx, borrower in enumerate([borrower_2025, borrower_2026]):
            biblio = BiblographicRecord(title=f"Book {idx}", medium_type="Livre")
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

        # Test filtering by academic year
        overdue_2025 = report_service.get_overdue_items(
            db_session, academic_year="2025-2026"
        )
        assert len(overdue_2025) == 1

        overdue_2026 = report_service.get_overdue_items(
            db_session, academic_year="2026-2027"
        )
        assert len(overdue_2026) == 1

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
            biblio = BiblographicRecord(title=f"Book {idx}", medium_type="Livre")
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
        biblio = BiblographicRecord(
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
        never_borrowed = report_service.get_never_borrowed_items(db_session)

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
            biblio = BiblographicRecord(
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
        most_borrowed = report_service.get_most_borrowed_titles(
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
            biblio = BiblographicRecord(title=f"Book {i}", medium_type="Livre")
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
            biblio = BiblographicRecord(title=f"Book {i}", medium_type="Livre")
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

        biblio = BiblographicRecord(
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

        biblio = BiblographicRecord(title="Book", medium_type="Livre")
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

        biblio = BiblographicRecord(title="Book", medium_type="Livre")
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
        biblio = BiblographicRecord(title="Checked Out Book", authors="Test Author", medium_type="Livre")
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
            biblio = BiblographicRecord(title=f"Book {idx}", medium_type="Livre")
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
            biblio = BiblographicRecord(title=f"Book {idx}", medium_type="Livre")
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
