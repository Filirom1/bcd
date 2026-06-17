"""
Integration test fixtures and configuration

Provides database fixtures and test data for integration testing.
"""

import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.bcd_api.core.database import Base, get_db
from src.bcd_api.main import app
from src.bcd_api.models.system_settings import SystemSettings
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item


@pytest.fixture(scope="function")
def db_engine():
    """Create shared in-memory SQLite engine for testing."""
    # Use a named in-memory database that can be shared across connections
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for a test with proper isolation.

    Uses transaction rollback strategy to ensure database is clean between tests.
    """
    # Create a connection and begin a transaction
    connection = db_engine.connect()
    transaction = connection.begin()

    # Create session bound to this connection
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    # Create default system settings
    settings = SystemSettings(
        id=1,
        loan_limit_default=2,
        loan_limit_teacher=5,
        loan_duration_days=14,
        renewal_limit=2,
        hold_expiration_days=3,
        max_holds_per_borrower=10,
        id_format="numeric",
        id_validation_regex=r"^\d+$",
        barcode_type="code39",
        language="fr",
        academic_year_current="2025-2026",
        library_name="BCD Test Library"
    )
    session.add(settings)
    session.commit()

    yield session

    # Rollback transaction to clean database state
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create FastAPI test client with integration test database.

    NOTE: Currently not working due to FastAPI TestClient dependency_overrides
    limitation. This fixture is kept for potential future use but API tests
    are skipped in favor of service-layer tests.
    """
    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_class(db_session):
    """Create a test class."""
    test_class = Class(
        name="CP-A",
        homeroom_teacher="Mme Dupont"
    )
    db_session.add(test_class)
    db_session.commit()
    db_session.refresh(test_class)
    return test_class


@pytest.fixture
def test_borrower_student(db_session, test_class):
    """Create a test student borrower."""
    borrower = Borrower(
        borrower_id="101",
        first_name="Amira",
        last_name="BENALI",
        full_name="Amira BENALI",
        role="student",
        class_id=test_class.id,
        active=True,
    )
    db_session.add(borrower)
    db_session.commit()
    db_session.refresh(borrower)
    return borrower


@pytest.fixture
def test_borrower_teacher(db_session):
    """Create a test teacher borrower."""
    borrower = Borrower(
        borrower_id="T001",
        first_name="Marie",
        last_name="MARTIN",
        full_name="Marie MARTIN",
        role="teacher",
        active=True,
    )
    db_session.add(borrower)
    db_session.commit()
    db_session.refresh(borrower)
    return borrower


@pytest.fixture
def test_borrower_blocked(db_session, test_class):
    """Create a blocked borrower with overdue items."""
    borrower = Borrower(
        borrower_id="102",
        first_name="Lucas",
        last_name="DUBOIS",
        full_name="Lucas DUBOIS",
        role="student",
        class_id=test_class.id,
        active=False,
        blocked_reason="Has overdue items",
    )
    db_session.add(borrower)
    db_session.commit()
    db_session.refresh(borrower)
    return borrower


