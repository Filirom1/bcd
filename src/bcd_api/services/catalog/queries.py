"""Queries module for the catalog domain."""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, case
from sqlalchemy.orm import Session, joinedload

from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.hold import Hold
from src.shared.constants import IDFormat
from ._validation import require_record, require_item

logger = logging.getLogger(__name__)


def get_bibliographic_record(db: Session, record_id: int) -> BiblographicRecord:
    """Retrieve bibliographic record by ID."""
    return require_record(db, record_id)


def get_bibliographic_record_with_counts(db: Session, record_id: int) -> BiblographicRecord:
    """Retrieve bibliographic record by ID and compute the real total_items."""
    record = require_record(db, record_id)
    record.total_items = db.query(Item).filter(Item.bibliographic_record_id == record_id).count()
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
) -> Tuple[List[BiblographicRecord], int]:
    """Search bibliographic records with filters."""
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


def get_item(db: Session, item_id: str) -> Item:
    """Retrieve single item by ID."""
    return require_item(db, item_id)


def get_items_for_bibliographic_record(
    db: Session, bibliographic_record_id: int
) -> list[dict]:
    """Get all items for a bibliographic record with optimized circulation details."""
    items = (
        db.query(Item)
        .filter(Item.bibliographic_record_id == bibliographic_record_id)
        .all()
    )

    item_ids = [item.id for item in items]
    active_loans_map = {}

    if item_ids:
        from ...models.circulation import CirculationTransaction
        from ..circulation.query_filters import active_loan_predicate

        active_loans = (
            db.query(CirculationTransaction)
            .filter(
                and_(
                    CirculationTransaction.item_id.in_(item_ids),
                    active_loan_predicate()
                )
            )
            .options(joinedload(CirculationTransaction.borrower))
            .all()
        )
        active_loans_map = {loan.item_id: loan for loan in active_loans}

    result = []
    for item in items:
        item_dict = {
            "id": item.id,
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

        if item.status == "on_loan" and item.id in active_loans_map:
            from ..circulation import policy as circ_policy
            active_loan = active_loans_map[item.id]
            is_overdue_val = circ_policy.is_overdue(active_loan.due_date, date.today())
            days_overdue_val = circ_policy.overdue_days(active_loan.due_date, date.today())
            item_dict["current_loan"] = {
                "borrower_id": active_loan.borrower.borrower_id,
                "borrower_name": active_loan.borrower.full_name,
                "due_date": active_loan.due_date.strftime('%d/%m/%Y'),
                "is_overdue": is_overdue_val,
                "days_overdue": days_overdue_val
            }

        result.append(item_dict)

    return result


def get_available_item_ids(
    db: Session,
    count: int = 30,
    start_from: Optional[str] = None,
    contiguous: bool = True
) -> Dict[str, Any]:
    """Generate available sequential/isolated item IDs that are not in use."""
    from ..settings_service import get_settings

    settings = get_settings(db)

    if count < 1 or count > 1000:
        raise ValueError("Count must be between 1 and 1000")

    if settings.id_format == IDFormat.NUMERIC.value:
        rows = db.query(Item.item_id).all()
        used_ids = set()
        for (iid,) in rows:
            try:
                n = int(iid)
                if n > 0:
                    used_ids.add(n)
            except (ValueError, TypeError):
                pass

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
            while len(ids) < count:
                all_free = True
                for offset in range(count - len(ids)):
                    if (candidate + offset) in used_ids:
                        all_free = False
                        candidate = candidate + offset + 1
                        break

                if all_free:
                    for offset in range(count - len(ids)):
                        ids.append(str(candidate + offset))
                    break
        else:
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

    else:
        raise NotImplementedError(
            "Alphanumeric ID generation not yet implemented. "
            "Please set id_format to 'numeric' in system settings."
        )


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
