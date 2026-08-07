"""Commands module for the catalog domain."""

import logging
from datetime import date, datetime
from typing import Any, List, Optional, Set
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from src.bcd_api.core.exceptions import (
    ConflictError,
    NotFoundError,
    NotFoundException,
    ValidationError,
    BiblographicRecordNotFoundException,
    DuplicateItemIDException,
    ItemHasActiveLoanException,
)
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.schemas.bibliographic_record import BiblographicRecordCreate
from src.bcd_api.schemas.item import ItemCreate
from src.shared.constants import MediumType
from ._validation import (
    require_record,
    require_item,
    normalize_item_id,
    validate_item_id_available,
    parse_item_acquisition_date,
)
from ._serialization import encode_record_lists
from .projections import refresh_total_items_in_transaction
from .lookup import _download_cover

logger = logging.getLogger(__name__)


def create_bibliographic_record(
    db: Session, record_data: BiblographicRecordCreate, isbn_lookup: bool = True
) -> BiblographicRecord:
    """Create a new bibliographic record, optionally performing BNF ISBN lookup."""
    try:
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
                from ..external.bnf import search_by_isbn as bnf_search_by_isbn
                bnf_data = bnf_search_by_isbn(record_data.isbn)
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

        # Serialize list fields to JSON strings
        db_data = encode_record_lists(db_data)
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
    except Exception:
        db.rollback()
        raise


def update_record(db: Session, record_id: int, update_data: dict) -> BiblographicRecord:
    """Update a single bibliographic record."""
    try:
        record = require_record(db, record_id)

        serialized_data = encode_record_lists(update_data)

        for field, value in serialized_data.items():
            if hasattr(record, field):
                setattr(record, field, value)

        db.commit()
        db.refresh(record)

        logger.info(f"Updated bibliographic record {record_id}")
        return record
    except Exception:
        db.rollback()
        raise


def bulk_edit_records(
    db: Session,
    record_ids: List[int],
    level: Optional[str] = None,
    target_audience: Optional[str] = None,
    language: Optional[str] = None,
    medium_type: Optional[str] = None,
    publisher: Optional[str] = None,
    collection: Optional[str] = None,
    binding_type: Optional[str] = None
) -> dict:
    """Bulk edit bibliographic records."""
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
    except Exception:
        db.rollback()
        raise


def bulk_delete_records(db: Session, record_ids: List[int]) -> dict:
    """Bulk delete bibliographic records, checking for active loans first."""
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
            from src.bcd_api.models.borrower import Borrower
            from src.bcd_api.models.circulation import CirculationTransaction

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
    except Exception:
        db.rollback()
        raise


def create_item(db: Session, item_data: ItemCreate) -> Item:
    """Create a new item (physical copy) and update the notice counter."""
    try:
        from ..settings_service import get_settings
        try:
            sys_settings = get_settings(db)
            prefix = sys_settings.item_barcode_prefix
        except Exception:
            prefix = None

        item_id = normalize_item_id(item_data.item_id, prefix)

        biblio_record = (
            db.query(BiblographicRecord)
            .filter(BiblographicRecord.id == item_data.bibliographic_record_id)
            .first()
        )
        if not biblio_record:
            raise BiblographicRecordNotFoundException(item_data.bibliographic_record_id)

        validate_item_id_available(db, item_id)

        item_dict = item_data.model_dump()
        item_dict['item_id'] = item_id
        if item_dict.get('acquisition_date') is None:
            item_dict['acquisition_date'] = date.today()

        db_item = Item(**item_dict)
        db.add(db_item)
        db.flush()

        # Recalculate total_items
        refresh_total_items_in_transaction(db, {biblio_record.id})

        db.commit()
        db.refresh(db_item)

        logger.info(f"Created item {db_item.item_id} for record {biblio_record.title}")
        return db_item
    except Exception:
        db.rollback()
        raise


def update_item(db: Session, item_id: str, update_data: dict) -> Item:
    """Update a single item."""
    try:
        item = require_item(db, item_id)

        if "item_id" in update_data:
            del update_data["item_id"]

        if "acquisition_date" in update_data:
            parsed = parse_item_acquisition_date(update_data["acquisition_date"])
            if parsed:
                update_data["acquisition_date"] = parsed
            else:
                del update_data["acquisition_date"]

        for field, value in update_data.items():
            if hasattr(item, field):
                setattr(item, field, value)

        db.commit()
        db.refresh(item)

        logger.info(f"Updated item {item_id} (barcode: {item.item_id})")
        return item
    except Exception:
        db.rollback()
        raise


def _check_item_has_active_loan(db: Session, item: Item) -> Optional[dict]:
    """Check if an item is currently on loan."""
    from src.bcd_api.models.circulation import CirculationTransaction
    from ..circulation.query_filters import active_loan_predicate

    active_loan = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            active_loan_predicate()
        )
    ).first()

    if active_loan:
        return {
            "borrower_name": active_loan.borrower.full_name,
            "due_date": active_loan.due_date
        }
    return None


def delete_item(db: Session, item_id: str) -> None:
    """Delete an item by barcode and update total_items count."""
    try:
        item = require_item(db, item_id)

        active_loan_info = _check_item_has_active_loan(db, item)
        if active_loan_info:
            raise ItemHasActiveLoanException(
                item_id=item_id,
                borrower_name=active_loan_info["borrower_name"],
                due_date=active_loan_info["due_date"]
            )

        record_id = item.bibliographic_record_id
        db.delete(item)
        db.flush()

        # Recalculate total_items
        if record_id:
            refresh_total_items_in_transaction(db, {record_id})

        db.commit()
        logger.info(f"Deleted item {item_id}")
    except Exception:
        db.rollback()
        raise
