"""Unit tests for custom exceptions."""

from fastapi import status

from src.bcd_api.core.exceptions import (
    BCDException,
    BiblographicRecordNotFoundException,
    BorrowerBlockedException,
    BorrowerNotFoundException,
    BusinessRuleViolation,
    ConflictError,
    DuplicateBorrowerIDException,
    DuplicateISBNException,
    DuplicateItemIDException,
    InvalidIDFormatException,
    ItemHasHoldsException,
    ItemNotAvailableException,
    ItemNotFoundException,
    ItemNotLoanableException,
    LoanLimitExceededException,
    NotFoundException,
    RenewalLimitExceededException,
    ValidationError,
)


class TestBaseExceptions:
    """Tests for base exception classes."""

    def test_bcd_exception(self):
        """Test BCDException base class."""
        exc = BCDException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test error",
        )
        assert exc.status_code == 500
        assert exc.detail == "Test error"

    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException(resource="Item", identifier="123")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "Item not found: 123" in str(exc.detail)

    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError(detail="Invalid input")
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.detail == "Invalid input"

    def test_conflict_error(self):
        """Test ConflictError."""
        exc = ConflictError(detail="Duplicate entry")
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert exc.detail == "Duplicate entry"

    def test_business_rule_violation(self):
        """Test BusinessRuleViolation."""
        exc = BusinessRuleViolation(detail="Rule violated")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.detail == "Rule violated"


class TestBorrowerExceptions:
    """Tests for borrower-related exceptions."""

    def test_borrower_not_found_exception(self):
        """Test BorrowerNotFoundException."""
        exc = BorrowerNotFoundException(borrower_id="101")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "101" in str(exc.detail)
        assert "Borrower" in str(exc.detail)

    def test_borrower_blocked_exception(self):
        """Test BorrowerBlockedException."""
        exc = BorrowerBlockedException(borrower_id="101", reason="Overdue items")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert "101" in str(exc.detail)
        assert "blocked" in str(exc.detail).lower()
        assert "Overdue items" in str(exc.detail)


class TestItemExceptions:
    """Tests for item-related exceptions."""

    def test_item_not_found_exception(self):
        """Test ItemNotFoundException."""
        exc = ItemNotFoundException(item_id="785")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "785" in str(exc.detail)
        assert "Item" in str(exc.detail)

    def test_item_not_available_exception(self):
        """Test ItemNotAvailableException."""
        exc = ItemNotAvailableException(item_id="785", current_status="Prêté")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert "785" in str(exc.detail)
        assert "Prêté" in str(exc.detail)

    def test_item_not_loanable_exception(self):
        """Test ItemNotLoanableException."""
        exc = ItemNotLoanableException(item_id="785")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert "785" in str(exc.detail)
        assert "not loanable" in str(exc.detail).lower()


class TestCirculationExceptions:
    """Tests for circulation-related exceptions."""

    def test_loan_limit_exceeded_exception(self):
        """Test LoanLimitExceededException."""
        exc = LoanLimitExceededException(borrower_id="101", current_count=3, limit=3)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        # Check context contains borrower_id even if detail doesn't
        assert exc.context["borrower_id"] == "101" or "101" in str(exc.detail)
        assert "3" in str(exc.detail)
        assert "limit" in str(exc.detail).lower()

    def test_renewal_limit_exceeded_exception(self):
        """Test RenewalLimitExceededException."""
        exc = RenewalLimitExceededException(item_id="785", current_renewals=2, limit=2)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert "785" in str(exc.detail)
        assert "2" in str(exc.detail)
        assert "renewal" in str(exc.detail).lower()

    def test_item_has_holds_exception(self):
        """Test ItemHasHoldsException."""
        exc = ItemHasHoldsException(item_id="785", holds_count=2)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert "785" in str(exc.detail)
        assert "2" in str(exc.detail)
        assert "hold" in str(exc.detail).lower()


class TestCatalogExceptions:
    """Tests for catalog-related exceptions."""

    def test_bibliographic_record_not_found_exception(self):
        """Test BiblographicRecordNotFoundException."""
        exc = BiblographicRecordNotFoundException(biblio_id=123)
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "123" in str(exc.detail)
        assert "Bibliographic record" in str(exc.detail)

    def test_duplicate_isbn_exception(self):
        """Test DuplicateISBNException."""
        exc = DuplicateISBNException(isbn="978-2-8006-8734-6", existing_id=42)
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert "978-2-8006-8734-6" in str(exc.detail)
        assert "42" in str(exc.detail)
        assert "already exists" in str(exc.detail).lower()


class TestDuplicateExceptions:
    """Tests for duplicate ID exceptions."""

    def test_duplicate_borrower_id_exception(self):
        """Test DuplicateBorrowerIDException."""
        exc = DuplicateBorrowerIDException(borrower_id="101")
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert "101" in str(exc.detail)
        assert "already exists" in str(exc.detail).lower()

    def test_duplicate_item_id_exception(self):
        """Test DuplicateItemIDException."""
        exc = DuplicateItemIDException(item_id="785")
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert "785" in str(exc.detail)
        assert "already exists" in str(exc.detail).lower()


class TestValidationExceptions:
    """Tests for validation exceptions."""

    def test_invalid_id_format_exception(self):
        """Test InvalidIDFormatException."""
        exc = InvalidIDFormatException(
            id_type="Borrower ID", value="ABC-123", expected_format="numeric only"
        )
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Borrower ID" in str(exc.detail)
        assert "ABC-123" in str(exc.detail)
        assert "numeric only" in str(exc.detail)
