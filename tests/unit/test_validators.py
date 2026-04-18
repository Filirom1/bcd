"""Unit tests for validation utilities."""

import pytest
from src.shared.validators import (
    validate_isbn,
    validate_isbn10,
    validate_isbn13,
    normalize_isbn,
    validate_id_format,
    validate_borrower_id,
    validate_item_id,
)


class TestISBNValidation:
    """Tests for ISBN validation functions."""

    def test_validate_isbn10_valid(self):
        """Test ISBN-10 validation with valid ISBNs."""
        assert validate_isbn10("0306406152")
        assert validate_isbn10("080442957X")
        assert validate_isbn10("0684843285")

    def test_validate_isbn10_invalid_checksum(self):
        """Test ISBN-10 validation with invalid checksum."""
        assert not validate_isbn10("0306406153")
        assert not validate_isbn10("0684843286")

    def test_validate_isbn10_invalid_format(self):
        """Test ISBN-10 validation with invalid format."""
        assert not validate_isbn10("123")
        assert not validate_isbn10("abcdefghij")
        assert not validate_isbn10("")

    def test_validate_isbn13_valid(self):
        """Test ISBN-13 validation with valid ISBNs."""
        assert validate_isbn13("9782800687346")
        assert validate_isbn13("9780306406157")
        assert validate_isbn13("9780684843285")

    def test_validate_isbn13_invalid_checksum(self):
        """Test ISBN-13 validation with invalid checksum."""
        assert not validate_isbn13("9782800687345")
        assert not validate_isbn13("9780306406158")

    def test_validate_isbn13_invalid_format(self):
        """Test ISBN-13 validation with invalid format."""
        assert not validate_isbn13("123")
        assert not validate_isbn13("abcdefghijklm")
        assert not validate_isbn13("")

    def test_validate_isbn_with_hyphens(self):
        """Test ISBN validation with hyphens."""
        assert validate_isbn("978-2-8006-8734-6")
        assert validate_isbn("0-306-40615-2")

    def test_validate_isbn_with_spaces(self):
        """Test ISBN validation with spaces."""
        assert validate_isbn("978 2 8006 8734 6")
        assert validate_isbn("0 306 40615 2")

    def test_validate_isbn_empty(self):
        """Test ISBN validation with empty string."""
        assert not validate_isbn("")
        assert not validate_isbn(None)

    def test_normalize_isbn(self):
        """Test ISBN normalization."""
        assert normalize_isbn("978-2-8006-8734-6") == "9782800687346"
        assert normalize_isbn("0-306-40615-2") == "0306406152"
        assert normalize_isbn("978 2 8006 8734 6") == "9782800687346"


class TestIDFormatValidation:
    """Tests for ID format validation."""

    def test_validate_id_format_regex_match(self):
        """Test ID format validation with regex."""
        assert validate_id_format("123", r"^\d+$")
        assert validate_id_format("ABC123", r"^[A-Z]+\d+$")
        assert validate_id_format("test_user", r"^[a-z_]+$")

    def test_validate_id_format_regex_no_match(self):
        """Test ID format validation with non-matching regex."""
        assert not validate_id_format("abc", r"^\d+$")
        assert not validate_id_format("123ABC", r"^[A-Z]+\d+$")

    def test_validate_id_format_length_constraints(self):
        """Test ID format validation with length constraints."""
        assert validate_id_format("12345", r"^\d+$", min_length=3, max_length=10)
        assert not validate_id_format("12", r"^\d+$", min_length=3, max_length=10)
        assert not validate_id_format("12345678901", r"^\d+$", min_length=3, max_length=10)

    def test_validate_id_format_empty(self):
        """Test ID format validation with empty string."""
        assert not validate_id_format("", r".*")
        assert not validate_id_format(None, r".*")


class TestBorrowerIDValidation:
    """Tests for borrower ID validation."""

    def test_validate_borrower_id_valid(self, db_session):
        """Test borrower ID validation with valid ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        # Create settings
        settings = SystemSettings(id=1)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_borrower_id("101", settings)
        assert is_valid
        assert error is None

    def test_validate_borrower_id_too_short(self, db_session):
        """Test borrower ID validation with too short ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1, id_length_min=3)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_borrower_id("12", settings)
        assert not is_valid
        assert "at least" in error

    def test_validate_borrower_id_too_long(self, db_session):
        """Test borrower ID validation with too long ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1, id_length_max=10)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_borrower_id("12345678901", settings)
        assert not is_valid
        assert "at most" in error

    def test_validate_borrower_id_invalid_format(self, db_session):
        """Test borrower ID validation with invalid format."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1, id_validation_regex=r"^\d+$")
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_borrower_id("ABC123", settings)
        assert not is_valid
        assert "format is invalid" in error

    def test_validate_borrower_id_empty(self, db_session):
        """Test borrower ID validation with empty ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_borrower_id("", settings)
        assert not is_valid
        assert "required" in error


class TestItemIDValidation:
    """Tests for item ID validation."""

    def test_validate_item_id_valid(self, db_session):
        """Test item ID validation with valid ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_item_id("785", settings)
        assert is_valid
        assert error is None

    def test_validate_item_id_too_short(self, db_session):
        """Test item ID validation with too short ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1, id_length_min=3)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_item_id("12", settings)
        assert not is_valid
        assert "at least" in error

    def test_validate_item_id_empty(self, db_session):
        """Test item ID validation with empty ID."""
        from src.bcd_api.models.system_settings import SystemSettings

        settings = SystemSettings(id=1)
        db_session.add(settings)
        db_session.commit()

        is_valid, error = validate_item_id("", settings)
        assert not is_valid
        assert "required" in error
