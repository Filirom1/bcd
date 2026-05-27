"""Catalog Service

Business logic for bibliographic records and items management.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, date

import httpx

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from ...shared.constants import MediumType, IDFormat
from ..core.config import settings
from ..core.exceptions import NotFoundError, ValidationError, ConflictError, NotFoundException
from ..models.bibliographic_record import BiblographicRecord
from ..models.hold import Hold
from ..models.item import Item
from ..schemas.bibliographic_record import BiblographicRecordCreate
from ..schemas.item import ItemCreate
from .bnf_service import search_by_isbn
from .google_books_service import search_by_isbn as google_search_by_isbn
from .sudoc_service import (
    search_by_isbn as sudoc_search_by_isbn,
    search_by_issn as sudoc_search_by_issn,
    ISSN_PATTERN as SUDOC_ISSN_PATTERN,
)

logger = logging.getLogger(__name__)


def _download_cover(isbn: str) -> Optional[str]:
    """
    Download a cover image, trying multiple providers (Amazon, Open Library,
    Google Books, geobib/BNF) in cascade.

    Accepts identifiers with or without ``isbn:`` / ``issn:`` prefix.
    Returns the filename ('{isbn}.jpg') on success, None if no cover found.
    Idempotent: returns the cached filename if the file already exists.
    """
    from . import cover_service
    return cover_service.download_cover(isbn, covers_dir=Path("data/covers"))


_EAN13_PERIODICAL_RE = re.compile(r"^977(\d{7})\d{3}$")


def _ean13_to_issn(ean13: str) -> Optional[str]:
    """Extract and validate ISSN from a kiosk EAN-13 barcode (prefix 977).

    Kiosk EAN-13 structure: 977 + 7 ISSN digits (no check digit) + 2 issue digits + 1 EAN check.
    ISSN check digit: modulo 11, X = 10.

    Example: 9771163770025 → "1163-770X"
    """
    m = _EAN13_PERIODICAL_RE.match(ean13)
    if not m:
        return None
    digits = m.group(1)  # 7 ISSN digits without check digit
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(digits, weights))
    check = (11 - (total % 11)) % 11
    check_char = "X" if check == 10 else str(check)
    return f"{digits[:4]}-{digits[4:7]}{check_char}"


def create_bibliographic_record(
    db: Session, record_data: BiblographicRecordCreate, isbn_lookup: bool = True
) -> BiblographicRecord:
    """
    Create a new bibliographic record.

    Args:
        db: Database session
        record_data: Bibliographic record data
        isbn_lookup: If True and ISBN provided, lookup BNF API first

    Returns:
        Created bibliographic record

    Raises:
        ValidationError: If ISBN already exists
        ConflictError: If duplicate ISBN found
    """
    # Check for duplicate ISBN
    if record_data.isbn:
        existing = (
            db.query(BiblographicRecord)
            .filter(BiblographicRecord.isbn == record_data.isbn)
            .first()
        )
        if existing:
            raise ConflictError(f"ISBN {record_data.isbn} already exists (record ID: {existing.id})")

    # BNF API lookup if requested and ISBN provided
    bnf_data = None
    if isbn_lookup and record_data.isbn:
        try:
            logger.info(f"Looking up ISBN {record_data.isbn} in BNF catalog")
            bnf_data = search_by_isbn(record_data.isbn)
            if bnf_data:
                logger.info(f"Found BNF data for ISBN {record_data.isbn}")
        except Exception as e:
            logger.warning(f"BNF API lookup failed for ISBN {record_data.isbn}: {e}")
            # Continue with manual entry if BNF lookup fails

    # Prepare data for database (convert lists to JSON)
    if bnf_data:
        # Merge: BNF data overrides user data, but user can provide fields BNF doesn't have
        merged_data = {**record_data.model_dump(exclude_unset=True), **bnf_data}
        db_data = merged_data
    else:
        db_data = record_data.model_dump()

    # Ensure medium_type has default if not present
    if "medium_type" not in db_data or db_data["medium_type"] is None:
        db_data["medium_type"] = MediumType.LIVRE.value

    # Convert lists to JSON strings for database storage
    if "authors" in db_data and isinstance(db_data["authors"], list):
        db_data["authors"] = json.dumps(db_data["authors"])
    if "illustrators" in db_data and isinstance(db_data["illustrators"], list):
        db_data["illustrators"] = json.dumps(db_data["illustrators"])
    if "keywords" in db_data and isinstance(db_data["keywords"], list):
        db_data["keywords"] = json.dumps(db_data["keywords"])

    # cover_url is a transient field from Google Books — not a model column
    db_data.pop("cover_url", None)

    # Download and cache cover from Open Library (best-effort, silent on failure)
    if db_data.get("isbn") and not db_data.get("cover_image"):
        filename = _download_cover(db_data["isbn"])
        if filename:
            db_data["cover_image"] = filename

    # Create record
    db_record = BiblographicRecord(**db_data)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    logger.info(f"Created bibliographic record ID {db_record.id}: {db_record.title}")
    return db_record


def lookup_isbn(db: Session, isbn: str) -> Optional[Dict[str, Any]]:
    """
    Lookup ISBN/ISSN in BNF / Google Books / SUDOC catalog, checking local database first.

    Args:
        db: Database session
        isbn: ISBN-10, ISBN-13, or ISSN to lookup

    Returns:
        Bibliographic data if found, None if not found

    Raises:
        ConflictError: If ISBN/ISSN already exists in local database
    """
    # Normalize identifier
    normalized_isbn = isbn.replace(" ", "").strip()

    # EAN-13 kiosk barcode for periodicals (prefix 977) → extract bare ISSN
    if re.match(r"^\d{13}$", normalized_isbn) and normalized_isbn.startswith("977"):
        extracted = _ean13_to_issn(normalized_isbn)
        if not extracted:
            raise ValidationError(f"Barcode {isbn} does not yield a valid ISSN")
        normalized_isbn = extracted  # bare "NNNN-NNNX", falls through to ISSN check

    # Detect ISSN vs ISBN; produce prefixed storage form + bare API form
    if SUDOC_ISSN_PATTERN.match(normalized_isbn):
        bare_identifier = normalized_isbn.upper()          # "1163-770X"
        normalized_isbn = f"issn:{bare_identifier}"       # "issn:1163-770X"
    else:
        bare_identifier = normalized_isbn.replace("-", "") # "9782070612758"
        normalized_isbn = f"isbn:{bare_identifier}"       # "isbn:9782070612758"

    # First check if ISBN/ISSN already exists in local database
    existing_record = db.query(BiblographicRecord).filter(
        BiblographicRecord.isbn == normalized_isbn
    ).first()

    if existing_record:
        # ISBN/ISSN already exists - raise conflict error
        error = ConflictError(f"ISBN/ISSN {normalized_isbn} already exists in database")
        error.context = {
            "record_id": existing_record.id,
            "title": existing_record.title,
            "isbn": normalized_isbn,
            "medium_type": existing_record.medium_type,
        }
        raise error

    # Fast path for ISSN: go directly to SUDOC (BNF and Google Books don't index periodicals)
    data = None
    source = None
    is_issn = normalized_isbn.startswith("issn:")

    if is_issn and settings.sudoc_enabled:
        logger.info(f"ISSN detected - querying SUDOC directly for {bare_identifier}")
        try:
            data = sudoc_search_by_issn(bare_identifier)
            if data:
                # Discard whatever isbn/issn SUDOC returned; use our prefixed normalized form
                data.pop("issn", None)
                data["isbn"] = normalized_isbn
                data.setdefault("medium_type", MediumType.PERIODIQUE.value)
                source = "sudoc"
            else:
                logger.info(f"ISSN {bare_identifier} not found in SUDOC")
        except Exception:
            logger.warning(
                f"SUDOC unavailable for ISSN {bare_identifier}", exc_info=True
            )

    # For ISBNs: try BNF, then Google Books, then SUDOC
    if data is None and not is_issn:
        # BNF lookup (primary source for books)
        if settings.bnf_enabled:
            logger.info(f"Looking up ISBN {bare_identifier} in BNF catalog")
            try:
                data = search_by_isbn(bare_identifier)
                if data is not None:
                    source = "bnf"
                else:
                    logger.info(f"ISBN {bare_identifier} not found in BNF catalog")
            except Exception:
                logger.warning(
                    f"BNF unavailable for ISBN {bare_identifier}", exc_info=True
                )

        # Google Books fallback
        if data is None and settings.google_books_enabled:
            logger.info(f"Trying Google Books for ISBN {bare_identifier}")
            try:
                data = google_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "google_books"
            except Exception:
                logger.warning(
                    f"Google Books unavailable for ISBN {bare_identifier}", exc_info=True
                )

        # SUDOC fallback (for ISBNs not found elsewhere)
        if data is None and settings.sudoc_enabled:
            logger.info(f"Trying SUDOC for ISBN {bare_identifier}")
            try:
                data = sudoc_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "sudoc"
            except Exception:
                logger.warning(
                    f"SUDOC unavailable for ISBN {bare_identifier}", exc_info=True
                )

        if data is not None:
            # Store the prefixed isbn form in the result
            data["isbn"] = normalized_isbn

    if data is None:
        logger.info(f"ISBN/ISSN {normalized_isbn} not found in any catalog")
        return None

    data["_source"] = source

    # Pre-download cover from Open Library (books only — no covers for periodicals).
    # Best-effort: silent on failure, idempotent if already cached.
    # _download_cover() handles isbn: prefix stripping and issn: skip internally.
    cover_file = _download_cover(normalized_isbn)
    if cover_file:
        data["cover_image"] = cover_file

    logger.info(f"Successfully found bibliographic data for {normalized_isbn} (source: {source})")
    return data


def get_bibliographic_record(db: Session, record_id: int) -> BiblographicRecord:
    """
    Get bibliographic record by ID.

    Args:
        db: Database session
        record_id: Record ID

    Returns:
        Bibliographic record

    Raises:
        NotFoundError: If record not found
    """
    record = db.query(BiblographicRecord).filter(BiblographicRecord.id == record_id).first()
    if not record:
        raise NotFoundError("Bibliographic record", record_id)
    return record


def search_bibliographic_records(
    db: Session,
    q: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    genre: Optional[str] = None,
    level: Optional[str] = None,
    language: Optional[str] = None,
    target_audience: Optional[str] = None,
    medium_type: Optional[str] = None,
    available_only: Optional[bool] = None,
    borrowed_only: Optional[bool] = None,
    has_holds: Optional[bool] = None,
    shelf_location: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[BiblographicRecord], int]:
    """
    Search bibliographic records with filters.

    Args:
        db: Database session
        q: General search query (searches title, authors)
        title: Title filter (case-insensitive partial match)
        author: Author filter (case-insensitive partial match)
        isbn: ISBN filter (exact match)
        genre: Genre filter
        level: Reading level filter
        language: Language filter (ISO 639 code)
        target_audience: Target audience filter
        medium_type: Medium type filter
        available_only: Only show records with at least one available item
        borrowed_only: Only show records with at least one borrowed item
        limit: Maximum records to return (max 100)
        offset: Offset for pagination

    Returns:
        Tuple of (records list, total count)
    """
    query = db.query(BiblographicRecord)

    # Apply filters
    if q:
        # Full-text search on title, authors, ISBN, catalog ID, and item IDs
        search_term = f"%{q}%"

        # Build search conditions
        search_conditions = [
            BiblographicRecord.title.ilike(search_term),
            BiblographicRecord.subtitle.ilike(search_term),
            BiblographicRecord.authors.ilike(search_term),
            BiblographicRecord.publisher.ilike(search_term),
            BiblographicRecord.collection.ilike(search_term),
            BiblographicRecord.keywords.ilike(search_term),
            BiblographicRecord.description.ilike(search_term),
        ]

        # Add ISBN search if provided (partial match)
        if BiblographicRecord.isbn is not None:
            search_conditions.append(BiblographicRecord.isbn.ilike(search_term))

        # Add catalog ID search if query is numeric
        if q.strip().isdigit():
            search_conditions.append(BiblographicRecord.id == int(q.strip()))

        # Search by item_id - find bibliographic records that have items matching this ID
        from sqlalchemy import exists
        search_conditions.append(
            exists().where(
                and_(
                    Item.bibliographic_record_id == BiblographicRecord.id,
                    Item.item_id.ilike(search_term)
                )
            )
        )

        query = query.filter(or_(*search_conditions))

    if title:
        query = query.filter(BiblographicRecord.title.ilike(f"%{title}%"))

    if author:
        query = query.filter(BiblographicRecord.authors.ilike(f"%{author}%"))

    if isbn:
        query = query.filter(BiblographicRecord.isbn == isbn)

    if genre:
        query = query.filter(BiblographicRecord.genre == genre)

    if level:
        query = query.filter(BiblographicRecord.level == level)

    if language:
        query = query.filter(BiblographicRecord.language == language)

    if target_audience:
        query = query.filter(BiblographicRecord.target_audience == target_audience)

    if medium_type:
        query = query.filter(BiblographicRecord.medium_type == medium_type)

    # Apply availability filters using EXISTS subqueries
    if available_only:
        # Only show records that have at least one available item
        from sqlalchemy import exists
        query = query.filter(
            exists().where(
                and_(
                    Item.bibliographic_record_id == BiblographicRecord.id,
                    Item.status == "available"
                )
            )
        )

    if borrowed_only:
        # Only show records that have at least one item on loan
        from sqlalchemy import exists
        query = query.filter(
            exists().where(
                and_(
                    Item.bibliographic_record_id == BiblographicRecord.id,
                    Item.status == "on_loan"
                )
            )
        )

    if has_holds:
        # Only show records that have at least one active hold (waiting or ready)
        from sqlalchemy import exists
        query = query.filter(
            exists().where(
                and_(
                    Hold.bibliographic_record_id == BiblographicRecord.id,
                    Hold.status.in_(["waiting", "ready"])
                )
            )
        )

    if shelf_location:
        from sqlalchemy import exists
        query = query.filter(
            exists().where(
                and_(
                    Item.bibliographic_record_id == BiblographicRecord.id,
                    Item.shelf_location == shelf_location
                )
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    limit = min(limit, 100)  # Cap at 100
    records = query.offset(offset).limit(limit).all()

    return records, total


def create_item(db: Session, item_data: ItemCreate) -> Item:
    """
    Create a new item (physical copy).

    Args:
        db: Database session
        item_data: Item data

    Returns:
        Created item

    Raises:
        ValidationError: If bibliographic record not found
        ConflictError: If item_id already exists
    """
    # Validate bibliographic record exists
    biblio_record = (
        db.query(BiblographicRecord)
        .filter(BiblographicRecord.id == item_data.bibliographic_record_id)
        .first()
    )
    if not biblio_record:
        from src.bcd_api.core.exceptions import BiblographicRecordNotFoundException
        raise BiblographicRecordNotFoundException(item_data.bibliographic_record_id)

    # Check for duplicate item_id
    existing = db.query(Item).filter(Item.item_id == item_data.item_id).first()
    if existing:
        from src.bcd_api.core.exceptions import DuplicateItemIDException
        raise DuplicateItemIDException(item_data.item_id)

    # Create item (barcode is auto-computed from item_id via property)
    item_dict = item_data.model_dump()
    if item_dict.get('acquisition_date') is None:
        item_dict['acquisition_date'] = date.today()
    db_item = Item(**item_dict)
    db.add(db_item)

    # Maintain denormalized counter
    biblio_record.total_items += 1

    db.commit()
    db.refresh(db_item)

    logger.info(f"Created item {db_item.item_id} for record {biblio_record.title}")
    return db_item


def get_item(db: Session, item_id: str) -> Item:
    """
    Get item by item_id.

    Args:
        db: Database session
        item_id: Item ID (inventory number)

    Returns:
        Item

    Raises:
        NotFoundError: If item not found
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise NotFoundError("Item", item_id)
    return item


