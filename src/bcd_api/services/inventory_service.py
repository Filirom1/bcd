"""Inventory Service

Business logic for collection inventory operations (récolement/weeding).
All functions in this module operate on items and bibliographic records
for physical inventory tracking and bulk operations.
"""

import csv
import logging
from datetime import date, datetime, timezone
from io import StringIO
from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from ...shared.constants import ItemStatus
from ..core.exceptions import ItemNotFoundException
from ..models.bibliographic_record import BiblographicRecord
from ..models.circulation import CirculationTransaction
from ..models.hold import Hold
from ..models.item import Item
from ..models.system_settings import SystemSettings

logger = logging.getLogger(__name__)


def _escape_like_pattern(pattern: str) -> str:
    """Escape special characters in LIKE pattern to prevent wildcard injection.

    Escapes % and _ characters so they are treated as literals, not wildcards.

    Args:
        pattern: User input to use in LIKE clause

    Returns:
        Escaped pattern safe for LIKE query
    """
    if not pattern:
        return pattern
    # Escape backslash first, then % and _
    return pattern.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')


# ==================== User Story 1: Barcode Scanning ====================


def mark_item_inventoried(db: Session, item_id: str) -> Item:
    """
    Mark a single item as inventoried (barcode scan).

    Updates `last_inventoried_at` to current UTC timestamp.

    Args:
        db: Database session
        item_id: Item barcode (inventory number)

    Returns:
        Updated Item with joined bibliographic_record for title

    Raises:
        ItemNotFoundException: If item_id not found
    """
    item = (
        db.query(Item)
        .options(joinedload(Item.bibliographic_record))
        .filter(Item.item_id == item_id)
        .first()
    )

    if not item:
        raise ItemNotFoundException(item_id)

    # Update inventory timestamp
    item.last_inventoried_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)

    logger.info(f"Marked item {item_id} as inventoried at {item.last_inventoried_at}")

    return item


# ==================== User Story 2: Search-Based Item Discovery ====================


def bulk_mark_inventoried(db: Session, item_ids: list[str]) -> dict:
    """
    Mark multiple items as inventoried (file import, search add).

    Updates `last_inventoried_at` to current UTC timestamp for all items in list.

    Args:
        db: Database session
        item_ids: List of item barcodes (inventory numbers)

    Returns:
        dict with:
            - items_updated (int): Number of items successfully updated
            - items_not_found (list[str]): Barcodes not found in database
            - timestamp (datetime): Timestamp when items were marked
    """
    timestamp = datetime.now(timezone.utc)

    # Query all items matching the provided item_ids
    items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()

    # Track which items were found
    found_item_ids = {item.item_id for item in items}
    not_found = [item_id for item_id in item_ids if item_id not in found_item_ids]

    # Update all found items
    for item in items:
        item.last_inventoried_at = timestamp

    db.commit()

    logger.info(f"Bulk marked {len(items)} items as inventoried, {len(not_found)} not found")

    return {
        "items_updated": len(items),
        "items_not_found": not_found,
        "timestamp": timestamp
    }


