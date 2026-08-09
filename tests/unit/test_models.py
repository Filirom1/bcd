"""Unit tests for database models."""

from datetime import date, timedelta

import pytest

from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.hold import Hold
from src.bcd_api.models.item import Item
from src.bcd_api.models.system_settings import SystemSettings
from src.shared.constants import (
    BorrowerRole,
    CirculationStatus,
    HoldStatus,
    ItemStatus,
)


class TestBorrowerModel:
    """Tests for Borrower model."""

    def test_create_borrower(self, db_session):
        """Test creating a borrower."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role=BorrowerRole.STUDENT.value,
        )
        db_session.add(borrower)
        db_session.commit()

        assert borrower.id is not None
        assert borrower.borrower_id == "101"
        assert borrower.active is True
        assert borrower.blocked_reason is None

    def test_borrower_blocked(self, db_session):
        """Test blocking a borrower."""
        borrower = Borrower(
            borrower_id="102",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role=BorrowerRole.STUDENT.value,
            active=False,
            blocked_reason="Overdue items",
        )
        db_session.add(borrower)
        db_session.commit()

        assert borrower.active is False
        assert borrower.blocked_reason == "Overdue items"

    def test_borrower_unique_id(self, db_session):
        """Test borrower ID uniqueness constraint."""
        borrower1 = Borrower(
            borrower_id="103",
            first_name="User1",
            last_name="Test",
            full_name="User1 Test",
            role=BorrowerRole.STUDENT.value,
        )
        db_session.add(borrower1)
        db_session.commit()

        borrower2 = Borrower(
            borrower_id="103",
            first_name="User2",
            last_name="Test",
            full_name="User2 Test",
            role=BorrowerRole.STUDENT.value,
        )
        db_session.add(borrower2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestBibliographicRecordModel:
    """Tests for BibliographicRecord model."""

    def test_create_bibliographic_record(self, db_session):
        """Test creating a bibliographic record."""
        biblio = BibliographicRecord(
            isbn="9782800687346",
            title="Ils ont arrêté mon père",
            authors='["Carmi, Danielle"]',
            publisher="Flammarion",
            publication_year=2004,
            language="fr",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        assert biblio.id is not None
        assert biblio.isbn == "9782800687346"
        assert biblio.total_items == 0

    def test_bibliographic_record_optional_fields(self, db_session):
        """Test bibliographic record with minimal data."""
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        assert biblio.id is not None
        assert biblio.isbn is None
        assert biblio.publisher is None


class TestItemModel:
    """Tests for Item model."""

    def test_create_item(self, db_session):
        """Test creating an item."""
        # Create bibliographic record first
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            loanable=True,
            status=ItemStatus.AVAILABLE.value,
        )
        db_session.add(item)
        db_session.commit()

        assert item.id is not None
        assert item.item_id == "785"
        assert item.status == ItemStatus.AVAILABLE.value
        assert item.loanable is True

    def test_item_unique_id(self, db_session):
        """Test item ID uniqueness constraint."""
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item1 = Item(
            item_id="786",
            bibliographic_record_id=biblio.id,
            call_number="800.001",
            loanable=True,
            status=ItemStatus.AVAILABLE.value,
        )
        db_session.add(item1)
        db_session.commit()

        item2 = Item(
            item_id="786",
            bibliographic_record_id=biblio.id,
            call_number="800.002",
            loanable=True,
            status=ItemStatus.AVAILABLE.value,
        )
        db_session.add(item2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestCirculationTransactionModel:
    """Tests for CirculationTransaction model."""

    def test_create_circulation_transaction(self, db_session):
        """Test creating a circulation transaction."""
        # Create dependencies
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role=BorrowerRole.STUDENT.value,
        )
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add_all([borrower, biblio])
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            loanable=True,
            status=ItemStatus.AVAILABLE.value,
        )
        db_session.add(item)
        db_session.commit()

        transaction = CirculationTransaction(
            item_id=item.id,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            checkout_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            status=CirculationStatus.ACTIVE.value,
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.id is not None
        assert transaction.status == CirculationStatus.ACTIVE.value
        assert transaction.return_date is None

    def test_circulation_is_overdue(self, db_session):
        """Test overdue calculation."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role=BorrowerRole.STUDENT.value,
        )
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add_all([borrower, biblio])
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            loanable=True,
            status=ItemStatus.AVAILABLE.value,
        )
        db_session.add(item)
        db_session.commit()

        # Create overdue transaction
        transaction = CirculationTransaction(
            item_id=item.id,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            checkout_date=date.today() - timedelta(days=10),
            due_date=date.today() - timedelta(days=3),
            status=CirculationStatus.ACTIVE.value,
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.is_overdue is True
        assert transaction.days_overdue == 3

    def test_circulation_not_overdue_when_returned(self, db_session):
        """Test that returned items are not overdue."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role=BorrowerRole.STUDENT.value,
        )
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add_all([borrower, biblio])
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            loanable=True,
            status=ItemStatus.AVAILABLE.value,
        )
        db_session.add(item)
        db_session.commit()

        transaction = CirculationTransaction(
            item_id=item.id,
            borrower_id=borrower.id,
            bibliographic_record_id=biblio.id,
            checkout_date=date.today() - timedelta(days=10),
            due_date=date.today() - timedelta(days=3),
            return_date=date.today() - timedelta(days=2),
            status=CirculationStatus.RETURNED.value,
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.is_overdue is False
        assert transaction.days_overdue == 0


class TestHoldModel:
    """Tests for Hold model."""

    def test_create_hold(self, db_session):
        """Test creating a hold."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role=BorrowerRole.STUDENT.value,
        )
        biblio = BibliographicRecord(
            title="Test Book",
            medium_type="Livre",
        )
        db_session.add_all([borrower, biblio])
        db_session.commit()

        hold = Hold(
            bibliographic_record_id=biblio.id,
            borrower_id=borrower.id,
            queue_position=1,
            hold_date=date.today(),
            expiration_date=date.today() + timedelta(days=7),
            status=HoldStatus.WAITING.value,
        )
        db_session.add(hold)
        db_session.commit()

        assert hold.id is not None
        assert hold.status == HoldStatus.WAITING.value
        assert hold.queue_position == 1


class TestClassModel:
    """Tests for Class model."""

    def test_create_class(self, db_session):
        """Test creating a class."""
        class_obj = Class(
            name="CP-A",
            homeroom_teacher="Mme Dupont",
            notes="Class notes",
        )
        db_session.add(class_obj)
        db_session.commit()

        assert class_obj.id is not None
        assert class_obj.name == "CP-A"
        assert class_obj.homeroom_teacher == "Mme Dupont"


class TestSystemSettingsModel:
    """Tests for SystemSettings model."""

    def test_create_system_settings(self, db_session):
        """Test creating system settings."""
        settings = SystemSettings(id=1)
        db_session.add(settings)
        db_session.commit()

        assert settings.id == 1
        assert settings.loan_duration_days == 14
        assert settings.loan_limit_default == 2
        assert settings.renewal_limit == 2

    def test_system_settings_custom_values(self, db_session):
        """Test system settings with custom values."""
        settings = SystemSettings(
            id=1,
            loan_duration_days=21,
            loan_limit_default=5,
            loan_limit_teacher=10,
            renewal_limit=3,
            id_length_min=5,
            id_length_max=15,
        )
        db_session.add(settings)
        db_session.commit()

        assert settings.loan_duration_days == 21
        assert settings.loan_limit_default == 5
        assert settings.loan_limit_teacher == 10
        assert settings.renewal_limit == 3
        assert settings.id_length_min == 5
        assert settings.id_length_max == 15