def get_items_for_bibliographic_record(
    db: Session, bibliographic_record_id: int
) -> list[dict]:
    """
    Get all items for a bibliographic record with circulation details.

    Args:
        db: Database session
        bibliographic_record_id: Bibliographic record ID

    Returns:
        List of item dictionaries with current_loan info
    """
    from ..models.circulation import CirculationTransaction
    from datetime import date

    items = (
        db.query(Item)
        .filter(Item.bibliographic_record_id == bibliographic_record_id)
        .all()
    )

    result = []
    for item in items:
        item_dict = {
            "id": item.id,  # Database ID for Vue key binding
            "item_id": item.item_id,
            "call_number": item.call_number,
            "shelf_location": item.shelf_location,
            "status": item.status,
            "condition": item.condition,
            "loanable": item.loanable,
            "acquisition_date": item.acquisition_date,
            "funding_source": item.funding_source,
            "current_loan": None
        }

        # If item is on loan, get borrower info
        if item.status == "on_loan":
            active_loan = db.query(CirculationTransaction).filter(
                and_(
                    CirculationTransaction.item_id == item.id,
                    CirculationTransaction.return_date.is_(None)
                )
            ).options(
                joinedload(CirculationTransaction.borrower)
            ).first()

            if active_loan:
                item_dict["current_loan"] = {
                    "borrower_id": active_loan.borrower.borrower_id,
                    "borrower_name": active_loan.borrower.full_name,
                    "due_date": active_loan.due_date.strftime('%d/%m/%Y'),
                    "is_overdue": active_loan.due_date < date.today(),
                    "days_overdue": (date.today() - active_loan.due_date).days if active_loan.due_date < date.today() else 0
                }

        result.append(item_dict)

    return result


