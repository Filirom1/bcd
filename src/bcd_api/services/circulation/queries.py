"""Circulation Queries - Read-only queries for active loans and histories.

Strictly read-only operations with no mutations, commits, or rollbacks.
"""

import math
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from ...core.exceptions import ItemNotFoundException, NotFoundException
from ...models.borrower import Borrower
from ...models.circulation import CirculationTransaction
from ...models.hold import Hold
from ...models.item import Item
from ...utils.serialization import deserialize_json_list
from ...schemas.circulation import (
    BorrowerHistoryItem,
    BorrowerHistoryResponse,
    ItemHistoryItem,
    ItemHistoryResponse,
    PaginationMeta,
)
from ._presentation import display_title
from .policy import is_overdue, overdue_days, was_returned_late
from .query_filters import active_loan_predicate


def get_active_loan_for_item(db: Session, item_db_id: int) -> Optional[CirculationTransaction]:
    """Get the active loan (if any) for an item by its primary key ID."""
    return db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item_db_id,
            active_loan_predicate()
        )
    ).first()


def get_active_loans_for_items(db: Session, item_db_ids: List[int]) -> List[CirculationTransaction]:
    """Get all active loans for a list of item primary key IDs."""
    return db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id.in_(item_db_ids),
            active_loan_predicate()
        )
    ).all()


def count_active_loans_for_borrower(db: Session, borrower_db_id: int) -> int:
    """Count the number of active loans for a borrower by their primary key ID."""
    return db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_db_id,
            active_loan_predicate()
        )
    ).count()


def get_borrower_current_loans(db: Session, borrower_id: str) -> List[dict]:
    """Get all currently active loans for a borrower by their borrower_id string."""
    from ...core.deps import get_settings

    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise NotFoundException("Borrower", borrower_id)

    transactions = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower.id,
            active_loan_predicate()
        )
    ).options(
        joinedload(CirculationTransaction.item),
        joinedload(CirculationTransaction.bibliographic_record)
    ).order_by(CirculationTransaction.due_date).all()

    settings = get_settings(db)
    record_ids = {t.bibliographic_record_id for t in transactions}
    active_hold_record_ids = set()
    if record_ids:
        active_hold_record_ids = {
            record_id
            for (record_id,) in db.query(Hold.bibliographic_record_id).filter(
                Hold.bibliographic_record_id.in_(record_ids),
                Hold.status.in_(["waiting", "ready"]),
            ).distinct().all()
        }

    return [
        {
            "transaction_id": t.id,
            "item_id": t.item.item_id,
            "bibliographic_record_id": t.bibliographic_record.id,
            "title": t.bibliographic_record.title,
            "call_number": t.item.call_number,
            "shelf_location": t.item.shelf_location,
            "display_title": display_title(t.bibliographic_record.title),
            "authors": deserialize_json_list(t.bibliographic_record.authors),
            "checkout_date": t.checkout_date,
            "due_date": t.due_date,
            "days_until_due": (t.due_date - date.today()).days,
            "is_overdue": is_overdue(t.due_date, date.today()),
            "days_overdue": overdue_days(t.due_date, date.today()),
            "renewal_count": t.renewal_count,
            "can_renew": (
                t.renewal_count < settings.renewal_limit
                and t.bibliographic_record_id not in active_hold_record_ids
            ),
            "cover_image": t.bibliographic_record.cover_image,
        }
        for t in transactions
    ]


def get_item_circulation_history(
    db: Session,
    item_id: str,
    page: int = 1,
    page_size: int = 20,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ItemHistoryResponse:
    """Get paginated circulation history for an item."""
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise ItemNotFoundException(item_id)

    # Fetch current active loan separately
    current_transaction = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            active_loan_predicate()
        )
    ).options(joinedload(CirculationTransaction.borrower)).first()

    current_loan = None
    if current_transaction:
        is_overdue_val = is_overdue(current_transaction.due_date, date.today())
        current_loan = ItemHistoryItem(
            borrower_id=current_transaction.borrower.borrower_id,
            borrower_name=current_transaction.borrower.full_name,
            checkout_date=current_transaction.checkout_date,
            due_date=current_transaction.due_date,
            return_date=None,
            was_overdue=is_overdue_val,
            status="overdue" if is_overdue_val else "on_loan",
        )

    # Build base query for completed transactions
    base_query = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            CirculationTransaction.return_date.isnot(None)
        )
    )

    # Apply date filters
    if date_from is not None:
        base_query = base_query.filter(
            CirculationTransaction.checkout_date >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to is not None:
        base_query = base_query.filter(
            CirculationTransaction.checkout_date <= datetime.combine(date_to, datetime.max.time())
        )

    total_items = base_query.count()
    total_pages = max(1, math.ceil(total_items / page_size))

    history_transactions = base_query.options(
        joinedload(CirculationTransaction.borrower)
    ).order_by(
        CirculationTransaction.checkout_date.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    history = []
    for t in history_transactions:
        was_overdue_val = bool(
            t.return_date and was_returned_late(t.due_date, t.return_date)
        )
        history.append(ItemHistoryItem(
            borrower_id=t.borrower.borrower_id,
            borrower_name=t.borrower.full_name,
            checkout_date=t.checkout_date,
            due_date=t.due_date,
            return_date=t.return_date,
            was_overdue=was_overdue_val,
            status="returned_late" if was_overdue_val else "returned_on_time",
        ))

    return ItemHistoryResponse(
        item_id=item_id,
        title=item.bibliographic_record.title if item.bibliographic_record else "",
        current_loan=current_loan,
        history=history,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


def get_borrower_circulation_history(
    db: Session,
    borrower_id: str,
    page: int = 1,
    page_size: int = 20,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> BorrowerHistoryResponse:
    """Get paginated circulation history for a borrower (completed transactions only)."""
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise NotFoundException("Borrower", borrower_id)

    # Build base query: completed transactions only
    base_query = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower.id,
            CirculationTransaction.return_date.isnot(None)
        )
    )

    # Apply date filters
    if date_from is not None:
        base_query = base_query.filter(
            CirculationTransaction.checkout_date >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to is not None:
        base_query = base_query.filter(
            CirculationTransaction.checkout_date <= datetime.combine(date_to, datetime.max.time())
        )

    total_items = base_query.count()
    total_pages = max(1, math.ceil(total_items / page_size))

    history_transactions = base_query.options(
        joinedload(CirculationTransaction.item),
        joinedload(CirculationTransaction.bibliographic_record),
    ).order_by(
        CirculationTransaction.checkout_date.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    history = []
    for t in history_transactions:
        was_overdue_val = bool(
            t.return_date and was_returned_late(t.due_date, t.return_date)
        )
        history.append(BorrowerHistoryItem(
            item_id=t.item.item_id,
            bibliographic_record_id=t.bibliographic_record_id,
            title=t.bibliographic_record.title,
            checkout_date=t.checkout_date,
            due_date=t.due_date,
            return_date=t.return_date,
            was_overdue=was_overdue_val,
        ))

    return BorrowerHistoryResponse(
        borrower_id=borrower_id,
        borrower_name=borrower.full_name,
        history=history,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