def search_items(
    db: Session,
    q: Optional[str] = None,
    status: Optional[str] = None,
    condition: Optional[str] = None,
    shelf_location: Optional[str] = None,
    never_inventoried: Optional[bool] = None,
    inventoried_before: Optional[date] = None,
    acquired_before: Optional[date] = None,
    acquired_after: Optional[date] = None,
    medium_type: Optional[str] = None,
    target_audience: Optional[str] = None,
    level: Optional[str] = None,
    language: Optional[str] = None,
    publication_year_min: Optional[int] = None,
    publication_year_max: Optional[int] = None,
    max_borrows: Optional[int] = None,
    since_date: Optional[date] = None,
    never_borrowed: Optional[bool] = None,
    no_limit: bool = False
) -> dict:
    """
    Search items matching inventory criteria (rotation, last inventoried, condition, etc.).

    Args:
        db: Database session
        q: Free text search (title, author, ISBN, call number)
        status: Item status filter
        condition: Item condition filter
        shelf_location: Partial match on location
        never_inventoried: Only items with NULL last_inventoried_at
        inventoried_before: Items not inventoried since this date
        acquired_before: Items acquired before this date (for age in collection filtering)
        acquired_after: Items acquired after or on this date
        medium_type: Bibliographic medium type
        target_audience: child, youth, adult
        level: Partial match on reading level
        publication_year_min: Min publication year
        publication_year_max: Max publication year
        max_borrows: Max loans in period (rotation filter)
        since_date: Start date for rotation filter
        no_limit: Skip result limit (default False, returns all results)

    Returns:
        dict with:
            - items (list): Search results (max 200 unless no_limit=True)
            - total_count (int): Total matching items before limit
            - displayed_count (int): Number of items in results
            - capped (bool): True if results were capped
            - archive_cutoff_date (datetime|None): Oldest transaction date
    """
    # Start with base query joining bibliographic_record with all needed fields
    query = db.query(
        Item,
        BiblographicRecord.title,
        BiblographicRecord.authors,
        BiblographicRecord.level,
        BiblographicRecord.target_audience,
        BiblographicRecord.language,
        BiblographicRecord.medium_type,
        BiblographicRecord.publication_year
    ).join(BiblographicRecord)

    # Always add subquery for all-time circulation count per item
    circ_subquery = (
        db.query(
            CirculationTransaction.item_id,
            func.count().label('circ_count')
        )
        .group_by(CirculationTransaction.item_id)
        .subquery()
    )
    query = query.outerjoin(circ_subquery, circ_subquery.c.item_id == Item.id)
    query = query.add_columns(func.coalesce(circ_subquery.c.circ_count, 0).label('circulation_count'))

    # If rotation filter is active, add LEFT JOIN subquery for loan counts
    period_loan_count_column = None
    if max_borrows is not None and since_date is not None:
        # Subquery: count loans in period per item
        loan_subquery = (
            db.query(
                CirculationTransaction.item_id,
                func.count().label('period_count')
            )
            .filter(CirculationTransaction.checkout_date >= since_date)
            .group_by(CirculationTransaction.item_id)
            .subquery()
        )

        # Add LEFT JOIN to main query
        query = query.outerjoin(loan_subquery, loan_subquery.c.item_id == Item.id)
        period_loan_count_column = func.coalesce(loan_subquery.c.period_count, 0).label('period_loan_count')
        query = query.add_columns(period_loan_count_column)

        # Apply rotation filter
        query = query.filter(func.coalesce(loan_subquery.c.period_count, 0) <= max_borrows)

    # Apply text search filter (q)
    if q:
        q_safe = _escape_like_pattern(q)
        query = query.filter(
            or_(
                BiblographicRecord.title.ilike(f'%{q_safe}%', escape='\\'),
                BiblographicRecord.authors.ilike(f'%{q_safe}%', escape='\\'),
                BiblographicRecord.isbn.ilike(f'%{q_safe}%', escape='\\'),
                Item.call_number.ilike(f'%{q_safe}%', escape='\\')
            )
        )

    # Apply item-level filters
    if status:
        query = query.filter(Item.status == status)
    if condition:
        query = query.filter(Item.condition == condition)
    if shelf_location == "__none__":
        query = query.filter(
            or_(Item.shelf_location.is_(None), Item.shelf_location == "")
        )
    elif shelf_location:
        shelf_safe = _escape_like_pattern(shelf_location)
        query = query.filter(Item.shelf_location.ilike(f'%{shelf_safe}%', escape='\\'))

    # Apply inventory filters
    if never_inventoried:
        query = query.filter(Item.last_inventoried_at.is_(None))
    if inventoried_before:
        query = query.filter(
            or_(
                Item.last_inventoried_at.is_(None),
                Item.last_inventoried_at < inventoried_before
            )
        )

    # Apply acquisition date filter (for age in collection)
    if acquired_before:
        query = query.filter(
            and_(
                Item.acquisition_date.is_not(None),  # Only items WITH acquisition date
                Item.acquisition_date < acquired_before
            )
        )

    if acquired_after:
        query = query.filter(
            and_(
                Item.acquisition_date.is_not(None),
                Item.acquisition_date >= acquired_after
            )
        )

    # Apply record-level filters
    if medium_type == "__none__":
        query = query.filter(BiblographicRecord.medium_type.is_(None))
    elif medium_type:
        query = query.filter(BiblographicRecord.medium_type == medium_type)
    if target_audience == "__none__":
        query = query.filter(BiblographicRecord.target_audience.is_(None))
    elif target_audience:
        query = query.filter(BiblographicRecord.target_audience == target_audience)
    if level == "__none__":
        query = query.filter(BiblographicRecord.level.is_(None))
    elif level:
        level_safe = _escape_like_pattern(level)
        query = query.filter(BiblographicRecord.level.ilike(f'%{level_safe}%', escape='\\'))
    if language == "__none__":
        query = query.filter(BiblographicRecord.language.is_(None))
    elif language:
        query = query.filter(BiblographicRecord.language == language)

    # Apply publication year range
    if publication_year_min is not None:
        query = query.filter(BiblographicRecord.publication_year >= publication_year_min)
    if publication_year_max is not None:
        query = query.filter(BiblographicRecord.publication_year <= publication_year_max)

    # Filter items never borrowed (last_borrowed_at IS NULL)
    if never_borrowed:
        query = query.filter(Item.last_borrowed_at.is_(None))

    # Get total count before limit
    total_count = query.count()

    # Apply limit (read from settings) unless no_limit is True
    capped = False
    if not no_limit:
        settings = db.query(SystemSettings).first()
        result_limit = settings.inventory_search_result_limit if settings else 200
        if total_count > result_limit:
            capped = True
        query = query.limit(result_limit)

    # Execute query
    results = query.all()

    # Build response items
    items = []
    for result in results:
        item = result[0]  # Item object
        title = result[1]  # title from BiblographicRecord
        authors = result[2]  # authors JSON string from BiblographicRecord
        level = result[3]  # level from BiblographicRecord
        target_audience = result[4]  # target_audience from BiblographicRecord
        language = result[5]  # language from BiblographicRecord
        medium_type = result[6]  # medium_type from BiblographicRecord
        publication_year = result[7]  # publication_year from BiblographicRecord
        circulation_count = result[8]  # all-time loan count (always present)

        # Parse authors JSON
        try:
            import json
            authors_list = json.loads(authors) if authors else None
        except:
            authors_list = None

        # Calculate age in days if acquisition_date exists
        age_days = None
        if item.acquisition_date:
            today = datetime.now(timezone.utc).date()
            age_days = (today - item.acquisition_date).days

        item_dict = {
            # Item fields
            "item_id": item.item_id,
            "bibliographic_record_id": item.bibliographic_record_id,
            "status": item.status,
            "condition": item.condition,
            "loanable": item.loanable,
            "shelf_location": item.shelf_location,
            "acquisition_date": item.acquisition_date,
            "last_borrowed_at": item.last_borrowed_at,
            "last_inventoried_at": item.last_inventoried_at,
            # Record fields (for display in working table)
            "title": title,
            "authors": authors_list,
            "call_number": item.call_number,
            "level": level,
            "target_audience": target_audience,
            "language": language,
            "medium_type": medium_type,
            "publication_year": publication_year,
            # Calculated fields
            "age_days": age_days,
            "circulation_count": circulation_count,
        }

        # Add period_loan_count if rotation filter was active
        if period_loan_count_column is not None and len(result) > 9:
            item_dict["period_loan_count"] = result[9]  # period_loan_count from subquery

        items.append(item_dict)

    # Compute archive cutoff date
    archive_cutoff = db.query(func.min(CirculationTransaction.checkout_date)).scalar()

    logger.info(f"Search found {total_count} items, returning {len(items)} (capped={capped})")

    return {
        "items": items,
        "total_count": total_count,
        "displayed_count": len(items),
        "capped": capped,
        "archive_cutoff_date": archive_cutoff
    }