# === US5: Bulk Catalog Operations ===


def bulk_edit_records(
    db: Session,
    record_ids: list[int],
    genre: Optional[str] = None,
    target_audience: Optional[str] = None,
    language: Optional[str] = None,
    medium_type: Optional[str] = None
) -> dict:
    """
    Bulk edit bibliographic records (US5).

    Updates common fields for multiple records in a single atomic transaction.
    Null values mean "no change" to that field.

    Args:
        db: Database session
        record_ids: List of record IDs to update
        genre: Genre to set (null = no change)
        target_audience: Target audience to set (null = no change)
        language: Language to set (null = no change)
        medium_type: Medium type to set (null = no change)

    Returns:
        Operation result with counts

    Raises:
        ValidationError: If no valid updates provided
    """
    if not record_ids:
        raise ValidationError("No record IDs provided")

    # Build update dict (only include non-None values)
    updates = {}
    if genre is not None:
        updates["genre"] = genre
    if target_audience is not None:
        updates["target_audience"] = target_audience
    if language is not None:
        updates["language"] = language
    if medium_type is not None:
        updates["medium_type"] = medium_type

    if not updates:
        raise ValidationError("No fields to update (all values are null)")

    try:
        # Atomic transaction - all succeed or all fail
        records = db.query(BiblographicRecord).filter(
            BiblographicRecord.id.in_(record_ids)
        ).all()

        if not records:
            raise NotFoundError(f"No records found with provided IDs")

        updated_count = 0
        for record in records:
            for field, value in updates.items():
                setattr(record, field, value)
            updated_count += 1

        db.commit()

        logger.info(f"Bulk edited {updated_count} bibliographic records")

        return {
            "operation": "bulk_edit_records",
            "total_count": len(record_ids),
            "successful_count": updated_count,
            "failed_count": 0,
            "details": {"updated_fields": list(updates.keys())}
        }

    except Exception as e:
        logger.error(f"Bulk edit records failed: {e}")
        raise


