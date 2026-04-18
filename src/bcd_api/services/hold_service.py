"""
Hold Service

Business logic for managing holds/reservations (librarian-mediated).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from ..models.hold import Hold
from ..models.borrower import Borrower
from ..models.bibliographic_record import BiblographicRecord
from ..models.item import Item
from ..models.system_settings import SystemSettings
from ..core.exceptions import NotFoundError, ValidationError, ConflictError, HoldLimitExceededException
from src.shared.constants import DEFAULT_HOLD_EXPIRATION_DAYS

logger = logging.getLogger(__name__)


def create_hold(
    db: Session,
    borrower_id: int,
    bibliographic_record_id: int,
    created_by: str,
    notes: Optional[str] = None,
) -> Hold:
    """
    Place a hold/reservation for a bibliographic record.

    Args:
        db: Database session
        borrower_id: ID of borrower requesting hold
        bibliographic_record_id: ID of bibliographic record
        created_by: Username/email of librarian creating hold
        notes: Optional notes

    Returns:
        Created Hold object

    Raises:
        NotFoundError: If borrower or bibliographic record not found
        ValidationError: If borrower is blocked or record has no items
        ConflictError: If borrower already has a hold for this record
    """
    # Validate borrower exists and is active
    borrower = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not borrower:
        raise NotFoundError("Borrower", borrower_id)

    if not borrower.active:
        raise ValidationError(
            f"Borrower {borrower.borrower_id} is blocked: {borrower.blocked_reason}"
        )

    # Validate bibliographic record exists
    biblio = db.query(BiblographicRecord).filter(
        BiblographicRecord.id == bibliographic_record_id
    ).first()
    if not biblio:
        raise NotFoundError("Bibliographic record", bibliographic_record_id)

    # Check if record has any items
    item_count = db.query(Item).filter(
        Item.bibliographic_record_id == bibliographic_record_id
    ).count()
    if item_count == 0:
        raise ValidationError(f"Bibliographic record has no items to reserve")

    # Check if borrower already has a hold for this record
    existing_hold = db.query(Hold).filter(
        and_(
            Hold.borrower_id == borrower_id,
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status.in_(["waiting", "ready"])
        )
    ).first()
    if existing_hold:
        raise ConflictError(
            f"Borrower already has an active hold for this record (Hold ID: {existing_hold.id})"
        )

    # Check borrower has not exceeded max active holds
    settings = db.query(SystemSettings).first()
    max_holds = settings.max_holds_per_borrower if settings else 1
    active_hold_count = db.query(Hold).filter(
        and_(
            Hold.borrower_id == borrower_id,
            Hold.status.in_(["waiting", "ready"])
        )
    ).count()
    if active_hold_count >= max_holds:
        raise HoldLimitExceededException(current=active_hold_count, limit=max_holds)

    # Calculate queue position (next position in line)
    max_position = db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status == "waiting"
        )
    ).count()

    queue_position = max_position + 1

    # Create hold
    hold = Hold(
        borrower_id=borrower_id,
        bibliographic_record_id=bibliographic_record_id,
        hold_date=datetime.utcnow(),
        queue_position=queue_position,
        status="waiting",
        created_by=created_by,
        notes=notes,
    )

    db.add(hold)
    db.commit()
    db.refresh(hold)

    return hold


def get_hold(db: Session, hold_id: int) -> Hold:
    """Get hold by ID."""
    hold = db.query(Hold).options(
        joinedload(Hold.borrower),
        joinedload(Hold.bibliographic_record)
    ).filter(Hold.id == hold_id).first()
    if not hold:
        raise NotFoundError("Hold", hold_id)
    return hold


def get_holds_for_borrower(
    db: Session,
    borrower_id: int,
    include_fulfilled: bool = False
) -> List[Hold]:
    """
    Get all holds for a borrower.

    Args:
        db: Database session
        borrower_id: Borrower ID
        include_fulfilled: Include fulfilled/cancelled/expired holds

    Returns:
        List of Hold objects
    """
    query = db.query(Hold).options(
        joinedload(Hold.borrower),
        joinedload(Hold.bibliographic_record)
    ).filter(Hold.borrower_id == borrower_id)

    if not include_fulfilled:
        query = query.filter(Hold.status.in_(["waiting", "ready"]))

    return query.order_by(Hold.hold_date.desc()).all()


def get_holds_for_bibliographic_record(
    db: Session,
    bibliographic_record_id: int,
    active_only: bool = True
) -> List[Hold]:
    """
    Get all holds for a bibliographic record.

    Args:
        db: Database session
        bibliographic_record_id: Bibliographic record ID
        active_only: Only return waiting/ready holds

    Returns:
        List of Hold objects ordered by queue position
    """
    query = db.query(Hold).options(
        joinedload(Hold.borrower),
        joinedload(Hold.bibliographic_record)
    ).filter(
        Hold.bibliographic_record_id == bibliographic_record_id
    )

    if active_only:
        query = query.filter(Hold.status.in_(["waiting", "ready"]))

    return query.order_by(Hold.queue_position).all()


def get_ready_holds(db: Session) -> List[Hold]:
    """
    Get all holds that are ready for pickup.

    Returns:
        List of Hold objects with status='ready'
    """
    return db.query(Hold).options(
        joinedload(Hold.borrower),
        joinedload(Hold.bibliographic_record)
    ).filter(Hold.status == "ready").order_by(Hold.available_date).all()


def mark_hold_ready(
    db: Session,
    hold_id: int,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS
) -> Hold:
    """
    Mark a hold as ready for pickup (item is now available).

    Args:
        db: Database session
        hold_id: Hold ID
        expiration_days: Days until hold expires

    Returns:
        Updated Hold object

    Raises:
        NotFoundError: If hold not found
        ValidationError: If hold is not in waiting status
    """
    hold = get_hold(db, hold_id)

    if hold.status != "waiting":
        raise ValidationError(f"Hold is not in waiting status (current: {hold.status})")

    hold.status = "ready"
    hold.available_date = datetime.utcnow()
    hold.expiration_date = datetime.utcnow().date() + timedelta(days=expiration_days)

    db.commit()
    db.refresh(hold)

    return hold


def fulfill_hold(db: Session, hold_id: int) -> None:
    """
    Delete hold when item is checked out to borrower.
    No history is kept to save database space.

    Args:
        db: Database session
        hold_id: Hold ID

    Raises:
        NotFoundError: If hold not found
        ValidationError: If hold is not ready
    """
    hold = get_hold(db, hold_id)

    if hold.status != "ready":
        raise ValidationError(
            f"Hold must be ready to fulfill (current status: {hold.status})"
        )

    bibliographic_record_id = hold.bibliographic_record_id
    queue_position = hold.queue_position

    # Delete the hold instead of marking as fulfilled
    db.delete(hold)
    db.commit()

    # Reorder queue for this bibliographic record
    _reorder_queue_after_removal(db, bibliographic_record_id, queue_position)


def cancel_hold(db: Session, hold_id: int) -> None:
    """
    Delete a hold (cancellation).
    No history is kept to save database space.

    Args:
        db: Database session
        hold_id: Hold ID
    """
    hold = get_hold(db, hold_id)

    if hold.status in ["fulfilled", "cancelled", "expired"]:
        raise ValidationError(f"Hold is already {hold.status}")

    bibliographic_record_id = hold.bibliographic_record_id
    queue_position = hold.queue_position

    # Delete the hold instead of marking as cancelled
    db.delete(hold)
    db.commit()

    # Reorder queue
    _reorder_queue_after_removal(db, bibliographic_record_id, queue_position)


def _reorder_queue_after_removal(
    db: Session,
    bibliographic_record_id: int,
    removed_position: int
):
    """
    Reorder queue positions after a hold is removed/fulfilled/cancelled.

    Args:
        db: Database session
        bibliographic_record_id: Bibliographic record ID
        removed_position: Position of removed hold
    """
    # Get all waiting holds with position > removed_position
    holds_to_reorder = db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status == "waiting",
            Hold.queue_position > removed_position
        )
    ).all()

    # Decrement their positions
    for hold in holds_to_reorder:
        hold.queue_position -= 1

    db.commit()


def auto_fill_holds_on_return(
    db: Session,
    bibliographic_record_id: int,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS
) -> Optional[Hold]:
    """
    Automatically mark the next waiting hold as ready when an item is returned.

    This should be called by the circulation service when an item is returned.

    Args:
        db: Database session
        bibliographic_record_id: Bibliographic record ID of returned item
        expiration_days: Days until hold expires

    Returns:
        Hold that was marked ready, or None if no waiting holds
    """
    # Get first waiting hold (position 1)
    next_hold = db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status == "waiting",
            Hold.queue_position == 1
        )
    ).first()

    if next_hold:
        return mark_hold_ready(db, next_hold.id, expiration_days)

    return None
