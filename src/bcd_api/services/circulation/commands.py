"""Circulation Commands - Checkout, return, and renew operations.

This module encapsulates all database mutation operations for circulation.
Each command possesses a single transaction boundary (try-commit-rollback).
Batch loads are preferred to eliminate N+1 queries.
"""

import logging
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from ...core.deps import get_settings
from ...core.exceptions import (
    BorrowerBlockedException,
    BorrowerNotFoundException,
    ItemAlreadyOnLoanException,
    ItemNotAvailableException,
    ItemNotFoundException,
    ItemNotLoanableException,
    ItemReservedForOtherBorrowerException,
    LoanLimitExceededException,
    LoanLimitWarningExceededException,
    NoRenewableItemsException,
    NotFoundException,
    ValidationError,
)
from ...models.borrower import Borrower
from ...models.circulation import CirculationTransaction
from ...models.hold import Hold
from ...models.item import Item
from ...schemas.circulation import (
    CheckoutResponse,
    RenewResponse,
    ReturnResponse,
)
from ..holds import commands as hold_commands
from ._presentation import display_title
from .policy import (
    CirculationPolicy,
    is_overdue,
    overdue_days,
)

logger = logging.getLogger(__name__)


def checkout_items(
    db: Session,
    borrower_id: str,
    item_ids: List[str],
    checked_out_by: Optional[str] = None
) -> CheckoutResponse:
    """Check out items to a borrower. Fully atomic and batch-loaded."""
    # 1. Validate scanner duplicates
    if len(item_ids) != len(set(item_ids)):
        raise ValidationError("La liste d'exemplaires contient des doublons.")

    # 2. Load settings and borrower
    settings = get_settings(db)
    policy = CirculationPolicy.from_settings(settings)

    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise BorrowerNotFoundException(borrower_id)

    if not borrower.active:
        raise BorrowerBlockedException(
            borrower_id=borrower_id,
            reason=borrower.blocked_reason or 'Account inactive'
        )

    # 3. Batch load loans count for borrower
    current_loans = db.query(CirculationTransaction).filter(
        CirculationTransaction.borrower_id == borrower.id,
        CirculationTransaction.return_date.is_(None),
    ).count()

    # Validate limits with policy
    decision = policy.checkout_decision(
        role=borrower.role,
        current_loans_count=current_loans,
        additional_count=len(item_ids),
        is_godot_ui=(checked_out_by == "godot-ui")
    )
    if not decision.allowed:
        if decision.error_code == "LOAN_LIMIT_WARNING_EXCEEDED":
            raise LoanLimitWarningExceededException(
                borrower_id=borrower_id,
                current_count=current_loans,
                limit=policy.kids_warning_limit,
                additional=len(item_ids)
            )
        else:
            raise LoanLimitExceededException(
                borrower_id=borrower_id,
                current_count=current_loans,
                limit=policy.loan_limit_for(borrower.role),
                additional=len(item_ids)
            )

    # 4. Batch load all requested items with records in ONE query
    items = db.query(Item).options(
        joinedload(Item.bibliographic_record)
    ).filter(Item.item_id.in_(item_ids)).all()

    item_map = {item.item_id: item for item in items}

    # Validate existence & loanable status
    items_to_checkout = []
    for item_id in item_ids:
        if item_id not in item_map:
            raise ItemNotFoundException(item_id)
        item = item_map[item_id]
        if not item.loanable:
            raise ItemNotLoanableException(item_id)
        items_to_checkout.append(item)

    # 5. Batch load all active holds for bibliographic records of these items
    bib_ids = [item.bibliographic_record_id for item in items_to_checkout]
    active_holds = db.query(Hold).options(
        joinedload(Hold.borrower)
    ).filter(
        and_(
            Hold.bibliographic_record_id.in_(bib_ids),
            Hold.status.in_(["waiting", "ready"])
        )
    ).all()

    # Organize holds by record ID
    holds_by_record = {}
    for hold in active_holds:
        holds_by_record.setdefault(hold.bibliographic_record_id, []).append(hold)
    processed_hold_ids: set[int] = set()

    # 6. Batch load active loans for items not available
    unavailable_item_ids = [item.id for item in items_to_checkout if item.status != "available"]
    active_loans = []
    if unavailable_item_ids:
        active_loans = db.query(CirculationTransaction).options(
            joinedload(CirculationTransaction.borrower)
        ).filter(
            and_(
                CirculationTransaction.item_id.in_(unavailable_item_ids),
                CirculationTransaction.return_date.is_(None)
            )
        ).all()
    loans_map = {loan.item_id: loan for loan in active_loans}

    # 7. Core validations
    for item in items_to_checkout:
        # Check holds priority
        if item.status == "available":
            holds = holds_by_record.get(item.bibliographic_record_id, [])
            borrower_own_hold = next((h for h in holds if h.borrower_id == borrower.id), None)
            if not borrower_own_hold:
                any_other_hold = next((h for h in holds if h.borrower_id != borrower.id), None)
                if any_other_hold:
                    raise ItemReservedForOtherBorrowerException(
                        item.item_id,
                        any_other_hold.borrower.full_name,
                    )

        if item.status != "available":
            if item.status == "on_loan":
                active_loan = loans_map.get(item.id)
                if active_loan:
                    raise ItemAlreadyOnLoanException(
                        item_id=item.item_id,
                        borrower_name=active_loan.borrower.full_name,
                        due_date=active_loan.due_date
                    )
            else:
                raise ItemNotAvailableException(item.item_id, item.status)

    # 8. Start mutations and single transaction commit
    checkout_date = datetime.now()
    due_date = policy.checkout_due_date(date.today())

    transactions = []
    try:
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

            # Consume borrower's active hold
            holds = holds_by_record.get(item.bibliographic_record_id, [])
            borrower_own_hold = next(
                (
                    h for h in holds
                    if h.borrower_id == borrower.id
                    and h.id not in processed_hold_ids
                ),
                None,
            )
            if borrower_own_hold:
                if borrower_own_hold.status == "ready":
                    hold_commands.fulfill_hold_in_transaction(db, borrower_own_hold.id)
                else:
                    hold_commands.cancel_hold_in_transaction(db, borrower_own_hold.id)
                processed_hold_ids.add(borrower_own_hold.id)

            transactions.append(transaction)

        db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Refresh to get IDs/relationships
    for t in transactions:
        db.refresh(t)

    logger.info(f"Checked out {len(transactions)} item(s) to borrower {borrower_id}")

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
                "display_title": display_title(t.bibliographic_record.title),
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
    """Process return of items. Fully atomic and transaction safe."""
    if len(item_ids) != len(set(item_ids)):
        raise ValidationError("La liste d'exemplaires contient des doublons.")

    return_date = datetime.now()
    returned_items = []

    # Batch load items and active loans
    items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    item_map = {item.item_id: item for item in items}

    items_to_return = []
    for item_id in item_ids:
        if item_id not in item_map:
            raise ItemNotFoundException(item_id)
        items_to_return.append(item_map[item_id])

    db_item_ids = [item.id for item in items_to_return]
    active_loans = db.query(CirculationTransaction).options(
        joinedload(CirculationTransaction.borrower),
        joinedload(CirculationTransaction.bibliographic_record)
    ).filter(
        and_(
            CirculationTransaction.item_id.in_(db_item_ids),
            CirculationTransaction.return_date.is_(None)
        )
    ).all()

    loans_map = {loan.item_id: loan for loan in active_loans}

    # Verify all items are actually on loan
    for item in items_to_return:
        if item.id not in loans_map:
            from ...core.exceptions import ItemNotOnLoanException
            raise ItemNotOnLoanException(item.item_id)

    # Process return mutations in single transaction
    try:
        for item in items_to_return:
            transaction = loans_map[item.id]

            # Calculate overdue
            today = date.today()
            was_overdue = is_overdue(transaction.due_date, today)
            days_overdue = overdue_days(transaction.due_date, today)

            transaction.return_date = return_date
            transaction.returned_by = returned_by or "system"
            transaction.status = "returned"

            item.status = "available"

            returned_items.append({
                "item_id": item.item_id,
                "title": transaction.bibliographic_record.title,
                "call_number": item.call_number,
                "shelf_location": item.shelf_location,
                "display_title": display_title(transaction.bibliographic_record.title, item.shelf_location),
                "borrower_id": transaction.borrower.borrower_id,
                "borrower_name": transaction.borrower.full_name,
                "checkout_date": transaction.checkout_date,
                "due_date": transaction.due_date,
                "return_date": return_date,
                "was_overdue": was_overdue,
                "days_overdue": days_overdue,
                "bibliographic_record_id": item.bibliographic_record_id
            })

        # Promote waiting holds before the single commit of the return.
        settings = get_settings(db)
        for returned_item in returned_items:
            ready_hold = hold_commands.auto_fill_holds_on_return_in_transaction(
                db,
                returned_item["bibliographic_record_id"],
                expiration_days=settings.hold_expiration_days,
            )
            if ready_hold:
                returned_item["hold_ready"] = {
                    "borrower_id": ready_hold.borrower.borrower_id,
                    "borrower_name": ready_hold.borrower.full_name,
                    "class_name": ready_hold.borrower.class_.name if ready_hold.borrower.class_ else None,
                    "expiration_date": ready_hold.expiration_date,
                }
            else:
                returned_item["hold_ready"] = None

        db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReturnResponse(
        items_returned=len(returned_items),
        return_date=return_date,
        items=returned_items,
    )