@pytest.fixture
def test_bibliographic_record(db_session):
    """Create a test bibliographic record."""
    record = BiblographicRecord(
        title="Ils ont arrêté mon père",
        authors=json.dumps(["Carmi, Danielle"]),
        publisher="Flammarion",
        publication_year=2004,
        isbn="978-2-08-161739-6",
        language="fr",
        target_audience="child",
        genre="Album",
        medium_type="Livre"
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.fixture
def test_bibliographic_record_2(db_session):
    """Create a second test bibliographic record."""
    record = BiblographicRecord(
        title="Stuart Little",
        authors=json.dumps(["White, E.B."]),
        publisher="Harper",
        publication_year=1945,
        isbn="978-0-06-026395-7",
        language="eng",
        target_audience="child",
        genre="Novel",
        medium_type="Livre"
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.fixture
def test_item_available(db_session, test_bibliographic_record):
    """Create a test item that is available."""
    item = Item(
        item_id="785",
        bibliographic_record_id=test_bibliographic_record.id,
        call_number="800.000",
        status="available",
        condition="good",
        loanable=True,
        shelf_location="Fiction - Section A - Row 3"
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def test_item_available_2(db_session, test_bibliographic_record_2):
    """Create a second test item that is available."""
    item = Item(
        item_id="787",
        bibliographic_record_id=test_bibliographic_record_2.id,
        call_number="813.000",
        status="available",
        condition="good",
        loanable=True,
        shelf_location="Fiction - Section B - Row 1"
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def test_item_not_loanable(db_session, test_bibliographic_record):
    """Create a test item that is not loanable (reference only)."""
    item = Item(
        item_id="999",
        bibliographic_record_id=test_bibliographic_record.id,
        call_number="REF.001",
        status="available",
        condition="good",
        loanable=False,
        shelf_location="Reference - Section A"
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def multiple_borrowers(db_session, test_class):
    """Create multiple borrowers for testing."""
    borrowers = []
    for i in range(3, 6):  # Create borrowers 103, 104, 105
        borrower = Borrower(
            borrower_id=f"10{i}",
            first_name=f"Student{i}",
            last_name=f"TEST{i}",
            full_name=f"Student{i} TEST{i}",
            role="student",
            class_id=test_class.id,
            active=True,
        )
        db_session.add(borrower)
        borrowers.append(borrower)

    db_session.commit()
    for b in borrowers:
        db_session.refresh(b)

    return borrowers


@pytest.fixture
def multiple_items(db_session, test_bibliographic_record):
    """Create multiple items for testing."""
    items = []
    for i in range(3):
        item = Item(
            item_id=f"79{i}",
            bibliographic_record_id=test_bibliographic_record.id,
            call_number="800.000",
            status="available",
            condition="good",
            loanable=True,
            shelf_location=f"Fiction - Section A - Row {i+1}"
        )
        db_session.add(item)
        items.append(item)

    db_session.commit()
    for item in items:
        db_session.refresh(item)

    return items


# Factory Fixtures

class BorrowerFactory:
    """Factory for creating borrower objects."""

    def __init__(self, db_session):
        self.db_session = db_session
        self._counter = 0

    def create(
        self,
        borrower_id=None,
        first_name=None,
        last_name=None,
        role="student",
        class_id=None,
        email=None,
        phone=None,
        notes=None,
        active=True,
        blocked_reason=None,
    ):
        """Create a single borrower with custom parameters."""
        self._counter += 1
        if borrower_id is None:
            borrower_id = f"{100 + self._counter}"
        if first_name is None:
            first_name = f"FirstName{self._counter}"
        if last_name is None:
            last_name = f"LastName{self._counter}"

        full_name = f"{first_name} {last_name}"
        barcode = f"BOR{borrower_id}"

        borrower = Borrower(
            borrower_id=borrower_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            role=role,
            class_id=class_id,
            email=email,
            phone=phone,
            notes=notes,
            active=active,
            blocked_reason=blocked_reason,
        )
        self.db_session.add(borrower)
        self.db_session.commit()
        self.db_session.refresh(borrower)
        return borrower

    def create_batch(self, count, **kwargs):
        """Create multiple borrowers."""
        borrowers = []
        for _ in range(count):
            borrowers.append(self.create(**kwargs))
        return borrowers


class ClassFactory:
    """Factory for creating class objects."""

    def __init__(self, db_session):
        self.db_session = db_session
        self._counter = 0

    def create(
        self,
        name=None,
        homeroom_teacher=None,
        notes=None,
    ):
        """Create a single class with custom parameters."""
        self._counter += 1
        if name is None:
            name = f"Class-{self._counter}"

        class_obj = Class(
            name=name,
            homeroom_teacher=homeroom_teacher,
            notes=notes,
        )
        self.db_session.add(class_obj)
        self.db_session.commit()
        self.db_session.refresh(class_obj)
        return class_obj

    def create_batch(self, count, **kwargs):
        """Create multiple classes."""
        classes = []
        for _ in range(count):
            classes.append(self.create(**kwargs))
        return classes


class ItemFactory:
    """Factory for creating item objects."""

    def __init__(self, db_session):
        self.db_session = db_session
        self._counter = 0

    def create(
        self,
        item_id=None,
        bibliographic_record_id=None,
        call_number=None,
        status="available",
        condition="good",
        loanable=True,
        shelf_location=None,
    ):
        """Create a single item with custom parameters."""
        self._counter += 1
        if item_id is None:
            item_id = f"{800 + self._counter}"
        if call_number is None:
            call_number = "800.000"
        if shelf_location is None:
            shelf_location = f"Section A - Row {self._counter}"

        item = Item(
            item_id=item_id,
            bibliographic_record_id=bibliographic_record_id,
            call_number=call_number,
            status=status,
            condition=condition,
            loanable=loanable,
            shelf_location=shelf_location,
        )
        self.db_session.add(item)
        self.db_session.commit()
        self.db_session.refresh(item)
        return item

    def create_with_record(
        self,
        title="Test Book",
        authors=None,
        **item_kwargs
    ):
        """Create a bibliographic record with an item."""
        if authors is None:
            authors = ["Test Author"]

        record = BiblographicRecord(
            title=title,
            authors=json.dumps(authors),
            publisher="Test Publisher",
            publication_year=2020,
            language="fr",
            target_audience="child",
            genre="Novel",
            medium_type="Livre",
        )
        self.db_session.add(record)
        self.db_session.commit()
        self.db_session.refresh(record)

        return self.create(bibliographic_record_id=record.id, **item_kwargs)


@pytest.fixture
def borrower_factory(db_session):
    """Provide borrower factory."""
    return BorrowerFactory(db_session)


@pytest.fixture
def class_factory(db_session):
    """Provide class factory."""
    return ClassFactory(db_session)


@pytest.fixture
def item_factory(db_session):
    """Provide item factory."""
    return ItemFactory(db_session)


@pytest.fixture
def system_settings(db_session):
    """Get system settings (already created by db_session fixture)."""
    return db_session.query(SystemSettings).filter(SystemSettings.id == 1).first()
