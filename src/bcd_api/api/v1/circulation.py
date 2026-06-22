"""
Circulation API Endpoints

Provides REST API endpoints for checkout, return, and renewal operations.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ...core.deps import get_db
from ...schemas.circulation import (
    BorrowerHistoryResponse,
    CheckoutRequest,
    ItemHistoryResponse,
    RenewRequest,
    RenewResponse,
    ReturnRequest,
)
from ...services import circulation_service

router = APIRouter(prefix="/circulation", tags=["circulation"])


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
def checkout_items(
    checkout_request: CheckoutRequest,
    db: Session = Depends(get_db)
):
    """
    Check out items to a borrower

    Validates borrower is active, not over limit, and items are available.
    Creates circulation transactions and sets items to 'on_loan' status.

    **Performance**: Completes in <500ms for 2 items per spec SC-001

    **Errors**:
    - 404: Borrower or item not found
    - 400: Borrower blocked, over limit, or item not available
    - 409: Item already on loan to another borrower
    """
    response = circulation_service.checkout_items(
        db=db,
        borrower_id=checkout_request.borrower_id,
        item_ids=checkout_request.item_ids,
        checked_out_by=checkout_request.checked_out_by
    )
    return response


@router.post("/return")
def return_items(
    return_request: ReturnRequest,
    db: Session = Depends(get_db)
):
    """
    Process return of items

    Calculates overdue status and automatically blocks borrowers with overdue items.
    Unblocks borrowers when all overdue items are returned.

    **Performance**: Completes in <400ms for 5 items per spec SC-002

    **Errors**:
    - 404: Item not found
    - 400: Item not currently on loan
    """
    response = circulation_service.return_items(
        db=db,
        item_ids=return_request.item_ids,
        returned_by=return_request.returned_by
    )
    return response



@router.post("/renew", response_model=RenewResponse)
def renew_items(
    renew_request: RenewRequest,
    db: Session = Depends(get_db)
):
    """
    Renew items for a borrower

    Extends due dates for items currently on loan to the borrower.
    Validates renewal limits and checks for holds/reservations.

    **Renewal Logic**:
    - Each item can be renewed up to `renewal_limit` times (default: 2)
    - Due date extended by `loan_duration_days` (default: 14 days)
    - Items with holds cannot be renewed

    **Errors**:
    - 404: Borrower or item not found
    - 400: Item not on loan to borrower or renewal limit exceeded
    """
    # If no item_ids specified, get all current loans
    item_ids = renew_request.item_ids
    if not item_ids:
        current_loans = circulation_service.get_borrower_current_loans(
            db=db,
            borrower_id=renew_request.borrower_id
        )
        item_ids = [loan["item_id"] for loan in current_loans if loan["can_renew"]]

    if not item_ids:
        from ...core.exceptions import NoRenewableItemsException
        raise NoRenewableItemsException(renew_request.borrower_id)

    response = circulation_service.renew_items(
        db=db,
        borrower_id=renew_request.borrower_id,
        item_ids=item_ids
    )
    return response



@router.get("/borrower/{borrower_id}/items")
def get_borrower_current_loans(
    borrower_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all active loans for a borrower

    Returns current checkout status including overdue warnings and renewal eligibility.

    **Response includes**:
    - Item details (ID, title, authors)
    - Checkout and due dates
    - Days until due / days overdue
    - Renewal status (count and eligibility)

    **Errors**:
    - 404: Borrower not found
    """
    loans = circulation_service.get_borrower_current_loans(
        db=db,
        borrower_id=borrower_id
    )
    return {
        "borrower_id": borrower_id,
        "loans_count": len(loans),
        "loans": loans
    }


@router.get("/item/{item_id}/history", response_model=ItemHistoryResponse)
def get_item_circulation_history(
    item_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Records per page"),
    date_from: Optional[date] = Query(None, description="Filter: checkout date on or after"),
    date_to: Optional[date] = Query(None, description="Filter: checkout date on or before"),
    db: Session = Depends(get_db),
):
    """
    Get paginated circulation history for an item.

    Returns the active loan (if any) and paginated completed loan history.

    **Errors**:
    - 404: Item not found
    """
    return circulation_service.get_item_circulation_history(
        db=db,
        item_id=item_id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/borrower/{borrower_id}/history", response_model=BorrowerHistoryResponse)
def get_borrower_circulation_history(
    borrower_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Records per page"),
    date_from: Optional[date] = Query(None, description="Filter: checkout date on or after"),
    date_to: Optional[date] = Query(None, description="Filter: checkout date on or before"),
    db: Session = Depends(get_db),
):
    """
    Get paginated circulation history for a borrower (completed transactions only).

    **Errors**:
    - 404: Borrower not found
    """
    return circulation_service.get_borrower_circulation_history(
        db=db,
        borrower_id=borrower_id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
    )
