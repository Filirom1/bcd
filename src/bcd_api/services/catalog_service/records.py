"""Bibliographic Record Service (Internal)

Handles business logic for bibliographic records management.
"""

import json
import logging
import re
from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy import and_, or_, case, func
from sqlalchemy.orm import Session, joinedload

from ....shared.constants import MediumType, ItemStatus
from ...core.config import settings
from ...core.exceptions import ConflictError, NotFoundError, NotFoundException, ValidationError
from ...models.bibliographic_record import BiblographicRecord
from ...models.hold import Hold
from ...models.item import Item
from ...schemas.bibliographic_record import BiblographicRecordCreate
from ..sudoc_service import (
    ISSN_PATTERN as SUDOC_ISSN_PATTERN,
)

logger = logging.getLogger(__name__)


def _download_cover(isbn: str) -> Optional[str]:
    """
    Download a cover image, trying multiple providers (Amazon, Open Library,
    Google Books, geobib/BNF) in cascade.
    """
    from .. import cover_service
    return cover_service.download_cover(isbn, covers_dir=None)


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


def create_bibliographic_record(
    db: Session, record_data: BiblographicRecordCreate, isbn_lookup: bool = True
) -> BiblographicRecord:
    """
    Create a new bibliographic record.
    """
    if record_data.isbn:
        existing = (
            db.query(BiblographicRecord)
            .filter(BiblographicRecord.isbn == record_data.isbn)
            .first()
        )
        if existing:
            raise ConflictError(f"ISBN {record_data.isbn} already exists (record ID: {existing.id})")

    bnf_data = None
    if isbn_lookup and record_data.isbn:
        try:
            logger.info(f"Looking up ISBN {record_data.isbn} in BNF catalog")
            from .. import catalog_service
            bnf_data = catalog_service.search_by_isbn(record_data.isbn)
            if bnf_data:
                logger.info(f"Found BNF data for ISBN {record_data.isbn}")
        except Exception as e:
            logger.warning(f"BNF API lookup failed for ISBN {record_data.isbn}: {e}")

    if bnf_data:
        merged_data = {**record_data.model_dump(exclude_unset=True), **bnf_data}
        db_data = merged_data
    else:
        db_data = record_data.model_dump()

    if "medium_type" not in db_data or db_data["medium_type"] is None:
        db_data["medium_type"] = MediumType.LIVRE.value

    if "authors" in db_data and isinstance(db_data["authors"], list):
        db_data["authors"] = json.dumps(db_data["authors"])
    if "illustrators" in db_data and isinstance(db_data["illustrators"], list):
        db_data["illustrators"] = json.dumps(db_data["illustrators"])
    if "keywords" in db_data and isinstance(db_data["keywords"], list):
        db_data["keywords"] = json.dumps(db_data["keywords"])

    db_data.pop("cover_url", None)

    if db_data.get("isbn") and not db_data.get("cover_image"):
        filename = _download_cover(db_data["isbn"])
        if filename:
            db_data["cover_image"] = filename

    db_record = BiblographicRecord(**db_data)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    logger.info(f"Created bibliographic record ID {db_record.id}: {db_record.title}")
    return db_record


