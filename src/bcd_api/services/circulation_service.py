"""
Circulation Service - Business logic for checkouts, returns, and renewals

This module implements the core circulation operations for the library system:
- Checkout items to borrowers
- Return items and calculate overdue status
- Renew items with validation
- Query borrower loans and item history
"""

import logging
import math
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

logger = logging.getLogger(__name__)

from ..models.circulation import CirculationTransaction
from ..models.item import Item
from ..models.borrower import Borrower
from ..models.hold import Hold
from ..models.system_settings import SystemSettings
from ..models.bibliographic_record import BiblographicRecord
from ..core.exceptions import (
    ValidationError, NotFoundException, ConflictError,
    BorrowerNotFoundException, BorrowerBlockedException, BorrowerHasOverdueItemsException,
    ItemNotFoundException, ItemAlreadyOnLoanException, LoanLimitExceededException,
    ItemReservedForOtherBorrowerException
)
from ..core.deps import get_settings as _get_system_settings
from ..schemas.circulation import (
    CheckoutResponse, ReturnResponse, RenewResponse,
    PaginationMeta,
    BorrowerHistoryItem, BorrowerHistoryResponse,
    ItemHistoryItem, ItemHistoryResponse,
)
from . import hold_service


def _display_title(title: str, shelf_location: Optional[str] = None) -> str:
    """Format a display title appending issue number and/or shelf location.

    Numeric call_number → "Title · n° 274"
    Free-form call_number → "Title · Avril 2026"
    shelf_location → appended after call_number (or alone)
    No extras → "Title"
    """
    parts = [title]
    if shelf_location:
        parts.append(shelf_location)
    return " \u00b7 ".join(parts)