def bulk_delete_records(db: Session, record_ids: list[int]) -> dict:
    """
    Bulk delete bibliographic records (US5).

    Deletes multiple records in a single atomic transaction.
    CASCADE delete removes associated items and circulation history.

    Args:
        db: Database session
        record_ids: List of record IDs to delete

    Returns:
        Operation result with counts

    Raises:
        NotFoundError: If no records found
    """
    if not record_ids:
        raise ValidationError("No record IDs provided")

    try:
        # Atomic transaction - all succeed or all fail
        # Fetch records WITH items in one query (eager loading)
        records = db.query(BiblographicRecord)\
            .options(joinedload(BiblographicRecord.items))\
            .filter(BiblographicRecord.id.in_(record_ids))\
            .all()

        if not records:
            raise NotFoundError(f"No records found with provided IDs")

        deleted_count = len(records)

        # Validate: Collect all item IDs and check for active loans in ONE batch query
        all_item_ids = []
        for record in records:
            all_item_ids.extend([item.id for item in record.items])

        # Single batch query to check for ANY active loan
        if all_item_ids:
            from src.bcd_api.models.circulation import CirculationTransaction
            from src.bcd_api.models.borrower import Borrower

            item_with_loan = db.query(
                Item.item_id,
                Borrower.full_name,
                CirculationTransaction.due_date
            ).join(
                CirculationTransaction,
                CirculationTransaction.item_id == Item.id
            ).join(
                Borrower,
                Borrower.id == CirculationTransaction.borrower_id
            ).filter(
                Item.id.in_(all_item_ids),
                CirculationTransaction.return_date.is_(None)
            ).first()

            if item_with_loan:
                from src.bcd_api.core.exceptions import ItemHasActiveLoanException
                raise ItemHasActiveLoanException(
                    item_id=item_with_loan.item_id,
                    borrower_name=item_with_loan.full_name,
                    due_date=item_with_loan.due_date
                )

        # CASCADE delete (defined in model relationships)
        # - Deletes all associated items
        # - Deletes circulation history for those items
        for record in records:
            db.delete(record)

        db.commit()

        logger.info(f"Bulk deleted {deleted_count} bibliographic records")

        return {
            "operation": "bulk_delete_records",
            "total_count": len(record_ids),
            "successful_count": deleted_count,
            "failed_count": 0
        }

    except Exception as e:
        logger.error(f"Bulk delete records failed: {e}")
        raise


