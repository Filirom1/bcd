from datetime import date
from unittest.mock import MagicMock

import pytest

from src.bcd_api.core.exceptions import (
    DuplicateItemIDException,
    NotFoundError,
    NotFoundException,
    ValidationError,
)
from src.bcd_api.services.catalog._validation import (
    _ean13_to_issn,
    normalize_identifier,
    normalize_item_id,
    parse_item_acquisition_date,
    require_item,
    require_record,
    validate_item_id_available,
)


def test_require_record_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(NotFoundError):
        require_record(db, 999)


def test_require_record_found():
    db = MagicMock()
    record = object()
    db.query.return_value.filter.return_value.first.return_value = record
    assert require_record(db, 1) is record


def test_require_item_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(NotFoundException):
        require_item(db, "999")


def test_require_item_found():
    db = MagicMock()
    item = object()
    db.query.return_value.filter.return_value.first.return_value = item
    assert require_item(db, "1") is item


def test_normalize_item_id():
    assert normalize_item_id(" 1234 ") == "1234"
    assert normalize_item_id("BC-1234", prefix="BC-") == "1234"
    assert normalize_item_id("BC-1234", prefix="  ") == "BC-1234"


def test_validate_item_id_available():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = object()
    with pytest.raises(DuplicateItemIDException):
        validate_item_id_available(db, "1234")


def test_normalize_identifier():
    assert normalize_identifier("978-2-07-040850-4") == "isbn:9782070408504"
    # ISSN format check
    assert normalize_identifier("2070-4085") == "issn:2070-4085"
    # 977 EAN-13 check
    assert normalize_identifier("9771144165005") == "issn:1144-1658"


def test_normalize_identifier_invalid_977(monkeypatch):
    import src.bcd_api.services.catalog._validation as val

    monkeypatch.setattr(val, "_ean13_to_issn", lambda x: None)
    with pytest.raises(ValidationError):
        normalize_identifier("9771144165005")


def test_ean13_to_issn_invalid():
    assert _ean13_to_issn("not_a_valid_ean") is None


def test_parse_item_acquisition_date():
    assert parse_item_acquisition_date(None) is None
    d = date(2023, 10, 15)
    assert parse_item_acquisition_date(d) is d
    assert parse_item_acquisition_date("2023-10-15") == d
    assert parse_item_acquisition_date("invalid-date") is None
    assert parse_item_acquisition_date(12345) is None
