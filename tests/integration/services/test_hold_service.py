"""Integration tests for hold service."""

from datetime import datetime, timedelta

import pytest

from src.bcd_api.core.exceptions import (
    ConflictError,
    HoldLimitExceededException,
    NotFoundError,
    ValidationError,
)
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.hold import Hold
from src.bcd_api.models.item import Item
from src.bcd_api.services import hold_service


class TestHoldCreation:
    """Test hold creation scenarios."""

    def test_create_hold_success(self, db_session):
        """Test successful hold creation."""
        # Create class
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.commit()

        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Create bibliographic record
        biblio = BiblographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        # Create item
        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="librarian@test.com",
            notes="Student really wants this book",
        )

        # Verify hold
        assert hold.id is not None
        assert hold.borrower_id == borrower.id
        assert hold.bibliographic_record_id == biblio.id
        assert hold.queue_position == 1
        assert hold.status == "waiting"
        assert hold.created_by == "librarian@test.com"
        assert hold.notes == "Student really wants this book"
        assert hold.hold_date is not None

    def test_create_hold_borrower_not_found(self, db_session):
        """Test hold creation with non-existent borrower."""
        # Create bibliographic record
        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        # Try to create hold with non-existent borrower
        with pytest.raises(NotFoundError, match="Borrower not found"):
            hold_service.create_hold(
                db=db_session,
                borrower_id=99999,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )

    def test_create_hold_bibliographic_record_not_found(self, db_session):
        """Test hold creation with non-existent bibliographic record."""
        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Try to create hold with non-existent record
        with pytest.raises(NotFoundError, match="Bibliographic record not found"):
            hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=99999,
                created_by="test",
            )

    def test_create_hold_borrower_blocked(self, db_session):
        """Test hold creation when borrower is blocked."""
        # Create blocked borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=False,
            blocked_reason="Overdue items",
        )
        db_session.add(borrower)
        db_session.commit()

        # Create bibliographic record with item
        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="available",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Try to create hold
        with pytest.raises(ValidationError, match="blocked"):
            hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )

    def test_create_hold_no_items(self, db_session):
        """Test hold creation when bibliographic record has no items."""
        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Create bibliographic record without items
        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        # Try to create hold
        with pytest.raises(ValidationError, match="no items"):
            hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )

    def test_create_hold_duplicate(self, db_session):
        """Test creating duplicate hold for same borrower and record."""
        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Create bibliographic record with item
        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create first hold
        hold1 = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )
        assert hold1.id is not None

        # Try to create duplicate hold
        with pytest.raises(ConflictError, match="already has an active hold"):
            hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )

    def test_create_multiple_holds_queue_position(self, db_session):
        """Test queue positions with multiple holds."""
        # Create 3 borrowers
        borrowers = []
        for i in range(1, 4):
            borrower = Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name="TEST",
                full_name=f"Student{i} TEST",
                role="student",
                active=True,
            )
            db_session.add(borrower)
            borrowers.append(borrower)
        db_session.commit()

        # Create bibliographic record with item
        biblio = BiblographicRecord(title="Popular Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create holds
        holds = []
        for borrower in borrowers:
            hold = hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )
            holds.append(hold)

        # Verify queue positions
        assert holds[0].queue_position == 1
        assert holds[1].queue_position == 2
        assert holds[2].queue_position == 3

    def test_create_hold_exceeds_max_holds_limit(self, db_session):
        """Test that hold creation fails when borrower has reached max active holds."""
        from src.bcd_api.models.system_settings import SystemSettings

        # Set max_holds_per_borrower to 1 (default)
        settings = db_session.query(SystemSettings).first()
        settings.max_holds_per_borrower = 1
        db_session.commit()

        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Create two bibliographic records each with an item
        biblio1 = BiblographicRecord(title="Book One", medium_type="Livre")
        biblio2 = BiblographicRecord(title="Book Two", medium_type="Livre")
        db_session.add_all([biblio1, biblio2])
        db_session.commit()

        item1 = Item(item_id="001", bibliographic_record_id=biblio1.id, status="on_loan", loanable=True)
        item2 = Item(item_id="002", bibliographic_record_id=biblio2.id, status="on_loan", loanable=True)
        db_session.add_all([item1, item2])
        db_session.commit()

        # First hold succeeds
        hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio1.id,
            created_by="test",
        )

        # Second hold on a different title must be rejected
        with pytest.raises(HoldLimitExceededException):
            hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio2.id,
                created_by="test",
            )

    def test_create_hold_custom_max_holds_limit(self, db_session):
        """Test that a custom max_holds_per_borrower of 2 allows 2 holds and blocks a third."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = db_session.query(SystemSettings).first()
        settings.max_holds_per_borrower = 2
        db_session.commit()

        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Create three bibliographic records each with an item
        biblios = []
        for i in range(1, 4):
            biblio = BiblographicRecord(title=f"Book {i}", medium_type="Livre")
            db_session.add(biblio)
            db_session.commit()
            item = Item(item_id=f"00{i}", bibliographic_record_id=biblio.id, status="on_loan", loanable=True)
            db_session.add(item)
            biblios.append(biblio)
        db_session.commit()

        # First two holds succeed
        hold_service.create_hold(db=db_session, borrower_id=borrower.id, bibliographic_record_id=biblios[0].id, created_by="test")
        hold_service.create_hold(db=db_session, borrower_id=borrower.id, bibliographic_record_id=biblios[1].id, created_by="test")

        # Third hold must be rejected
        with pytest.raises(HoldLimitExceededException):
            hold_service.create_hold(db=db_session, borrower_id=borrower.id, bibliographic_record_id=biblios[2].id, created_by="test")


class TestHoldRetrieval:
    """Test hold retrieval functions."""

    def test_get_hold_success(self, db_session):
        """Test retrieving hold by ID."""
        # Create borrower and biblio
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)

        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )

        # Retrieve hold
        retrieved = hold_service.get_hold(db_session, hold.id)
        assert retrieved.id == hold.id
        assert retrieved.borrower_id == borrower.id

    def test_get_hold_not_found(self, db_session):
        """Test retrieving non-existent hold."""
        with pytest.raises(NotFoundError, match="Hold not found"):
            hold_service.get_hold(db_session, 99999)

    def test_get_holds_for_borrower(self, db_session):
        """Test getting all holds for a borrower."""
        # Create borrower
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        # Create multiple biblio records with items
        holds = []
        for i in range(3):
            biblio = BiblographicRecord(title=f"Book {i}", medium_type="Livre")
            db_session.add(biblio)
            db_session.commit()

            item = Item(
                item_id=f"78{i}",
                bibliographic_record_id=biblio.id,
                status="on_loan",
                loanable=True,
            )
            db_session.add(item)
            db_session.commit()

            hold = hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )
            holds.append(hold)

        # Retrieve borrower's holds
        retrieved = hold_service.get_holds_for_borrower(db_session, borrower.id)
        assert len(retrieved) == 3

    def test_get_holds_for_bibliographic_record(self, db_session):
        """Test getting all holds for a bibliographic record."""
        # Create biblio record with item
        biblio = BiblographicRecord(title="Popular Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create multiple borrowers with holds
        for i in range(3):
            borrower = Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name="TEST",
                full_name=f"Student{i} TEST",
                role="student",
                active=True,
            )
            db_session.add(borrower)
            db_session.commit()

            hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )

        # Retrieve holds for biblio record
        retrieved = hold_service.get_holds_for_bibliographic_record(
            db_session, biblio.id
        )
        assert len(retrieved) == 3
        # Verify ordering by queue position
        assert retrieved[0].queue_position == 1
        assert retrieved[1].queue_position == 2
        assert retrieved[2].queue_position == 3


class TestHoldStatusManagement:
    """Test hold status transitions."""

    def test_mark_hold_ready(self, db_session):
        """Test marking hold as ready."""
        # Create borrower, biblio, item
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)

        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )
        assert hold.status == "waiting"

        # Mark as ready
        updated = hold_service.mark_hold_ready(db_session, hold.id, expiration_days=3)
        assert updated.status == "ready"
        assert updated.available_date is not None
        assert updated.expiration_date is not None

        # Verify expiration date is 3 days from now
        expected_exp = (datetime.utcnow() + timedelta(days=3)).date()
        assert updated.expiration_date == expected_exp

    def test_mark_hold_ready_not_waiting(self, db_session):
        """Test marking hold ready when not in waiting status."""
        # Create borrower, biblio, item
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)

        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create and immediately mark ready
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )
        hold_service.mark_hold_ready(db_session, hold.id)

        # Try to mark ready again
        with pytest.raises(ValidationError, match="not in waiting status"):
            hold_service.mark_hold_ready(db_session, hold.id)

    def test_fulfill_hold(self, db_session):
        """Test fulfilling a hold (deletes it to save space)."""
        # Create borrower, biblio, item
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)

        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create hold and mark ready
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )
        hold_service.mark_hold_ready(db_session, hold.id)
        hold_id = hold.id

        # Fulfill hold - should delete it
        hold_service.fulfill_hold(db_session, hold_id)

        # Verify hold is deleted (no history kept)
        deleted_hold = db_session.query(Hold).filter(Hold.id == hold_id).first()
        assert deleted_hold is None

    def test_cancel_hold(self, db_session):
        """Test cancelling a hold (deletes it to save space)."""
        # Create borrower, biblio, item
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)

        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )
        hold_id = hold.id

        # Cancel hold - should delete it
        hold_service.cancel_hold(db_session, hold_id)

        # Verify hold is deleted (no history kept)
        deleted_hold = db_session.query(Hold).filter(Hold.id == hold_id).first()
        assert deleted_hold is None


class TestHoldQueueManagement:
    """Test hold queue reordering."""

    def test_queue_reordering_on_cancel(self, db_session):
        """Test queue reorders when hold is cancelled."""
        # Create 3 borrowers
        borrowers = []
        for i in range(1, 4):
            borrower = Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name="TEST",
                full_name=f"Student{i} TEST",
                role="student",
                active=True,
            )
            db_session.add(borrower)
            borrowers.append(borrower)
        db_session.commit()

        # Create biblio with item
        biblio = BiblographicRecord(title="Popular Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create 3 holds
        holds = []
        for borrower in borrowers:
            hold = hold_service.create_hold(
                db=db_session,
                borrower_id=borrower.id,
                bibliographic_record_id=biblio.id,
                created_by="test",
            )
            holds.append(hold)

        # Cancel middle hold (position 2)
        hold_service.cancel_hold(db_session, holds[1].id)

        # Verify queue reordered
        db_session.refresh(holds[2])
        assert holds[2].queue_position == 2  # Should move from 3 to 2


class TestAutoFillHolds:
    """Test automatic hold filling on return."""

    def test_auto_fill_on_return(self, db_session):
        """Test automatically filling next hold when item is returned."""
        # Create borrower, biblio, item
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role="student",
            active=True,
        )
        db_session.add(borrower)

        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            created_by="test",
        )
        assert hold.status == "waiting"
        assert hold.queue_position == 1

        # Simulate item return - auto-fill hold
        filled_hold = hold_service.auto_fill_holds_on_return(
            db_session, biblio.id, expiration_days=3
        )

        assert filled_hold is not None
        assert filled_hold.id == hold.id
        assert filled_hold.status == "ready"
        assert filled_hold.available_date is not None

    def test_auto_fill_no_waiting_holds(self, db_session):
        """Test auto-fill when no holds are waiting."""
        # Create biblio
        biblio = BiblographicRecord(title="Test Book", medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        # Try to auto-fill (no holds exist)
        result = hold_service.auto_fill_holds_on_return(db_session, biblio.id)
        assert result is None
