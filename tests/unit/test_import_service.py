"""Unit tests for import_service._normalize_isbn().

Covers ISSN preservation, isbn: prefix for books, and edge cases.
"""

import pytest

from src.bcd_api.services.import_service import _normalize_isbn


class TestNormalizeIsbn:
    """Tests for _normalize_isbn() — now returns prefixed identifiers."""

    # --- ISSN cases ---

    def test_bare_issn_gets_issn_prefix(self):
        assert _normalize_isbn("1163-7706") == "issn:1163-7706"

    def test_bare_issn_uppercase_x_check_digit(self):
        assert _normalize_isbn("0336-743X") == "issn:0336-743X"

    def test_bare_issn_lowercase_x_normalized_to_uppercase(self):
        assert _normalize_isbn("0336-743x") == "issn:0336-743X"

    def test_prefixed_issn_returned_as_is(self):
        assert _normalize_isbn("issn:1163-7706") == "issn:1163-7706"

    def test_prefixed_issn_uppercase_prefix(self):
        assert _normalize_isbn("ISSN:0336-743X") == "issn:0336-743X"

    def test_eight_digit_string_without_hyphen_is_invalid(self):
        # "11637706" is not ISSN (no hyphen) and not ISBN (8 digits)
        assert _normalize_isbn("11637706") is None

    def test_issn_wrong_format_without_hyphen_invalid(self):
        # 8 digits is not 10 or 13, so invalid
        assert _normalize_isbn("01234567") is None

    # --- ISBN cases ---

    def test_isbn13_with_hyphens_returns_with_isbn_prefix(self):
        assert _normalize_isbn("978-2-07-061275-8") == "isbn:9782070612758"

    def test_isbn13_bare_returns_with_isbn_prefix(self):
        assert _normalize_isbn("9782070612758") == "isbn:9782070612758"

    def test_isbn10_with_hyphens_returns_with_isbn_prefix(self):
        assert _normalize_isbn("2-07-061275-6") == "isbn:2070612756"

    def test_isbn10_bare_returns_with_isbn_prefix(self):
        assert _normalize_isbn("2070612756") == "isbn:2070612756"

    def test_already_prefixed_isbn_idempotent(self):
        assert _normalize_isbn("isbn:9782070612758") == "isbn:9782070612758"

    def test_already_prefixed_isbn_with_uppercase(self):
        assert _normalize_isbn("ISBN:9782070612758") == "isbn:9782070612758"

    # --- Empty / invalid ---

    def test_empty_string_returns_none(self):
        assert _normalize_isbn("") is None

    def test_none_equivalent_whitespace_returns_none(self):
        assert _normalize_isbn("   ") is None

    def test_invalid_length_returns_none(self):
        # 12 digits is not ISBN-10 or ISBN-13
        assert _normalize_isbn("123456789012") is None

    def test_non_numeric_returns_none(self):
        assert _normalize_isbn("not-an-isbn") is None