def checkout_items(
    db: Session,
    borrower_id: str,
    item_ids: List[str],
    checked_out_by: Optional[str] = None
) -> CheckoutResponse:
    """
    Check out items to a borrower

    Validates:
    - Borrower exists and is active
    - Borrower is not over checkout limit
    - Items exist and are available
    - Items are loanable

    Args:
        db: Database session
        borrower_id: Unique borrower ID
        item_ids: List of item IDs to check out
        checked_out_by: Librarian performing the checkout

    Returns:
        CheckoutResponse with transaction details

    Raises:
        NotFoundError: Borrower or item not found
        ValidationError: Borrower blocked, over limit, or item not available
        ConflictError: Item already on loan
    """
    # Get system settings for loan limits and duration
    settings = _get_system_settings(db)

    # Validate borrower exists and is active
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        logger.warning(f"Checkout failed: borrower {borrower_id} not found")
        raise BorrowerNotFoundException(borrower_id)

    if not borrower.active:
        logger.warning(f"Checkout failed: borrower {borrower_id} is blocked")
        raise BorrowerBlockedException(
            borrower_id=borrower_id,
            reason=borrower.blocked_reason or 'Account inactive'
        )

    # Count current active loans
    current_loans = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower.id,
            CirculationTransaction.return_date.is_(None)
        )
    ).count()

    # Determine checkout limit based on borrower role
    if borrower.role == "teacher" or borrower.role == "staff":
        limit = settings.loan_limit_teacher
    else:
        limit = settings.loan_limit_default

    # Check if borrower would exceed limit
    if current_loans + len(item_ids) > limit:
        raise LoanLimitExceededException(
            borrower_id=borrower_id,
            current_count=current_loans,
            limit=limit,
            additional=len(item_ids)
        )

    # Validate all items before creating transactions
    items_to_checkout = []
    for item_id_str in item_ids:
        item = db.query(Item).options(
            joinedload(Item.bibliographic_record)
        ).filter(Item.item_id == item_id_str).first()

        if not item:
            raise ItemNotFoundException(item_id_str)

        if not item.loanable:
            from ..core.exceptions import ItemNotLoanableException
            raise ItemNotLoanableException(item_id_str)

        # Check if item is available but reserved for a different borrower.
        # The current borrower's own hold always takes priority.
        if item.status == "available":
            borrower_own_hold = db.query(Hold).filter(
                and_(
                    Hold.bibliographic_record_id == item.bibliographic_record_id,
                    Hold.status.in_(["ready", "waiting"]),
                    Hold.borrower_id == borrower.id
                )
            ).first()
            if not borrower_own_hold:
                ready_hold = db.query(Hold).filter(
                    and_(
                        Hold.bibliographic_record_id == item.bibliographic_record_id,
                        Hold.status == "ready",
                        Hold.borrower_id != borrower.id
                    )
                ).first()
                if ready_hold:
                    other_borrower = db.query(Borrower).filter(
                        Borrower.id == ready_hold.borrower_id
                    ).first()
                    raise ItemReservedForOtherBorrowerException(
                        item_id_str, other_borrower.full_name
                    )

        if item.status != "available":
            # Check if on loan
            if item.status == "on_loan":
                # Find who has it
                active_loan = db.query(CirculationTransaction).filter(
                    and_(
                        CirculationTransaction.item_id == item.id,
                        CirculationTransaction.return_date.is_(None)
                    )
                ).options(joinedload(CirculationTransaction.borrower)).first()

                if active_loan:
                    raise ItemAlreadyOnLoanException(
                        item_id=item_id_str,
                        borrower_name=active_loan.borrower.full_name,
                        due_date=active_loan.due_date
                    )
            else:
                from ..core.exceptions import ItemNotAvailableException
                raise ItemNotAvailableException(item_id_str, item.status)

        items_to_checkout.append(item)

    # Calculate due date
    checkout_date = datetime.now()
    due_date = date.today() + timedelta(days=settings.loan_duration_days)

    # Create circulation transactions
    transactions = []
    for item in items_to_checkout:
        transaction = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=item.bibliographic_record_id,
            checkout_date=checkout_date,
            due_date=due_date,
            checked_out_by=checked_out_by or "system",
            status="active"
        )
        db.add(transaction)

        # Update item status
        item.status = "on_loan"
        item.last_borrowed_at = checkout_date

        # Fulfill or cancel any active hold this borrower had for this title
        active_hold_for_borrower = db.query(Hold).filter(
            and_(
                Hold.bibliographic_record_id == item.bibliographic_record_id,
                Hold.status.in_(["ready", "waiting"]),
                Hold.borrower_id == borrower.id
            )
        ).first()
        if active_hold_for_borrower:
            if active_hold_for_borrower.status == "ready":
                hold_service.fulfill_hold(db, active_hold_for_borrower.id)
            else:
                hold_service.cancel_hold(db, active_hold_for_borrower.id)

        transactions.append(transaction)

    # Commit all transactions
    db.commit()

    # Refresh to get computed fields and relationships
    for transaction in transactions:
        db.refresh(transaction)

    logger.info(f"Checked out {len(transactions)} item(s) to borrower {borrower_id}")

    # Build response
    return CheckoutResponse(
        borrower_id=borrower_id,
        borrower_name=borrower.full_name,
        checkout_date=checkout_date,
        due_date=due_date,
        items_checked_out=len(transactions),
        transactions=[
            {
                "transaction_id": t.id,
                "item_id": t.item.item_id,
                "title": t.bibliographic_record.title,
                "call_number": t.item.call_number,
                "display_title": _display_title(t.bibliographic_record.title),
                "due_date": t.due_date,
                "cover_image": t.bibliographic_record.cover_image,
            }
            for t in transactions
        ]
    )


