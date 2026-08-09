"""Command services for inventory, including scans, edits, and deletions."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from src.shared.constants import ItemStatus
from ...core.exceptions import ItemNotFoundException
from ...models.bibliographic_record import BibliographicRecord
from ...models.circulation import CirculationTransaction
from ...models.item import Item
from ._validation import normalize_field_value
from ._policy import item_update_decision, can_deaccession
from ..circulation.queries import get_active_loans_for_items
from ..hold_service import cancel_holds_for_records_in_transaction
from ..catalog_service import bulk_delete_records

logger = logging.getLogger(__name__)


def mark_item_inventoried(db: Session, item_id: str) -> Item:
    """
    Mark a single item as inventoried (barcode scan).

    Updates `last_inventoried_at` to current UTC timestamp.
    """
    try:
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
        db.flush()
        db.commit()
        db.refresh(item)

        logger.info(f"Marked item {item_id} as inventoried at {item.last_inventoried_at}")
        return item
    except Exception:
        db.rollback()
        raise


def bulk_mark_inventoried(db: Session, item_ids: list[str]) -> dict:
    """
    Mark multiple items as inventoried (file import, search add).

    Updates `last_inventoried_at` to current UTC timestamp for all items in list.
    """
    try:
        timestamp = datetime.now(timezone.utc)

        # Query all items matching the provided item_ids
        items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()

        # Track which items were found
        found_item_ids = {item.item_id for item in items}
        not_found = [item_id for item_id in item_ids if item_id not in found_item_ids]

        # Update all found items
        for item in items:
            item.last_inventoried_at = timestamp

        db.flush()
        db.commit()

        logger.info(f"Bulk marked {len(items)} items as inventoried, {len(not_found)} not found")

        return {
            "items_updated": len(items),
            "items_not_found": not_found,
            "timestamp": timestamp
        }
    except Exception:
        db.rollback()
        raise


def bulk_update_items(
    db: Session,
    item_ids: list[str],
    item_updates: Optional[dict] = None,
    record_updates: Optional[dict] = None
) -> dict:
    """
    Apply same changes to multiple items + their parent records (bulk edit).
    """
    try:
        # Fetch all items by item_id
        items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()

        items_updated = 0
        items_skipped_on_loan = 0

        # Get all active loans for the retrieved items to determine has_active_loan
        active_loans = get_active_loans_for_items(db, [item.id for item in items])
        active_loan_item_ids = {loan.item_id for loan in active_loans}

        # Apply item-level updates
        if item_updates:
            for item in items:
                has_active_loan = item.id in active_loan_item_ids
                decision = item_update_decision(
                    has_active_loan=has_active_loan,
                    requested_updates=item_updates,
                )
                
                # Apply accepted updates
                for key, value in decision.accepted_updates.items():
                    if value is not None:
                        setattr(item, key, normalize_field_value(value))
                
                if "status" in decision.ignored_fields:
                    items_skipped_on_loan += 1
                
                items_updated += 1

        # Deduplicate records from the selected items
        record_ids = {item.bibliographic_record_id for item in items}
        records = db.query(BibliographicRecord).filter(BibliographicRecord.id.in_(record_ids)).all()

        records_updated = 0
        other_copies_affected = 0

        # Apply record-level updates
        if record_updates:
            for record in records:
                for key, value in record_updates.items():
                    if value is not None:
                        setattr(record, key, normalize_field_value(value))
                records_updated += 1

                # Count other copies affected (items with this record but not in our selection)
                other_copies_affected += record.total_items - sum(1 for item in items if item.bibliographic_record_id == record.id)

        db.flush()
        db.commit()

        logger.info(f"Bulk updated {items_updated} items ({items_skipped_on_loan} skipped on_loan), {records_updated} records, {other_copies_affected} other copies affected")

        return {
            "items_updated": items_updated,
            "items_skipped_on_loan": items_skipped_on_loan,
            "records_updated": records_updated,
            "other_copies_affected": other_copies_affected
        }
    except Exception:
        db.rollback()
        raise


def delete_items_bulk(db: Session, item_ids: list[str]) -> dict:
    """
    Permanently delete items from system (on_loan items and items with active loans excluded, holds cancelled).
    """
    try:
        # Fetch all items by item_id
        items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()

        # Find active loans where return_date IS NULL for safety
        active_loan_item_ids = set()
        if items:
            active_loans = db.query(CirculationTransaction.item_id).filter(
                CirculationTransaction.item_id.in_([item.id for item in items]),
                CirculationTransaction.return_date.is_(None)
            ).all()
            active_loan_item_ids = {loan[0] for loan in active_loans}

        # Separate deletable from on_loan (based on active loan)
        deletable_items = [
            item for item in items
            if can_deaccession(has_active_loan=item.id in active_loan_item_ids)
        ]
        on_loan_items = [
            item for item in items
            if not can_deaccession(has_active_loan=item.id in active_loan_item_ids)
        ]

        # Get unique record IDs for hold cancellation
        deletable_record_ids = {item.bibliographic_record_id for item in deletable_items}

        # Cancel holds on bibliographic records of deletable items (FR-034)
        holds_cancelled = cancel_holds_for_records_in_transaction(db, deletable_record_ids)

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
            record = db.query(BibliographicRecord).filter(BibliographicRecord.id == record_id).first()
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
    except Exception:
        db.rollback()
        raise


def delete_orphan_records(db: Session) -> dict:
    """
    Remove all bibliographic records with no remaining items (using real relationship check).
    """
    try:
        # Get orphan record IDs
        orphan_ids = [
            record.id
            for record in db.query(BibliographicRecord).filter(
                ~db.query(Item).filter(Item.bibliographic_record_id == BibliographicRecord.id).exists()
            ).all()
        ]

        # Use existing bulk_delete_records function
        if orphan_ids:
            bulk_delete_records(db, orphan_ids)

        db.commit()
        logger.info(f"Deleted {len(orphan_ids)} orphan records")

        return {
            "records_deleted": len(orphan_ids)
        }
    except Exception:
        db.rollback()
        raise
