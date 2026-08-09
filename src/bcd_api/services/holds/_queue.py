"""Holds Queue Management.

Private helper functions for queue ordering and progression.
"""

from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...models.hold import Hold


def next_queue_position(db: Session, bibliographic_record_id: int) -> int:
    """Calculate the next queue position (waiting count + 1) for a bibliographic record."""
    max_position = db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status == "waiting"
        )
    ).count()

    return max_position + 1


def reorder_after_removal_in_transaction(
    db: Session,
    bibliographic_record_id: int,
    removed_position: int
) -> None:
    """Reorder queue positions after a hold is removed/fulfilled/cancelled."""
    holds_to_reorder = db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status == "waiting",
            Hold.queue_position > removed_position
        )
    ).all()

    for hold in holds_to_reorder:
        hold.queue_position -= 1


def next_waiting_hold(db: Session, bibliographic_record_id: int) -> Optional[Hold]:
    """Get the next waiting hold (position 1) for a bibliographic record."""
    return db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id == bibliographic_record_id,
            Hold.status == "waiting",
            Hold.queue_position == 1
        )
    ).first()
