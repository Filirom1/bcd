"""Private validation helpers for the catalog domain."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import NotFoundError, NotFoundException
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.utils.catalog_input import _ean13_to_issn, classify_catalog_input


def require_record(db: Session, record_id: int) -> BibliographicRecord:
    """Verify record exists and return it, raising NotFoundError otherwise."""
    record = db.query(BibliographicRecord).filter(BibliographicRecord.id == record_id).first()
    if not record:
        raise NotFoundError("Bibliographic record", record_id)
    return record


def require_item(db: Session, item_id: str) -> Item:
    """Verify item exists and return it, raising NotFoundException otherwise."""
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise NotFoundException(resource="Item", identifier=item_id)
    return item


def normalize_item_id(item_id: str, prefix: Optional[str] = None) -> str:
    """Clean item ID and strip barcode prefix if configured."""
    cleaned = item_id.strip()
    if prefix:
        prefix_strip = prefix.strip()
        if prefix_strip and cleaned.startswith(prefix_strip):
            cleaned = cleaned[len(prefix_strip):]
    return cleaned


def item_id_search_values(item_id: str, prefix: Optional[str] = None) -> set[str]:
    """Return item ID values that should match a prefixed or raw barcode search."""
    cleaned = item_id.strip()
    prefix_strip = (prefix or "").strip()
    values = {cleaned}

    if prefix_strip:
        raw_id = normalize_item_id(cleaned, prefix_strip)
        values.add(raw_id)
        values.add(f"{prefix_strip}{raw_id}")

    return values


def validate_item_id_available(db: Session, item_id: str) -> None:
    """Raise ConflictError/DuplicateItemIDException if item_id already in use."""
    existing = db.query(Item).filter(Item.item_id == item_id).first()
    if existing:
        from src.bcd_api.core.exceptions import DuplicateItemIDException
        raise DuplicateItemIDException(item_id)


def normalize_identifier(isbn_or_issn: str) -> str:
    """Normalize a supported ISBN, ISSN, or EAN-977 into storage format."""
    compact = (isbn_or_issn or "").replace("-", "").replace(" ", "")
    # Keep this compatibility seam for callers that monkeypatch the legacy
    # helper; classification itself remains centralized in catalog_input.py.
    if compact.startswith("977") and len(compact) == 13 and _ean13_to_issn(compact) is None:
        from src.bcd_api.core.exceptions import ValidationError
        raise ValidationError(f"Unsupported bibliographic identifier: {isbn_or_issn}")
    classified = classify_catalog_input(isbn_or_issn)
    if not classified.normalized_identifier:
        from src.bcd_api.core.exceptions import ValidationError
        raise ValidationError(f"Unsupported bibliographic identifier: {isbn_or_issn}")
    return classified.normalized_identifier


def parse_item_acquisition_date(value: Optional[str | date]) -> Optional[date]:
    """Parse acquisition date or return date object directly."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None