def renew_items(
    db: Session,
    borrower_id: str,
    item_ids: Optional[List[str]] = None
) -> RenewResponse:
    """Renew items for a borrower. Successful requests are commited together."""
    if item_ids is None:
        from .queries import get_borrower_current_loans
        current_loans = get_borrower_current_loans(db=db, borrower_id=borrower_id)
        item_ids = [loan["item_id"] for loan in current_loans if loan["can_renew"]]
        if not item_ids:
            raise NoRenewableItemsException(borrower_id)

    if len(item_ids) != len(set(item_ids)):
        raise ValidationError("La liste d'exemplaires contient des doublons.")

    settings = get_settings(db)
    policy = CirculationPolicy.from_settings(settings)

    # Validate borrower
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise NotFoundException("Borrower", borrower_id)

    renewed = []
    failed = []

    # Batch load items and active loans
    items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    item_map = {item.item_id: item for item in items}

    bib_ids = [item.bibliographic_record_id for item in items]
    active_holds = db.query(Hold).filter(
        and_(
            Hold.bibliographic_record_id.in_(bib_ids),
            Hold.status.in_(["waiting", "ready"])
        )
    ).all()
    holds_by_record = {hold.bibliographic_record_id for hold in active_holds}

    transactions_to_renew = []

    for item_id_str in item_ids:
        if item_id_str not in item_map:
            failed.append({
                "item_id": item_id_str,
                "reason": "Item not found"
            })
            continue

        item = item_map[item_id_str]

        # Find active transaction
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

        # Evaluate renewal with policy
        has_hold = item.bibliographic_record_id in holds_by_record
        decision = policy.renewal_decision(transaction.renewal_count, has_hold)

        if not decision.allowed:
            failed.append({
                "item_id": item_id_str,
                "reason": decision.reason
            })
            continue

        transactions_to_renew.append((item_id_str, transaction))

    # Apply all successful mutations in a single transaction block
    if transactions_to_renew:
        try:
            for item_id_str, transaction in transactions_to_renew:
                new_due_date = policy.renewed_due_date(transaction.due_date)
                old_due_date = transaction.due_date

                transaction.renewal_count += 1
                transaction.due_date = new_due_date
                transaction.status = "active"

                renewed.append({
                    "item_id": item_id_str,
                    "title": transaction.bibliographic_record.title,
                    "old_due_date": old_due_date,
                    "new_due_date": new_due_date,
                    "renewals_used": transaction.renewal_count,
                    "renewals_remaining": policy.renewal_limit - transaction.renewal_count
                })

            db.flush()
            db.commit()
        except Exception:
            db.rollback()
            raise

    return RenewResponse(
        borrower_id=borrower_id,
        renewed_count=len(renewed),
        failed_count=len(failed),
        renewed=renewed,
        failed=failed
    )
