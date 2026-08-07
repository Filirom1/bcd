"""Private validation helpers for the catalog domain."""

import re
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import NotFoundError, NotFoundException, ConflictError
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item


def require_record(db: Session, record_id: int) -> BiblographicRecord:
    """Verify record exists and return it, raising NotFoundError otherwise."""
    record = db.query(BiblographicRecord).filter(BiblographicRecord.id == record_id).first()
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


def validate_item_id_available(db: Session, item_id: str) -> None:
    """Raise ConflictError/DuplicateItemIDException if item_id already in use."""
    existing = db.query(Item).filter(Item.item_id == item_id).first()
    if existing:
        from src.bcd_api.core.exceptions import DuplicateItemIDException
        raise DuplicateItemIDException(item_id)


def normalize_identifier(isbn_or_issn: str) -> str:
    """Clean and return isbn:xxx or issn:xxx from input identifier."""
    from src.bcd_api.services.external.sudoc import ISSN_PATTERN as SUDOC_ISSN_PATTERN
    
    normalized = isbn_or_issn.replace(" ", "").strip()

    # If it's periodical EAN-13
    if re.match(r"^\d{13}$", normalized) and normalized.startswith("977"):
        from ._validation import _ean13_to_issn
        extracted = _ean13_to_issn(normalized)
        if not extracted:
            from src.bcd_api.core.exceptions import ValidationError
            raise ValidationError(f"Barcode {isbn_or_issn} does not yield a valid ISSN")
        normalized = extracted

    if SUDOC_ISSN_PATTERN.match(normalized):
        return f"issn:{normalized.upper()}"
    else:
        bare = normalized.replace("-", "")
        return f"isbn:{bare}"


_EAN13_PERIODICAL_RE = re.compile(r"^977(\d{7})\d{3}$")


def _ean13_to_issn(ean13: str) -> Optional[str]:
    """Extract and validate ISSN from a kiosk EAN-13 barcode (prefix 977)."""
    m = _EAN13_PERIODICAL_RE.match(ean13)
    if not m:
        return None
    digits = m.group(1)
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(digits, weights))
    check = (11 - (total % 11)) % 11
    check_char = "X" if check == 10 else str(check)
    return f"{digits[:4]}-{digits[4:7]}{check_char}"


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
