"""Holds Commands - Placing, updating, cancelling, and fulfilling holds.

Each public command wraps its mutations inside an atomic transaction (try-commit-rollback).
Each command delegates to an `_in_transaction` variant for parent-controlled mutations (like return or checkout).
"""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.shared.constants import DEFAULT_HOLD_EXPIRATION_DAYS

from ...core.exceptions import (
    ConflictError,
    HoldLimitExceededException,
    NotFoundError,
    ValidationError,
)
from ...models.bibliographic_record import BibliographicRecord
from ...models.borrower import Borrower
from ...models.hold import Hold
from ...models.item import Item
from ...models.system_settings import SystemSettings
from ._policy import hold_expiration_date, is_transition_allowed, is_hold_expired
from ._queue import (
    next_queue_position,
    next_waiting_hold,
    reorder_after_removal_in_transaction,
)


def _get_hold_for_mutation(db: Session, hold_id: int) -> Hold:
    """Load a hold for a command without depending on the query module."""
    hold = db.query(Hold).filter(Hold.id == hold_id).first()
    if not hold:
        raise NotFoundError("Hold", hold_id)
    return hold


def create_hold_in_transaction(
    db: Session,
    borrower_id: int,
    bibliographic_record_id: int,
    created_by: str,
    notes: Optional[str] = None,
) -> Hold:
    """Place a hold/reservation (in-transaction helper, no commit)."""
    borrower = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not borrower:
        raise NotFoundError("Borrower", borrower_id)

    if not borrower.active:
        raise ValidationError(
            f"Borrower {borrower.borrower_id} is blocked: {borrower.blocked_reason}"
        )

    biblio = db.query(BibliographicRecord).filter(
        BibliographicRecord.id == bibliographic_record_id
    ).first()
    if not biblio:
        raise NotFoundError("Bibliographic record", bibliographic_record_id)

    item_count = db.query(Item).filter(
        Item.bibliographic_record_id == bibliographic_record_id
    ).count()
    if item_count == 0:
        raise ValidationError("Bibliographic record has no items to reserve")

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

    queue_position = next_queue_position(db, bibliographic_record_id)

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
    return hold


def create_hold(
    db: Session,
    borrower_id: int,
    bibliographic_record_id: int,
    created_by: str,
    notes: Optional[str] = None,
) -> Hold:
    """Place a hold/reservation (autononous, handles commit)."""
    try:
        hold = create_hold_in_transaction(db, borrower_id, bibliographic_record_id, created_by, notes)
        db.flush()
        db.commit()
        db.refresh(hold)
        return hold
    except Exception:
        db.rollback()
        raise


def mark_hold_ready_in_transaction(
    db: Session,
    hold_id: int,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS
) -> Hold:
    """Mark a hold as ready for pickup (in-transaction helper, no commit)."""
    hold = _get_hold_for_mutation(db, hold_id)

    if not is_transition_allowed("mark_ready", hold.status):
        raise ValidationError(f"Hold is not in waiting status (current: {hold.status})")

    hold.status = "ready"
    hold.available_date = datetime.utcnow()
    hold.expiration_date = hold_expiration_date(date.today(), expiration_days)

    return hold


def mark_hold_ready(
    db: Session,
    hold_id: int,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS
) -> Hold:
    """Mark a hold as ready for pickup (autonomous, handles commit)."""
    try:
        hold = mark_hold_ready_in_transaction(db, hold_id, expiration_days)
        db.flush()
        db.commit()
        db.refresh(hold)
        return hold
    except Exception:
        db.rollback()
        raise


def fulfill_hold_in_transaction(db: Session, hold_id: int) -> None:
    """Fulfill a hold (item checked out) (in-transaction helper, no commit)."""
    hold = _get_hold_for_mutation(db, hold_id)

    if not is_transition_allowed("fulfill", hold.status):
        raise ValidationError(
            f"Hold must be ready to fulfill (current status: {hold.status})"
        )

    bibliographic_record_id = hold.bibliographic_record_id
    queue_position = hold.queue_position

    db.delete(hold)
    reorder_after_removal_in_transaction(db, bibliographic_record_id, queue_position)


