"""
Holds API Endpoints

REST API for managing holds/reservations.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.deps import get_db
from ...schemas.hold import (
    HoldCreate,
    HoldResponse,
    HoldWithDetails,
)
from ...services.holds import commands as hold_commands
from ...services.holds import queries as hold_queries

router = APIRouter(prefix="/holds", tags=["holds"])


@router.post("", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
def create_hold(
    hold_data: HoldCreate,
    db: Session = Depends(get_db),
):
    """
    Place a hold/reservation for a bibliographic record.

    Args:
        hold_data: Hold creation data
        db: Database session

    Returns:
        Created hold

    Raises:
        404: Borrower or bibliographic record not found
        400: Validation error (borrower blocked, no items, etc.)
        409: Borrower already has hold for this record
    """
    hold = hold_commands.create_hold(
        db=db,
        borrower_id=hold_data.borrower_id,
        bibliographic_record_id=hold_data.bibliographic_record_id,
        created_by=hold_data.created_by or "api",
        notes=hold_data.notes,
    )
    return hold


@router.get("/ready", response_model=List[HoldWithDetails])
def get_ready_holds(db: Session = Depends(get_db)):
    """
    Get all holds that are ready for pickup.

    Args:
        db: Database session

    Returns:
        List of holds with status='ready'
    """
    holds = hold_queries.get_ready_holds(db)
    return holds


@router.get("/{hold_id}", response_model=HoldWithDetails)
def get_hold(
    hold_id: int,
    db: Session = Depends(get_db),
):
    """
    Get hold by ID with full details.

    Args:
        hold_id: Hold ID
        db: Database session

    Returns:
        Hold with borrower and bibliographic record details

    Raises:
        404: Hold not found
    """
    hold = hold_queries.get_hold(db, hold_id)
    return hold


@router.get("/borrower/{borrower_id}", response_model=List[HoldWithDetails])
def get_holds_for_borrower(
    borrower_id: int,
    include_fulfilled: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get all holds for a borrower.

    Args:
        borrower_id: Borrower ID
        include_fulfilled: Include fulfilled/cancelled/expired holds
        db: Database session

    Returns:
        List of holds
    """
    holds = hold_queries.get_holds_for_borrower(
        db, borrower_id, include_fulfilled=include_fulfilled
    )
    return holds


@router.get("/bibliographic/{biblio_id}", response_model=List[HoldWithDetails])
def get_holds_for_title(
    biblio_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    Get all holds for a bibliographic record.

    Args:
        biblio_id: Bibliographic record ID
        active_only: Only return waiting/ready holds
        db: Database session

    Returns:
        List of holds ordered by queue position
    """
    holds = hold_queries.get_holds_for_bibliographic_record(
        db, biblio_id, active_only=active_only
    )
    return holds


@router.post("/{hold_id}/ready", response_model=HoldResponse)
def mark_hold_ready(
    hold_id: int,
    expiration_days: int = 3,
    db: Session = Depends(get_db),
):
    """
    Mark a hold as ready for pickup.

    Args:
        hold_id: Hold ID
        expiration_days: Days until hold expires
        db: Database session

    Returns:
        Updated hold

    Raises:
        404: Hold not found
        400: Hold not in waiting status
    """
    hold = hold_commands.mark_hold_ready(db, hold_id, expiration_days)
    return hold


@router.post("/{hold_id}/fulfill", status_code=status.HTTP_204_NO_CONTENT)
def fulfill_hold(
    hold_id: int,
    db: Session = Depends(get_db),
):
    """
    Fulfill and delete hold (item checked out).
    No history is kept to save database space.

    Args:
        hold_id: Hold ID
        db: Database session

    Raises:
        404: Hold not found
        400: Hold not ready
    """
    hold_commands.fulfill_hold(db, hold_id)
    return None


@router.delete("/{hold_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_hold(
    hold_id: int,
    db: Session = Depends(get_db),
):
    """
    Cancel a hold.

    Args:
        hold_id: Hold ID
        db: Database session

    Raises:
        404: Hold not found
        400: Hold already fulfilled/cancelled/expired
    """
    hold_commands.cancel_hold(db, hold_id)
