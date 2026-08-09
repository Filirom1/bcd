import pytest
from pydantic import ValidationError

from src.bcd_api.schemas.bibliographic_record import (
    BibliographicRecordCreate, BibliographicRecordResponse,
    BibliographicRecordSummary, BibliographicRecordUpdate,
)


def test_create_schema_normalizes_isbn_and_dewey():
    record = BibliographicRecordCreate(title="Book", isbn=" 978-123 ", dewey_number="800.abc/1")
    assert record.isbn == "isbn:978-123"
    assert record.dewey_number == "800.ABC1"
    assert record.medium_type == "Livre"


def test_create_schema_detects_issn():
    record = BibliographicRecordCreate(title="Magazine", isbn="1234-5678")
    assert record.isbn == "issn:1234-5678"


@pytest.mark.parametrize("field, value", [("title", ""), ("publication_year", 999), ("page_count", -1)])
def test_create_schema_rejects_invalid_values(field, value):
    payload = {"title": "Book", field: value}
    if field == "title":
        payload["title"] = value
    with pytest.raises(ValidationError):
        BibliographicRecordCreate(**payload)


def test_response_deserializes_json_fields_and_defaults_empty():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    response = BibliographicRecordResponse(id=1, title="Book", total_items=0, created_at=now, updated_at=now, authors='["A"]', illustrators="invalid", keywords=None)
    assert response.authors == ["A"]
    assert response.illustrators == []
    assert response.keywords == []


def test_summary_deserializes_authors():
    summary = BibliographicRecordSummary(id=1, title="Book", authors='["A", "B"]', publication_year=None, medium_type="Livre", total_items=0, isbn=None)
    assert summary.authors == ["A", "B"]


def test_update_schema_normalizes_isbn_and_allows_partial_data():
    update = BibliographicRecordUpdate(isbn="1234567890")
    assert update.isbn == "isbn:1234567890"
    assert update.title is None
