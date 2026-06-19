"""Unit tests for Pydantic schemas."""

from datetime import date

import pytest
from pydantic import ValidationError

from src.bcd_api.schemas.bibliographic_record import (
    BiblographicRecordCreate,
    BiblographicRecordUpdate,
)
from src.bcd_api.schemas.borrower import BorrowerCreate, BorrowerResponse, BorrowerUpdate
from src.bcd_api.schemas.circulation import CheckoutRequest, RenewRequest, ReturnRequest
from src.bcd_api.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from src.shared.constants import BorrowerRole, ItemCondition, ItemStatus


class TestBorrowerSchemas:
    """Tests for Borrower schemas."""

    def test_borrower_create_valid(self):
        """Test creating a borrower with valid data."""
        data = {
            "borrower_id": "101",
            "first_name": "Amira",
            "last_name": "BENALI",
            "role": "student",
            "class_id": 1,
        }
        borrower = BorrowerCreate(**data)
        assert borrower.borrower_id == "101"
        assert borrower.first_name == "Amira"
        assert borrower.last_name == "BENALI"
        assert borrower.role == BorrowerRole.STUDENT

    def test_borrower_create_missing_required(self):
        """Test borrower creation with missing required fields."""
        with pytest.raises(ValidationError):
            BorrowerCreate(borrower_id="101", first_name="Amira")

    def test_borrower_update(self):
        """Test borrower update schema."""
        data = {"first_name": "Updated", "grade_level": "CE1"}
        update = BorrowerUpdate(**data)
        assert update.first_name == "Updated"
        assert update.grade_level == "CE1"
        assert update.last_name is None

    def test_borrower_response(self):
        """Test borrower response schema."""
        data = {
            "id": 1,
            "borrower_id": "101",
            "first_name": "Amira",
            "last_name": "BENALI",
            "full_name": "Amira BENALI",
            "role": "student",
            "active": True,
            "blocked_reason": None,
            "class_id": 1,
            "grade_level": "CP",
            "barcode": "101",
            "email": None,
            "phone": None,
            "notes": None,
            "created_at": date.today(),
            "updated_at": date.today(),
        }
        response = BorrowerResponse(**data)
        assert response.id == 1
        assert response.borrower_id == "101"


class TestBiblioSchemas:
    """Tests for BiblographicRecord schemas."""

    def test_biblio_create_minimal(self):
        """Test creating a bibliographic record with minimal data."""
        data = {"title": "Test Book", "medium_type": "Livre"}
        biblio = BiblographicRecordCreate(**data)
        assert biblio.title == "Test Book"
        assert biblio.medium_type == "Livre"

    def test_biblio_create_full(self):
        """Test creating a bibliographic record with all fields."""
        data = {
            "isbn": "978-2-8006-8734-6",
            "title": "Ils ont arrêté mon père",
            "authors": ["Carmi, Danielle"],
            "publisher": "Flammarion",
            "publication_year": 2004,
            "language": "fre",
            "genre": "Album",
            "medium_type": "Livre",
            "page_count": 32,
            "has_illustrations": True,
        }
        biblio = BiblographicRecordCreate(**data)
        assert biblio.isbn == "isbn:978-2-8006-8734-6"
        assert biblio.authors == ["Carmi, Danielle"]
        assert biblio.page_count == 32

    def test_biblio_create_missing_title(self):
        """Test biblio creation without title."""
        with pytest.raises(ValidationError):
            BiblographicRecordCreate(medium_type="Livre")

    def test_biblio_update(self):
        """Test bibliographic record update schema."""
        data = {"title": "Updated Title", "publisher": "New Publisher"}
        update = BiblographicRecordUpdate(**data)
        assert update.title == "Updated Title"
        assert update.publisher == "New Publisher"

    def test_biblio_dewey_number_cleaning(self):
        """Test that dewey_number is cleaned of special characters and normalized."""
        data = {"title": "Test Book", "medium_type": "Livre", "dewey_number": "843 (3)°"}
        biblio = BiblographicRecordCreate(**data)
        assert biblio.dewey_number == "843 3"

        # Update test
        update_data = {"dewey_number": "R(A)°"}
        update = BiblographicRecordUpdate(**update_data)
        assert update.dewey_number == "RA"