# === US6: Single Catalog Record/Item Editing ===


def update_record(db: Session, record_id: int, update_data: dict) -> BiblographicRecord:
    """
    Update a single bibliographic record (US6).

    Args:
        db: Database session
        record_id: Record ID
        update_data: Fields to update

    Returns:
        Updated bibliographic record

    Raises:
        NotFoundError: If record not found
    """
    record = db.query(BiblographicRecord).filter(BiblographicRecord.id == record_id).first()

    if not record:
        raise NotFoundException(resource="Bibliographic record", identifier=record_id)

    # Convert lists to JSON for database storage
    if "authors" in update_data and isinstance(update_data["authors"], list):
        update_data["authors"] = json.dumps(update_data["authors"])
    if "illustrators" in update_data and isinstance(update_data["illustrators"], list):
        update_data["illustrators"] = json.dumps(update_data["illustrators"])
    if "keywords" in update_data and isinstance(update_data["keywords"], list):
        update_data["keywords"] = json.dumps(update_data["keywords"])

    # Update fields
    for field, value in update_data.items():
        if value is not None and hasattr(record, field):
            setattr(record, field, value)

    db.commit()
    db.refresh(record)

    logger.info(f"Updated bibliographic record {record_id}")

    return record


def update_item(db: Session, item_id: str, update_data: dict) -> Item:
    """
    Update a single item (US6).

    Args:
        db: Database session
        item_id: Item barcode (item_id field, not database id)
        update_data: Fields to update (barcode/item_id cannot be changed)

    Returns:
        Updated item

    Raises:
        NotFoundError: If item not found
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()

    if not item:
        raise NotFoundException(resource="Item", identifier=item_id)

    # Barcode (item_id) is immutable - ignore if in update_data
    if "item_id" in update_data:
        del update_data["item_id"]

    # Convert date strings to date objects (SQLite requires date objects, not strings)
    if "acquisition_date" in update_data and isinstance(update_data["acquisition_date"], str):
        try:
            update_data["acquisition_date"] = datetime.strptime(update_data["acquisition_date"], "%Y-%m-%d").date()
        except ValueError:
            # Invalid date format - skip this field
            logger.warning(f"Invalid acquisition_date format: {update_data['acquisition_date']}")
            del update_data["acquisition_date"]

    # Update fields
    for field, value in update_data.items():
        if value is not None and hasattr(item, field):
            setattr(item, field, value)

    db.commit()
    db.refresh(item)

    logger.info(f"Updated item {item_id} (barcode: {item.item_id})")

    return item


def _check_item_has_active_loan(db: Session, item: Item) -> Optional[dict]:
    """
    Check if an item is currently on loan.

    Args:
        db: Database session
        item: Item model instance

    Returns:
        Dict with borrower_name and due_date if on loan, None otherwise
    """
    from src.bcd_api.models.circulation import CirculationTransaction
    from sqlalchemy import and_

    active_loan = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            CirculationTransaction.return_date.is_(None)
        )
    ).first()

    if active_loan:
        return {
            "borrower_name": active_loan.borrower.full_name,
            "due_date": active_loan.due_date
        }
    return None


def delete_item(db: Session, item_id: str) -> None:
    """
    Delete an item by barcode.

    Args:
        db: Database session
        item_id: Item barcode (item_id field)

    Raises:
        NotFoundError: If item not found
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()

    if not item:
        raise NotFoundException(resource="Item", identifier=item_id)

    # Validate: Check for active loan
    active_loan_info = _check_item_has_active_loan(db, item)
    if active_loan_info:
        from src.bcd_api.core.exceptions import ItemHasActiveLoanException
        raise ItemHasActiveLoanException(
            item_id=item_id,
            borrower_name=active_loan_info["borrower_name"],
            due_date=active_loan_info["due_date"]
        )

    biblio_record = db.query(BiblographicRecord).filter(
        BiblographicRecord.id == item.bibliographic_record_id
    ).first()

    db.delete(item)

    if biblio_record and biblio_record.total_items > 0:
        biblio_record.total_items -= 1

    db.commit()

    logger.info(f"Deleted item {item_id}")