# ==================== User Story 3: Bulk Edit of Items and Records ====================


def bulk_update_items(
    db: Session,
    item_ids: list[str],
    item_updates: Optional[dict] = None,
    record_updates: Optional[dict] = None
) -> dict:
    """
    Apply same changes to multiple items + their parent records (bulk edit).

    Args:
        db: Database session
        item_ids: List of item barcodes to update
        item_updates: Optional dict with item field updates (status, condition, loanable, shelf_location)
        record_updates: Optional dict with record field updates (level, target_audience, language, medium_type)

    Returns:
        dict with:
            - items_updated (int): Number of items successfully updated
            - items_skipped_on_loan (int): Items with status='on_loan' excluded from status changes
            - records_updated (int): Number of unique bibliographic records updated
            - other_copies_affected (int): Copies of same titles NOT in item_ids but affected by record updates
    """
    # Fetch all items by item_id
    items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()

    items_updated = 0
    items_skipped_on_loan = 0

    # Apply item-level updates
    if item_updates:
        for item in items:
            # Skip status changes for on_loan items (FR-029)
            if "status" in item_updates and item.status == ItemStatus.ON_LOAN.value:
                items_skipped_on_loan += 1
                # Apply other updates but not status
                for key, value in item_updates.items():
                    if key != "status" and value is not None:
                        setattr(item, key, None if value == "" else value)
            else:
                # Apply all updates
                for key, value in item_updates.items():
                    if value is not None:
                        setattr(item, key, None if value == "" else value)
            items_updated += 1

    # Deduplicate records from the selected items
    record_ids = {item.bibliographic_record_id for item in items}
    records = db.query(BiblographicRecord).filter(BiblographicRecord.id.in_(record_ids)).all()

    records_updated = 0
    other_copies_affected = 0

    # Apply record-level updates
    if record_updates:
        for record in records:
            for key, value in record_updates.items():
                if value is not None:
                    setattr(record, key, None if value == "" else value)
            records_updated += 1

            # Count other copies affected (items with this record but not in our selection)
            other_copies_affected += record.total_items - sum(1 for item in items if item.bibliographic_record_id == record.id)

    db.commit()

    logger.info(f"Bulk updated {items_updated} items ({items_skipped_on_loan} skipped on_loan), {records_updated} records, {other_copies_affected} other copies affected")

    return {
        "items_updated": items_updated,
        "items_skipped_on_loan": items_skipped_on_loan,
        "records_updated": records_updated,
        "other_copies_affected": other_copies_affected
    }