class TestItemSchemas:
    """Tests for Item schemas."""

    def test_item_create_valid(self):
        """Test creating an item with valid data."""
        data = {
            "item_id": "785",
            "bibliographic_record_id": 1,
            "call_number": "800.000",
            "loanable": True,
        }
        item = ItemCreate(**data)
        assert item.item_id == "785"
        assert item.bibliographic_record_id == 1
        assert item.loanable is True

    def test_item_call_number_cleaning(self):
        """Test that call_number is cleaned of special characters and normalized."""
        data = {
            "item_id": "785",
            "bibliographic_record_id": 1,
            "call_number": "843 (3)° D'O-R",
            "loanable": True,
        }
        item = ItemCreate(**data)
        assert item.call_number == "843 3 DOR"

        update_data = {"call_number": "A°(B) D'U"}
        update = ItemUpdate(**update_data)
        assert update.call_number == "AB DU"

    def test_item_create_missing_required(self):
        """Test item creation with missing required fields."""
        with pytest.raises(ValidationError):
            ItemCreate(item_id="785", call_number="800.000")

    def test_item_update(self):
        """Test item update schema."""
        data = {"status": ItemStatus.AVAILABLE, "shelf_location": "Salle de classe"}
        update = ItemUpdate(**data)
        assert update.status == ItemStatus.AVAILABLE
        assert update.shelf_location == "Salle de classe"

    def test_item_response(self):
        """Test item response schema."""
        data = {
            "id": 1,
            "item_id": "785",
            "barcode": "785",  # Computed from item_id
            "bibliographic_record_id": 1,
            "call_number": "800.000",
            "status": ItemStatus.AVAILABLE,
            "loanable": True,
            "shelf_location": None,
            "condition": ItemCondition.GOOD,
            "acquisition_date": None,
            "funding_source": None,
            "last_borrowed_at": None,
            "created_at": date.today(),
            "updated_at": date.today(),
        }
        response = ItemResponse(**data)
        assert response.id == 1
        assert response.item_id == "785"


class TestCirculationSchemas:
    """Tests for Circulation schemas."""

    def test_checkout_request_valid(self):
        """Test checkout request with valid data."""
        data = {"borrower_id": "101", "item_ids": ["785", "786"]}
        request = CheckoutRequest(**data)
        assert request.borrower_id == "101"
        assert len(request.item_ids) == 2

    def test_checkout_request_empty_items(self):
        """Test checkout request with empty item list."""
        with pytest.raises(ValidationError):
            CheckoutRequest(borrower_id="101", item_ids=[])

    def test_checkout_request_missing_borrower(self):
        """Test checkout request without borrower ID."""
        with pytest.raises(ValidationError):
            CheckoutRequest(item_ids=["785"])

    def test_return_request_valid(self):
        """Test return request with valid data."""
        data = {"item_ids": ["785", "786"]}
        request = ReturnRequest(**data)
        assert len(request.item_ids) == 2

    def test_return_request_empty_items(self):
        """Test return request with empty item list."""
        with pytest.raises(ValidationError):
            ReturnRequest(item_ids=[])

    def test_renew_request_valid(self):
        """Test renew request with valid data."""
        data = {"borrower_id": "101", "item_ids": ["785"]}
        request = RenewRequest(**data)
        assert request.borrower_id == "101"
        assert len(request.item_ids) == 1

    def test_renew_request_no_items(self):
        """Test renew request without item list (renew all)."""
        data = {"borrower_id": "101"}
        request = RenewRequest(**data)
        assert request.borrower_id == "101"
        assert request.item_ids is None


class TestSchemaValidation:
    """Tests for schema field validation."""

    def test_string_length_validation(self):
        """Test string length constraints."""
        # Title too long
        with pytest.raises(ValidationError):
            BiblographicRecordCreate(title="x" * 501, medium_type="Livre")

    def test_year_validation(self):
        """Test publication year validation."""
        # Valid year
        biblio = BiblographicRecordCreate(
            title="Test Book", medium_type="Livre", publication_year=2024
        )
        assert biblio.publication_year == 2024

        # Year too old
        with pytest.raises(ValidationError):
            BiblographicRecordCreate(title="Test Book", medium_type="Livre", publication_year=999)

        # Future year (2101 is above max of 2100)
        with pytest.raises(ValidationError):
            BiblographicRecordCreate(title="Test Book", medium_type="Livre", publication_year=2101)
