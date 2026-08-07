"""Queries module for the borrower domain."""

import unicodedata
from datetime import date, datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import BorrowerNotFoundException
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class as ClassModel
from ._enrichment import (
    Counts,
    circulation_counts_by_borrower,
    class_details_by_id,
    apply_borrower_enrichment,
)


def get_borrower_by_id(db: Session, borrower_id: str) -> Borrower:
    """
    Retrieve a borrower by their borrower_id.

    Args:
        db: Database session
        borrower_id: Borrower ID to lookup

    Returns:
        Borrower object

    Raises:
        BorrowerNotFoundException: Borrower not found
    """
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise BorrowerNotFoundException(borrower_id)
    return borrower


def get_next_available_id(db: Session) -> str:
    """
    Find the smallest positive integer not currently used as a borrower_id.

    Allows reuse of IDs freed when students leave (e.g., CM2 deletion at year-end).
    Non-numeric borrower IDs (e.g., "PROF1") are ignored.
    """
    rows = db.query(Borrower.borrower_id).all()
    used_ids = set()
    for (bid,) in rows:
        try:
            n = int(bid)
            if n > 0:
                used_ids.add(n)
        except (ValueError, TypeError):
            pass

    candidate = 1
    while candidate in used_ids:
        candidate += 1
    return str(candidate)


def _normalize(s: str) -> str:
    """Strip accents and lowercase for accent-insensitive comparison."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def list_borrowers(
    db: Session,
    search: Optional[str] = None,
    class_id: Optional[int] = None,
    role: Optional[str] = None,
    active: Optional[bool] = None,
    blocked: Optional[bool] = None,
    has_overdue: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Borrower], int]:
    """
    List borrowers with optional filters.

    Args:
        db: Database session
        search: Search query for name or borrower_id
        class_id: Filter by class ID
        role: Filter by role (student/teacher/staff)
        active: Filter by active status (True/False)
        blocked: Filter by blocked status (True = blocked, False = active)
        has_overdue: Filter by overdue status (True = has overdue items)
        limit: Maximum number of results (default 100)
        offset: Number of results to skip (pagination)

    Returns:
        Tuple of (List of Borrower objects, total count)
    """
    query = db.query(Borrower)

    # Apply filters
    if class_id is not None:
        query = query.filter(Borrower.class_id == class_id)

    if role is not None:
        query = query.filter(Borrower.role == role)

    if active is not None:
        query = query.filter(Borrower.active == active)

    if blocked is not None:
        # blocked=True means active=False
        query = query.filter(Borrower.active == (not blocked))

    # Filter by overdue status
    if has_overdue is not None and has_overdue:
        # Join with CirculationTransaction to find borrowers with overdue items
        query = query.join(CirculationTransaction, Borrower.id == CirculationTransaction.borrower_id)
        query = query.filter(
            and_(
                CirculationTransaction.return_date.is_(None),
                CirculationTransaction.due_date < date.today()
            )
        ).distinct()

    # Order by class name, then last name, then first name
    query = query.outerjoin(ClassModel, Borrower.class_id == ClassModel.id)
    query = query.order_by(ClassModel.name, Borrower.last_name, Borrower.first_name)

    # Apply accent-insensitive search filter in Python (SQLite has no unaccent support)
    if search:
        normalized_search = _normalize(search)
        results = [
            b for b in query.all()
            if normalized_search in _normalize(b.first_name)
            or normalized_search in _normalize(b.last_name)
            or normalized_search in _normalize(b.full_name)
            or normalized_search in b.borrower_id.lower()
        ]
        total = len(results)
        return results[offset:offset + limit], total

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    query = query.limit(limit).offset(offset)

    return query.all(), total


def get_borrower_details(db: Session, borrower_id: str) -> dict:
    """
    Get detailed information about a borrower including statistics.

    Args:
        db: Database session
        borrower_id: Borrower ID

    Returns:
        Dictionary with borrower info and statistics

    Raises:
        BorrowerNotFoundException: Borrower not found
    """
    borrower = get_borrower_by_id(db, borrower_id)

    # Get current loans count
    current_loans_count = (
        db.query(func.count(CirculationTransaction.id))
        .filter(
            CirculationTransaction.borrower_id == borrower.id,
            CirculationTransaction.return_date.is_(None),
        )
        .scalar()
    )

    # Get total checkouts count
    total_checkouts = (
        db.query(func.count(CirculationTransaction.id))
        .filter(CirculationTransaction.borrower_id == borrower.id)
        .scalar()
    )

    # Get overdue count
    overdue_count = (
        db.query(func.count(CirculationTransaction.id))
        .filter(
            CirculationTransaction.borrower_id == borrower.id,
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < date.today(),
        )
        .scalar()
    )

    return {
        "borrower": borrower,
        "current_loans_count": current_loans_count,
        "total_checkouts": total_checkouts,
        "overdue_count": overdue_count,
    }


def enrich_borrowers(
    db: Session,
    borrowers: List[Borrower],
    settings: Optional[Any] = None,
) -> List[Borrower]:
    """Enrich a list of borrower objects with class, circulation, and limit stats in batch."""
    if not borrowers:
        return borrowers

    from src.bcd_api.services import settings_service
    if settings is None:
        settings = settings_service.get_settings(db)

    from src.bcd_api.services.circulation.policy import CirculationPolicy
    policy = CirculationPolicy.from_settings(settings)
    settings_warning = settings.loan_limit_warning

    borrower_ids = [b.id for b in borrowers]
    counts_map = circulation_counts_by_borrower(db, borrower_ids)

    class_ids = [b.class_id for b in borrowers if b.class_id is not None]
    class_map = class_details_by_id(db, class_ids)

    for b in borrowers:
        counts = counts_map.get(b.id, Counts(0, 0))
        class_details = class_map.get(b.class_id) if b.class_id else None
        apply_borrower_enrichment(b, counts, class_details, policy, settings_warning)

    return borrowers


def enrich_borrower(
    db: Session,
    borrower: Borrower,
    settings: Optional[Any] = None,
) -> Borrower:
    """Enrich a single borrower object."""
    return enrich_borrowers(db, [borrower], settings)[0]


def get_detailed_borrower(
    db: Session,
    borrower_id: str,
    include_loans: bool = False,
) -> dict:
    """
    Get highly detailed borrower representation, completely enriched and mapped.
    """
    from src.bcd_api.services import settings_service
    from src.bcd_api.schemas.borrower import BorrowerDetailed
    from src.bcd_api.services import circulation_service

    details = get_borrower_details(db, borrower_id)
    borrower = details["borrower"]

    # Get loan limit based on role from system settings
    settings = settings_service.get_settings(db)
    enrich_borrower(db, borrower, settings)

    borrower_dict = borrower.__dict__.copy()
    borrower_dict.update({
        "barcode": borrower.barcode,  # Computed property not in __dict__
        "current_loans_count": details["current_loans_count"],
        "total_checkouts": details["total_checkouts"],
        "overdue_count": details["overdue_count"],
        "loan_limit": borrower.loan_limit,
        "loan_limit_warning": borrower.loan_limit_warning,
        "class_name": borrower.class_name,
        "homeroom_teacher": borrower.homeroom_teacher,
    })

    borrower_detailed = BorrowerDetailed(**borrower_dict)
    res = borrower_detailed.model_dump(mode='json')

    if include_loans:
        current_loans = circulation_service.get_borrower_current_loans(db, borrower_id)
        res["current_loans"] = current_loans

    return res

