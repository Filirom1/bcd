"""Pytest configuration and fixtures for BCD tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.bcd_api.core.database import Base, get_db
from src.bcd_api.main import app

# Test database URL (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_borrower_data():
    """Sample borrower data for testing."""
    return {
        "borrower_id": "101",
        "first_name": "Amira",
        "last_name": "BENALI",
        "role": "student",
        "class_name": "CP-A",
    }


@pytest.fixture
def sample_bibliographic_data():
    """Sample bibliographic record data for testing."""
    return {
        "isbn": "978-2-8006-8734-6",
        "title": "Ils ont arrêté mon père",
        "authors": ["Carmi, Danielle"],
        "publisher": "Flammarion",
        "publication_year": 2004,
        "language": "fre",
        "genre": "Album",
        "medium_type": "Livre",
    }


@pytest.fixture
def sample_item_data():
    """Sample item data for testing."""
    return {
        "item_id": "785",
        "call_number": "800.000",
        "loanable": True,
    }