def fulfill_hold(db: Session, hold_id: int) -> None:
    """Fulfill a hold (autonomous, handles commit)."""
    try:
        fulfill_hold_in_transaction(db, hold_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def cancel_hold_in_transaction(db: Session, hold_id: int) -> None:
    """Cancel a hold (in-transaction helper, no commit)."""
    hold = _get_hold_for_mutation(db, hold_id)

    if not is_transition_allowed("cancel", hold.status):
        raise ValidationError(f"Hold is already {hold.status}")

    bibliographic_record_id = hold.bibliographic_record_id
    queue_position = hold.queue_position

    db.delete(hold)
    reorder_after_removal_in_transaction(db, bibliographic_record_id, queue_position)


def cancel_hold(db: Session, hold_id: int) -> None:
    """Cancel a hold (autonomous, handles commit)."""
    try:
        cancel_hold_in_transaction(db, hold_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def expire_ready_holds_in_transaction(
    db: Session,
    today: Optional[date] = None,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS,
) -> int:
    """Delete expired ready holds and promote one next hold per affected title.

    The caller owns the transaction. Expired holds are deleted because the
    application intentionally does not retain reservation history.
    """
    today = today or date.today()
    expired_holds = db.query(Hold).filter(
        Hold.status == "ready",
        Hold.expiration_date.isnot(None),
        Hold.expiration_date < today,
    ).order_by(Hold.bibliographic_record_id, Hold.queue_position).all()

    affected_record_ids = set()
    for hold in expired_holds:
        affected_record_ids.add(hold.bibliographic_record_id)
        db.delete(hold)
        reorder_after_removal_in_transaction(
            db, hold.bibliographic_record_id, hold.queue_position
        )

    if not affected_record_ids:
        return 0

    # Make deletions and reordering visible before finding new queue heads.
    db.flush()
    for record_id in affected_record_ids:
        has_ready_hold = db.query(Hold.id).filter(
            Hold.bibliographic_record_id == record_id,
            Hold.status == "ready",
        ).first()
        if not has_ready_hold:
            auto_fill_holds_on_return_in_transaction(
                db, record_id, expiration_days
            )

    return len(expired_holds)


def expire_ready_holds(
    db: Session,
    today: Optional[date] = None,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS,
) -> int:
    """Expire ready holds as an autonomous transaction."""
    try:
        expired_count = expire_ready_holds_in_transaction(
            db, today=today, expiration_days=expiration_days
        )
        db.commit()
        return expired_count
    except Exception:
        db.rollback()
        raise


def auto_fill_holds_on_return_in_transaction(
    db: Session,
    bibliographic_record_id: int,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS
) -> Optional[Hold]:
    """Automatically mark the next waiting hold as ready (in-transaction helper, no commit)."""
    next_hold = next_waiting_hold(db, bibliographic_record_id)
    if next_hold:
        return mark_hold_ready_in_transaction(db, next_hold.id, expiration_days)
    return None


def auto_fill_holds_on_return(
    db: Session,
    bibliographic_record_id: int,
    expiration_days: int = DEFAULT_HOLD_EXPIRATION_DAYS
) -> Optional[Hold]:
    """Automatically mark the next waiting hold as ready (autonomous, handles commit)."""
    try:
        hold = auto_fill_holds_on_return_in_transaction(db, bibliographic_record_id, expiration_days)
        db.commit()
        if hold:
            db.refresh(hold)
        return hold
    except Exception:
        db.rollback()
        raise


def cancel_holds_for_records_in_transaction(
    db: Session,
    record_ids: set[int],
) -> int:
    """Cancel and delete active holds on bibliographic records (in-transaction helper, no commit)."""
    if not record_ids:
        return 0
    holds_query = db.query(Hold).filter(
        Hold.bibliographic_record_id.in_(list(record_ids))
    )
    holds_cancelled = holds_query.count()
    holds_query.delete(synchronize_session=False)
    return holds_cancelled