# ==================== User Story 5: Bulk Deaccessioning and Deletion ====================


def delete_items_bulk(db: Session, item_ids: list[str]) -> dict:
    """
    Permanently delete items from system (on_loan items excluded, holds cancelled).

    Args:
        db: Database session
        item_ids: List of item barcodes to delete

    Returns:
        dict with:
            - items_deleted (int): Number of items successfully deleted
            - items_skipped_on_loan (int): Items with status='on_loan' excluded from deletion
            - holds_cancelled (int): Active holds cancelled
            - orphan_records_created (int): Records where total_items became 0
    """
    # Fetch all items by item_id
    items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()

    # Separate deletable (not on_loan) from on_loan
    deletable_items = [item for item in items if item.status != ItemStatus.ON_LOAN.value]
    on_loan_items = [item for item in items if item.status == ItemStatus.ON_LOAN.value]

    # Get unique record IDs for hold cancellation
    deletable_record_ids = {item.bibliographic_record_id for item in deletable_items}

    # Cancel holds on bibliographic records of deletable items (FR-034)
    # Note: Holds are placed on records, not individual items
    holds_query = db.query(Hold).filter(Hold.bibliographic_record_id.in_(deletable_record_ids))
    holds_cancelled = holds_query.count()
    holds_query.delete(synchronize_session=False)

    # Track parent records before deletion
    record_ids = {item.bibliographic_record_id for item in deletable_items}

    # Delete deletable items
    for item in deletable_items:
        db.delete(item)

    # Flush deletes to database so count queries below see the updated state (important when autoflush=False)
    db.flush()

    # Update parent record counters
    orphan_records_created = 0
    for record_id in record_ids:
        record = db.query(BiblographicRecord).filter(BiblographicRecord.id == record_id).first()
        if record:
            # Recount items for this record
            item_count = db.query(Item).filter(Item.bibliographic_record_id == record_id).count()
            record.total_items = item_count

            if item_count == 0:
                orphan_records_created += 1

    db.commit()

    logger.info(f"Deleted {len(deletable_items)} items ({len(on_loan_items)} skipped on_loan), cancelled {holds_cancelled} holds, created {orphan_records_created} orphans")

    return {
        "items_deleted": len(deletable_items),
        "items_skipped_on_loan": len(on_loan_items),
        "holds_cancelled": holds_cancelled,
        "orphan_records_created": orphan_records_created
    }