def lookup_isbn(db: Session, isbn: str) -> Optional[Dict[str, Any]]:
    """
    Lookup ISBN/ISSN in BNF / Google Books / SUDOC catalog, checking local database first.
    """
    normalized_isbn = isbn.replace(" ", "").strip()

    if re.match(r"^\d{13}$", normalized_isbn) and normalized_isbn.startswith("977"):
        extracted = _ean13_to_issn(normalized_isbn)
        if not extracted:
            raise ValidationError(f"Barcode {isbn} does not yield a valid ISSN")
        normalized_isbn = extracted

    if SUDOC_ISSN_PATTERN.match(normalized_isbn):
        bare_identifier = normalized_isbn.upper()
        normalized_isbn = f"issn:{bare_identifier}"
    else:
        bare_identifier = normalized_isbn.replace("-", "")
        normalized_isbn = f"isbn:{bare_identifier}"

    existing_record = db.query(BiblographicRecord).filter(
        BiblographicRecord.isbn == normalized_isbn
    ).first()

    if existing_record:
        error = ConflictError(f"ISBN/ISSN {normalized_isbn} already exists in database")
        error.context = {
            "record_id": existing_record.id,
            "title": existing_record.title,
            "isbn": normalized_isbn,
            "medium_type": existing_record.medium_type,
        }
        raise error

    data = None
    source = None
    is_issn = normalized_isbn.startswith("issn:")

    from .. import catalog_service

    if is_issn and settings.sudoc_enabled:
        logger.info(f"ISSN detected - querying SUDOC directly for {bare_identifier}")
        try:
            data = catalog_service.sudoc_search_by_issn(bare_identifier)
            if data:
                data.pop("issn", None)
                data["isbn"] = normalized_isbn
                data["medium_type"] = MediumType.PERIODIQUE.value
                source = "sudoc"
            else:
                logger.info(f"ISSN {bare_identifier} not found in SUDOC")
        except Exception:
            logger.warning(
                f"SUDOC unavailable for ISSN {bare_identifier}", exc_info=True
            )

    if data is None and not is_issn:
        if settings.bnf_enabled:
            logger.info(f"Looking up ISBN {bare_identifier} in BNF catalog")
            try:
                data = catalog_service.search_by_isbn(bare_identifier)
                if data is not None:
                    source = "bnf"
                else:
                    logger.info(f"ISBN {bare_identifier} not found in BNF catalog")
            except Exception:
                logger.warning(
                    f"BNF unavailable for ISBN {bare_identifier}", exc_info=True
                )

        if data is None and settings.google_books_enabled:
            logger.info(f"Trying Google Books for ISBN {bare_identifier}")
            try:
                data = catalog_service.google_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "google_books"
            except Exception:
                logger.warning(
                    f"Google Books unavailable for ISBN {bare_identifier}", exc_info=True
                )

        if data is None and settings.sudoc_enabled:
            logger.info(f"Trying SUDOC for ISBN {bare_identifier}")
            try:
                data = catalog_service.sudoc_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "sudoc"
            except Exception:
                logger.warning(
                    f"SUDOC unavailable for ISBN {bare_identifier}", exc_info=True
                )

        if data is not None:
            data["isbn"] = normalized_isbn

    if data is None:
        logger.info(f"ISBN/ISSN {normalized_isbn} not found in any catalog")
        return None

    data["_source"] = source

    cover_file = _download_cover(normalized_isbn)
    if cover_file:
        data["cover_image"] = cover_file

    logger.info(f"Successfully found bibliographic data for {normalized_isbn} (source: {source})")
    return data


def get_bibliographic_record(db: Session, record_id: int) -> BiblographicRecord:
    """
    Get bibliographic record by ID.
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
    """
    query = db.query(BiblographicRecord)

    if q:
        search_term = f"%{q}%"
        search_conditions = [
            BiblographicRecord.title.ilike(search_term),
            BiblographicRecord.subtitle.ilike(search_term),
            BiblographicRecord.authors.ilike(search_term),
            BiblographicRecord.publisher.ilike(search_term),
            BiblographicRecord.collection.ilike(search_term),
            BiblographicRecord.keywords.ilike(search_term),
            BiblographicRecord.description.ilike(search_term),
        ]

        if BiblographicRecord.isbn is not None:
            search_conditions.append(BiblographicRecord.isbn.ilike(search_term))

        if q.strip().isdigit():
            search_conditions.append(BiblographicRecord.id == int(q.strip()))

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

    if level:
        query = query.filter(BiblographicRecord.level == level)

    if language:
        query = query.filter(BiblographicRecord.language == language)

    if target_audience:
        query = query.filter(BiblographicRecord.target_audience == target_audience)

    if medium_type:
        query = query.filter(BiblographicRecord.medium_type == medium_type)

    if available_only:
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

    total = query.count()
    limit = min(limit, 100)
    records = query.offset(offset).limit(limit).all()

    return records, total