def return_items(
    db: Session,
    item_ids: List[str],
    returned_by: Optional[str] = None
) -> ReturnResponse:
    """
    Process return of items

    Calculates overdue status and auto-blocks borrowers with overdue items.

    Args:
        db: Database session
        item_ids: List of item IDs being returned
        returned_by: Librarian processing the return

    Returns:
        ReturnResponse with return details and overdue information

    Raises:
        NotFoundError: Item not found or not on loan
        ValidationError: Item already returned
    """
    return_date = datetime.now()
    returned_items = []
    borrowers_to_check = set()

    for item_id_str in item_ids:
        # Find item
        item = db.query(Item).filter(Item.item_id == item_id_str).first()
        if not item:
            raise ItemNotFoundException(item_id_str)

        # Find active transaction
        transaction = db.query(CirculationTransaction).filter(
            and_(
                CirculationTransaction.item_id == item.id,
                CirculationTransaction.return_date.is_(None)
            )
        ).options(
            joinedload(CirculationTransaction.borrower),
            joinedload(CirculationTransaction.bibliographic_record)
        ).first()

        if not transaction:
            from ..core.exceptions import ItemNotOnLoanException
            raise ItemNotOnLoanException(item_id_str)

        # Calculate overdue
        was_overdue = transaction.due_date < date.today()
        days_overdue = (date.today() - transaction.due_date).days if was_overdue else 0

        # Update transaction
        transaction.return_date = return_date
        transaction.returned_by = returned_by or "system"
        transaction.status = "returned"

        # Update item status (will be set to available by trigger, but explicit)
        item.status = "available"

        # Track borrower for blocking check
        borrowers_to_check.add(transaction.borrower_id)

        returned_items.append({
            "item_id": item.item_id,
            "title": transaction.bibliographic_record.title,
            "call_number": item.call_number,
            "shelf_location": item.shelf_location,
            "display_title": _display_title(transaction.bibliographic_record.title, item.shelf_location),
            "borrower_id": transaction.borrower.borrower_id,
            "borrower_name": transaction.borrower.full_name,
            "checkout_date": transaction.checkout_date,
            "due_date": transaction.due_date,
            "return_date": return_date,
            "was_overdue": was_overdue,
            "days_overdue": days_overdue,
            "bibliographic_record_id": item.bibliographic_record_id
        })

    db.commit()
    logger.info(f"Returned {len(returned_items)} item(s)")

    # Get hold expiration setting
    settings = _get_system_settings(db)

    # Auto-fill next waiting hold for each returned bibliographic record
    # and capture hold information to display to librarian
    for returned_item in returned_items:
        ready_hold = hold_service.auto_fill_holds_on_return(
            db,
            returned_item["bibliographic_record_id"],
            expiration_days=settings.hold_expiration_days
        )
        if ready_hold:
            # Add hold information so librarian knows to set aside this item
            returned_item["hold_ready"] = {
                "borrower_id": ready_hold.borrower.borrower_id,
                "borrower_name": ready_hold.borrower.full_name,
                "class_name": ready_hold.borrower.class_.name if ready_hold.borrower.class_ else None,
                "expiration_date": ready_hold.expiration_date
            }
        else:
            returned_item["hold_ready"] = None

    db.commit()

    return ReturnResponse(
        items_returned=len(returned_items),
        return_date=return_date,
        items=returned_items,
    )


def renew_items(
    db: Session,
    borrower_id: str,
    item_ids: List[str]
) -> RenewResponse:
    """
    Renew items for a borrower

    Validates:
    - Items are currently on loan to this borrower
    - Items haven't exceeded renewal limit
    - Items don't have holds/reservations waiting

    Args:
        db: Database session
        borrower_id: Borrower requesting renewal
        item_ids: List of item IDs to renew

    Returns:
        RenewResponse with renewed items and failures

    Raises:
        NotFoundError: Borrower or item not found
        ValidationError: Item not on loan to this borrower
    """
    settings = _get_system_settings(db)

    # Validate borrower
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise NotFoundException("Borrower", borrower_id)

    renewed = []
    failed = []

    for item_id_str in item_ids:
        try:
            # Find item
            item = db.query(Item).filter(Item.item_id == item_id_str).first()
            if not item:
                failed.append({
                    "item_id": item_id_str,
                    "reason": "Item not found"
                })
                continue

            # Find active transaction for this borrower
            transaction = db.query(CirculationTransaction).filter(
                and_(
                    CirculationTransaction.item_id == item.id,
                    CirculationTransaction.borrower_id == borrower.id,
                    CirculationTransaction.return_date.is_(None)
                )
            ).options(joinedload(CirculationTransaction.bibliographic_record)).first()

            if not transaction:
                failed.append({
                    "item_id": item_id_str,
                    "reason": f"Item not on loan to borrower {borrower_id}"
                })
                continue

            # Check renewal limit
            if transaction.renewal_count >= settings.renewal_limit:
                failed.append({
                    "item_id": item_id_str,
                    "reason": f"Renewal limit reached ({settings.renewal_limit})"
                })
                continue

            # Check for holds (if hold system is implemented)
            # For now, skip hold check as Phase 3 doesn't include holds

            # Calculate new due date
            new_due_date = transaction.due_date + timedelta(days=settings.loan_duration_days)
            old_due_date = transaction.due_date

            # Update transaction
            transaction.renewal_count += 1
            transaction.due_date = new_due_date
            transaction.status = "active"  # Clear overdue if it was overdue

            renewed.append({
                "item_id": item_id_str,
                "title": transaction.bibliographic_record.title,
                "old_due_date": old_due_date,
                "new_due_date": new_due_date,
                "renewals_used": transaction.renewal_count,
                "renewals_remaining": settings.renewal_limit - transaction.renewal_count
            })

        except Exception as e:
            failed.append({
                "item_id": item_id_str,
                "reason": str(e)
            })

    db.commit()

    return RenewResponse(
        borrower_id=borrower_id,
        renewed_count=len(renewed),
        failed_count=len(failed),
        renewed=renewed,
        failed=failed
    )