# ==================== User Story 6: Working Table Management and Export ====================


def get_items_csv(db: Session, item_ids: list[str]) -> str:
    """
    Generate CSV export of items in working table.

    Args:
        db: Database session
        item_ids: List of item barcodes to export

    Returns:
        str: CSV string with 9 columns
    """

    # Fetch items with joined bibliographic_record
    items = (
        db.query(Item)
        .options(joinedload(Item.bibliographic_record))
        .filter(Item.item_id.in_(item_ids))
        .all()
    )

    # Build CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write header (FR-036 columns)
    writer.writerow([
        'barcode',
        'title',
        'author',
        'call_number',
        'location',
        'status',
        'condition',
        'last_loan_date',
        'last_inventory_date'
    ])

    # Write rows
    for item in items:
        record = item.bibliographic_record

        # Parse first author
        try:
            import json
            authors = json.loads(record.authors) if record.authors else []
            first_author = authors[0] if authors else ""
        except:
            first_author = ""

        # Format dates
        last_loan_date = item.last_borrowed_at.date().isoformat() if item.last_borrowed_at else ""
        last_inventory_date = item.last_inventoried_at.date().isoformat() if item.last_inventoried_at else ""

        writer.writerow([
            f".{item.item_id}",  # Barcode with prefix
            record.title,
            first_author,
            item.call_number or "",
            item.shelf_location or "",
            item.status,
            item.condition,
            last_loan_date,
            last_inventory_date
        ])

    return output.getvalue()


# ==================== User Story 7: Orphan Record Cleanup ====================


def get_orphan_records(db: Session) -> dict:
    """
    Get bibliographic records with no remaining items (total_items = 0).

    Args:
        db: Database session

    Returns:
        dict with:
            - count (int): Number of orphan records
            - records (list): Orphan record details (id, title, isbn)
    """
    orphans = db.query(BiblographicRecord).filter(BiblographicRecord.total_items == 0).all()

    records = [
        {
            "id": record.id,
            "title": record.title,
            "isbn": record.isbn
        }
        for record in orphans
    ]

    logger.info(f"Found {len(records)} orphan records")

    return {
        "count": len(records),
        "records": records
    }


def delete_orphan_records(db: Session) -> dict:
    """
    Remove all bibliographic records with total_items = 0.

    Args:
        db: Database session

    Returns:
        dict with:
            - records_deleted (int): Number of records deleted
    """
    # Get orphan record IDs
    orphan_ids = [
        record.id
        for record in db.query(BiblographicRecord).filter(BiblographicRecord.total_items == 0).all()
    ]

    # Import catalog_service here to avoid circular import
    from . import catalog_service

    # Use existing bulk_delete_records function
    if orphan_ids:
        catalog_service.bulk_delete_records(db, orphan_ids)

    logger.info(f"Deleted {len(orphan_ids)} orphan records")

    return {
        "records_deleted": len(orphan_ids)
    }