def get_available_item_ids(
    db: Session,
    count: int = 30,
    start_from: Optional[str] = None,
    contiguous: bool = True
) -> Dict[str, Any]:
    """
    Generate a list of available item IDs that are not currently in use.

    For numeric ID format, finds free IDs starting from start_from.
    - contiguous=True  : finds the first block of `count` consecutive free IDs
    - contiguous=False : collects the next `count` free IDs one by one (may have gaps)

    All returned IDs are guaranteed to be not currently in use.

    For alphanumeric ID format, raises NotImplementedError (future enhancement).

    Args:
        db: Database session
        count: Number of IDs to generate (1-1000)
        start_from: Optional starting ID (if omitted, searches from 1)
        contiguous: If True (default), IDs form a gapless block.
                    If False, IDs are the next N free slots (may have gaps).

    Returns:
        Dictionary with start_id, end_id, ids list, count, id_format and contiguous

    Raises:
        NotImplementedError: If id_format is alphanumeric (not yet supported)
        ValueError: If count is out of range or start_from is invalid
    """
    from .settings_service import get_settings

    # Get system settings for ID format
    settings = get_settings(db)

    # Validate count
    if count < 1 or count > 1000:
        raise ValueError("Count must be between 1 and 1000")

    if settings.id_format == IDFormat.NUMERIC.value:
        # Get all currently used IDs
        rows = db.query(Item.item_id).all()
        used_ids = set()
        for (iid,) in rows:
            try:
                n = int(iid)
                if n > 0:
                    used_ids.add(n)
            except (ValueError, TypeError):
                pass

        # Determine starting point
        if start_from:
            try:
                start_point = int(start_from)
            except ValueError:
                raise ValueError(f"Invalid start_from value for numeric format: {start_from}")
        else:
            start_point = 1

        ids = []
        candidate = start_point

        if contiguous:
            # Find first gapless block of `count` free IDs
            while len(ids) < count:
                # Check if we have a contiguous block starting at candidate
                all_free = True
                for offset in range(count - len(ids)):
                    if (candidate + offset) in used_ids:
                        all_free = False
                        # Skip to next position after the conflict
                        candidate = candidate + offset + 1
                        break

                if all_free:
                    # Found a contiguous block - collect the IDs
                    for offset in range(count - len(ids)):
                        ids.append(str(candidate + offset))
                    break
        else:
            # Scatter mode: collect next N free IDs one by one (gaps allowed)
            while len(ids) < count:
                if candidate not in used_ids:
                    ids.append(str(candidate))
                candidate += 1

        return {
            "start_id": ids[0],
            "end_id": ids[-1],
            "ids": ids,
            "count": count,
            "id_format": settings.id_format,
            "contiguous": contiguous
        }

    else:  # alphanumeric
        # For alphanumeric, would need to parse pattern (e.g., ITEM001)
        # and generate next IDs following that pattern
        # Not implemented yet - future enhancement
        raise NotImplementedError(
            "Alphanumeric ID generation not yet implemented. "
            "Please set id_format to 'numeric' in system settings."
        )