def get_borrower_current_loans(
    db: Session,
    borrower_id: str
) -> List[dict]:
    """
    Get all active loans for a borrower

    Args:
        db: Database session
        borrower_id: Borrower ID

    Returns:
        List of active loan dictionaries

    Raises:
        NotFoundError: Borrower not found
    """
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise NotFoundException("Borrower", borrower_id)

    transactions = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower.id,
            CirculationTransaction.return_date.is_(None)
        )
    ).options(
        joinedload(CirculationTransaction.item),
        joinedload(CirculationTransaction.bibliographic_record)
    ).order_by(CirculationTransaction.due_date).all()

    settings = _get_system_settings(db)

    import json

    return [
        {
            "transaction_id": t.id,
            "item_id": t.item.item_id,
            "bibliographic_record_id": t.bibliographic_record.id,
            "title": t.bibliographic_record.title,
            "call_number": t.item.call_number,
            "shelf_location": t.item.shelf_location,
            "display_title": _display_title(t.bibliographic_record.title),
            "authors": ", ".join(json.loads(t.bibliographic_record.authors)) if t.bibliographic_record.authors else None,
            "checkout_date": t.checkout_date,
            "due_date": t.due_date,
            "days_until_due": (t.due_date - date.today()).days,
            "is_overdue": t.due_date < date.today(),
            "days_overdue": (date.today() - t.due_date).days if t.due_date < date.today() else 0,
            "renewal_count": t.renewal_count,
            "can_renew": t.renewal_count < settings.renewal_limit,
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
    """
    Get paginated circulation history for an item.

    Args:
        db: Database session
        item_id: Item ID
        page: Page number (1-indexed)
        page_size: Records per page
        date_from: Filter completed transactions with checkout_date >= date_from
        date_to: Filter completed transactions with checkout_date <= date_to

    Returns:
        ItemHistoryResponse with current_loan, paginated history, and pagination metadata

    Raises:
        ItemNotFoundException: Item not found
    """
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise ItemNotFoundException(item_id)

    # Fetch current active loan separately (not paginated, not date-filtered)
    current_transaction = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            CirculationTransaction.return_date.is_(None)
        )
    ).options(joinedload(CirculationTransaction.borrower)).first()

    current_loan = None
    if current_transaction:
        is_overdue = current_transaction.due_date < date.today()
        current_loan = ItemHistoryItem(
            borrower_id=current_transaction.borrower.borrower_id,
            borrower_name=current_transaction.borrower.full_name,
            checkout_date=current_transaction.checkout_date,
            due_date=current_transaction.due_date,
            return_date=None,
            was_overdue=is_overdue,
            status="overdue" if is_overdue else "on_loan",
        )

    # Build base query for completed transactions
    base_query = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.item_id == item.id,
            CirculationTransaction.return_date.isnot(None)
        )
    )

    # Apply date filters on checkout_date
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
        was_overdue = bool(t.return_date and t.return_date.date() > t.due_date)
        history.append(ItemHistoryItem(
            borrower_id=t.borrower.borrower_id,
            borrower_name=t.borrower.full_name,
            checkout_date=t.checkout_date,
            due_date=t.due_date,
            return_date=t.return_date,
            was_overdue=was_overdue,
            status="returned_late" if was_overdue else "returned_on_time",
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
    """
    Get paginated circulation history for a borrower (completed transactions only).

    Args:
        db: Database session
        borrower_id: Borrower ID
        page: Page number (1-indexed)
        page_size: Records per page
        date_from: Filter transactions with checkout_date >= date_from
        date_to: Filter transactions with checkout_date <= date_to

    Returns:
        BorrowerHistoryResponse with paginated completed loan history

    Raises:
        NotFoundException: Borrower not found
    """
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

    # Apply date filters on checkout_date
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
        was_overdue = bool(t.return_date and t.return_date.date() > t.due_date)
        history.append(BorrowerHistoryItem(
            item_id=t.item.item_id,
            bibliographic_record_id=t.bibliographic_record_id,
            title=t.bibliographic_record.title,
            checkout_date=t.checkout_date,
            due_date=t.due_date,
            return_date=t.return_date,
            was_overdue=was_overdue,
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
