"""Projections module for catalog stats, counters, and availability projections."""

import logging
from typing import Set, List
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.hold import Hold
from src.shared.constants import ItemStatus
from ._serialization import decode_list

logger = logging.getLogger(__name__)


def refresh_total_items_in_transaction(db: Session, record_ids: Set[int]) -> None:
    """Recalculate total_items count for the given bibliographic record IDs."""
    if not record_ids:
        return

    # Query the actual count of items for each record ID
    counts = (
        db.query(Item.bibliographic_record_id, func.count(Item.id))
        .filter(Item.bibliographic_record_id.in_(record_ids))
        .group_by(Item.bibliographic_record_id)
        .all()
    )
    counts_map = {rid: cnt for rid, cnt in counts}

    # Update records
    records = db.query(BiblographicRecord).filter(BiblographicRecord.id.in_(record_ids)).all()
    for record in records:
        record.total_items = counts_map.get(record.id, 0)

    # Any record_id without items should be set to 0
    for rid in record_ids:
        if rid not in counts_map:
            record = db.query(BiblographicRecord).filter(BiblographicRecord.id == rid).first()
            if record:
                record.total_items = 0


def availability_by_record(db: Session, records: List[BiblographicRecord]) -> List[dict]:
    """
    Enrich bibliographic records with availability, copy counts, and first item information.
    Batch queries are used to avoid N+1 queries.
    """
    if not records:
        return []

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
    first_item_by_record = {}
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
        authors = decode_list(r.authors)

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
