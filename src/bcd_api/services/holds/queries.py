"""Holds Queries - Read-only queries for holds.

No mutations, commits, or rollbacks.
"""

from typing import List

from sqlalchemy.orm import Session, joinedload

from ...core.exceptions import NotFoundError
from ...models.hold import Hold


def get_hold(db: Session, hold_id: int) -> Hold:
    """Get hold by ID with eager loading."""
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
    """Get all holds for a borrower."""
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
    """Get all holds for a bibliographic record."""
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
    """Get all holds that are ready for pickup."""
    return db.query(Hold).options(
        joinedload(Hold.borrower),
        joinedload(Hold.bibliographic_record)
    ).filter(Hold.status == "ready").order_by(Hold.available_date).all()