def bulk_edit_records(
    db: Session,
    record_ids: list[int],
    level: Optional[str] = None,
    target_audience: Optional[str] = None,
    language: Optional[str] = None,
    medium_type: Optional[str] = None,
    publisher: Optional[str] = None,
    collection: Optional[str] = None,
    binding_type: Optional[str] = None
) -> dict:
    """
    Bulk edit bibliographic records (US5).
    """
    if not record_ids:
        raise ValidationError("No record IDs provided")

    updates = {}
    if level is not None:
        updates["level"] = level
    if target_audience is not None:
        updates["target_audience"] = target_audience
    if language is not None:
        updates["language"] = language
    if medium_type is not None:
        updates["medium_type"] = medium_type
    if publisher is not None:
        updates["publisher"] = publisher
    if collection is not None:
        updates["collection"] = collection
    if binding_type is not None:
        updates["binding_type"] = binding_type

    if not updates:
        raise ValidationError("No fields to update (all values are null)")

    try:
        records = db.query(BiblographicRecord).filter(
            BiblographicRecord.id.in_(record_ids)
        ).all()

        if not records:
            raise NotFoundError("No records found with provided IDs")

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
    """
    if not record_ids:
        raise ValidationError("No record IDs provided")

    try:
        records = db.query(BiblographicRecord)\
            .options(joinedload(BiblographicRecord.items))\
            .filter(BiblographicRecord.id.in_(record_ids))\
            .all()

        if not records:
            raise NotFoundError("No records found with provided IDs")

        deleted_count = len(records)

        all_item_ids = []
        for record in records:
            all_item_ids.extend([item.id for item in record.items])

        if all_item_ids:
            from ...models.borrower import Borrower
            from ...models.circulation import CirculationTransaction

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
                from ...core.exceptions import ItemHasActiveLoanException
                raise ItemHasActiveLoanException(
                    item_id=item_with_loan.item_id,
                    borrower_name=item_with_loan.full_name,
                    due_date=item_with_loan.due_date
                )

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


def update_record(db: Session, record_id: int, update_data: dict) -> BiblographicRecord:
    """
    Update a single bibliographic record (US6).
    """
    record = db.query(BiblographicRecord).filter(BiblographicRecord.id == record_id).first()

    if not record:
        raise NotFoundException(resource="Bibliographic record", identifier=record_id)

    if "authors" in update_data and isinstance(update_data["authors"], list):
        update_data["authors"] = json.dumps(update_data["authors"])
    if "illustrators" in update_data and isinstance(update_data["illustrators"], list):
        update_data["illustrators"] = json.dumps(update_data["illustrators"])
    if "keywords" in update_data and isinstance(update_data["keywords"], list):
        update_data["keywords"] = json.dumps(update_data["keywords"])

    for field, value in update_data.items():
        if hasattr(record, field):
            setattr(record, field, value)

    db.commit()
    db.refresh(record)

    logger.info(f"Updated bibliographic record {record_id}")

    return record


def get_shelf_locations(db: Session) -> list[str]:
    """Returns distinct non-empty shelf_location values, sorted."""
    results = (
        db.query(Item.shelf_location)
        .filter(Item.shelf_location.isnot(None), Item.shelf_location != "")
        .distinct()
        .order_by(Item.shelf_location)
        .all()
    )
    return [r[0] for r in results]


def enrich_bibliographic_records_with_availability(db: Session, records: list[BiblographicRecord]) -> list[dict]:
    """
    Enrich bibliographic records with availability, copy counts, and first item information.
    """
    record_ids = [r.id for r in records]

    counts_rows = (
        db.query(
            Item.bibliographic_record_id,
            func.count(Item.id).label("total"),
            func.sum(
                case((Item.status == ItemStatus.AVAILABLE.value, 1), else_=0)
            ).label("available"),
        )
        .filter(Item.bibliographic_record_id.in_(record_ids))
        .group_by(Item.bibliographic_record_id)
        .all()
    )
    counts_by_record = {row.bibliographic_record_id: row for row in counts_rows}

    holds_rows = (
        db.query(Hold.bibliographic_record_id, func.count(Hold.id).label("holds"))
        .filter(
            Hold.bibliographic_record_id.in_(record_ids),
            Hold.status.in_(["waiting", "ready"])
        )
        .group_by(Hold.bibliographic_record_id)
        .all()
    )
    holds_by_record = {row.bibliographic_record_id: row.holds for row in holds_rows}

    all_items = (
        db.query(Item)
        .filter(Item.bibliographic_record_id.in_(record_ids))
        .order_by(
            Item.bibliographic_record_id,
            case((Item.status == ItemStatus.AVAILABLE.value, 0), else_=1),
            Item.id,
        )
        .all()
    )
    first_item_by_record: dict = {}
    for item in all_items:
        if item.bibliographic_record_id not in first_item_by_record:
            first_item_by_record[item.bibliographic_record_id] = item

    records_with_availability = []
    for r in records:
        counts = counts_by_record.get(r.id)
        total_count = counts.total if counts else 0
        available_count = int(counts.available or 0) if counts else 0
        active_holds_count = holds_by_record.get(r.id, 0)

        first_item = first_item_by_record.get(r.id)

        authors = r.authors
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except (json.JSONDecodeError, TypeError):
                authors = []
        elif authors is None:
            authors = []

        record_dict = {
            "id": r.id,
            "record_id": r.id,
            "isbn": r.isbn,
            "isbn_value": r.isbn_value,
            "identifier_type": r.identifier_type,
            "title": r.title,
            "subtitle": r.subtitle,
            "authors": authors,
            "publisher": r.publisher,
            "publication_year": r.publication_year,
            "collection": r.collection,
            "series_number": r.series_number,
            "medium_type": r.medium_type,
            "target_audience": r.target_audience,
            "level": r.level,
            "language": r.language,
            "binding_type": r.binding_type,
            "page_count": r.page_count,
            "has_illustrations": r.has_illustrations,
            "total_items": total_count,
            "total_copies": total_count,
            "available_copies": available_count,
            "active_holds_count": active_holds_count,
            "cover_image": r.cover_image,
            "first_item_id": first_item.item_id if first_item else None,
            "shelf_location": first_item.shelf_location if first_item else None,
            "call_number": first_item.call_number if first_item else None,
        }
        records_with_availability.append(record_dict)

    return records_with_availability
