"""Validation utilities for BCD library system."""

import re
from typing import Optional


def validate_isbn(isbn: str) -> bool:
    """
    Validate ISBN-10 or ISBN-13 format.

    Args:
        isbn: ISBN string to validate

    Returns:
        bool: True if valid ISBN format
    """
    if not isbn:
        return False

    # Remove hyphens and spaces
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    # Check ISBN-10
    if len(clean_isbn) == 10:
        return validate_isbn10(clean_isbn)

    # Check ISBN-13
    if len(clean_isbn) == 13:
        return validate_isbn13(clean_isbn)

    return False


def validate_isbn10(isbn: str) -> bool:
    """Validate ISBN-10 format."""
    if not re.match(r"^\d{9}[\dX]$", isbn):
        return False

    # Calculate checksum
    checksum = 0
    for i in range(9):
        checksum += int(isbn[i]) * (10 - i)

    # Last digit can be X (representing 10)
    if isbn[9] == 'X':
        checksum += 10
    else:
        checksum += int(isbn[9])

    return checksum % 11 == 0


def validate_isbn13(isbn: str) -> bool:
    """Validate ISBN-13 format."""
    if not re.match(r"^\d{13}$", isbn):
        return False

    # Calculate checksum
    checksum = 0
    for i in range(12):
        weight = 1 if i % 2 == 0 else 3
        checksum += int(isbn[i]) * weight

    check_digit = (10 - (checksum % 10)) % 10
    return check_digit == int(isbn[12])


def normalize_isbn(isbn: str) -> str:
    """
    Normalize ISBN by removing hyphens and spaces.

    Args:
        isbn: ISBN string to normalize

    Returns:
        str: Normalized ISBN
    """
    return isbn.replace("-", "").replace(" ", "")


def validate_id_format(
    value: str,
    validation_regex: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> bool:
    """
    Validate ID format against regex and length constraints.

    Args:
        value: ID value to validate
        validation_regex: Regex pattern for validation
        min_length: Minimum length (optional)
        max_length: Maximum length (optional)

    Returns:
        bool: True if valid
    """
    if not value:
        return False

    # Check length
    if min_length and len(value) < min_length:
        return False

    if max_length and len(value) > max_length:
        return False

    # Check regex
    if not re.match(validation_regex, value):
        return False

    return True


def validate_borrower_id(borrower_id: str, settings) -> tuple[bool, Optional[str]]:
    """
    Validate borrower ID against system settings.

    Args:
        borrower_id: Borrower ID to validate
        settings: SystemSettings instance

    Returns:
        tuple: (is_valid, error_message)
    """
    if not borrower_id:
        return False, "Borrower ID is required"

    if len(borrower_id) < settings.id_length_min:
        return False, f"Borrower ID must be at least {settings.id_length_min} characters"

    if len(borrower_id) > settings.id_length_max:
        return False, f"Borrower ID must be at most {settings.id_length_max} characters"

    if not re.match(settings.id_validation_regex, borrower_id):
        return False, f"Borrower ID format is invalid (must match {settings.id_validation_regex})"

    return True, None


def validate_item_id(item_id: str, settings) -> tuple[bool, Optional[str]]:
    """
    Validate item ID against system settings.

    Args:
        item_id: Item ID to validate
        settings: SystemSettings instance

    Returns:
        tuple: (is_valid, error_message)
    """
    if not item_id:
        return False, "Item ID is required"

    if len(item_id) < settings.id_length_min:
        return False, f"Item ID must be at least {settings.id_length_min} characters"

    if len(item_id) > settings.id_length_max:
        return False, f"Item ID must be at most {settings.id_length_max} characters"

    if not re.match(settings.id_validation_regex, item_id):
        return False, f"Item ID format is invalid (must match {settings.id_validation_regex})"

    return True, None
