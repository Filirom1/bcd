"""
Borrower Service

Handles business logic for borrower management including:
- Creating borrowers (students, teachers, staff)
- Listing borrowers with filters
- Retrieving borrower details with circulation statistics
- Validating borrower IDs against configured format
- Auto-generating barcodes
"""

import logging
import unicodedata
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.bcd_api.core.exceptions import (
    DuplicateError,
)
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.system_settings import SystemSettings
from src.shared.constants import BorrowerRole
from src.shared.validators import validate_id_format


def create_borrower(
    db: Session,
    borrower_id: str,
    first_name: str,
    last_name: str,
    role: str = "student",
    class_id: Optional[int] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None,
) -> Borrower:
    """
    Create a new borrower.

    Args:
        db: Database session
        borrower_id: Unique borrower ID (validated against system settings)
        first_name: Borrower's first name
        last_name: Borrower's last name
        role: "student", "teacher", or "staff"
        class_id: Optional class ID (for students)
        email: Optional email address
        phone: Optional phone number
        notes: Optional notes

    Returns:
        Created Borrower object

    Raises:
        ValidationError: Invalid borrower ID format or role
        DuplicateError: Borrower ID already exists
        NotFoundError: Class ID not found
    """
    # Validate role
    try:
        BorrowerRole(role)
    except ValueError:
        from src.bcd_api.core.exceptions import InvalidIDFormatException
        valid_roles = ', '.join([r.value for r in BorrowerRole])
        raise InvalidIDFormatException("role", role, valid_roles)

    # Validate ID format against system settings
    settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if settings:
        if not validate_id_format(borrower_id, settings.id_validation_regex):
            from src.bcd_api.core.exceptions import InvalidIDFormatException
            raise InvalidIDFormatException("borrower_id", borrower_id, settings.id_format)

    # Check for duplicate borrower_id
    existing = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if existing:
        raise DuplicateError(f"Borrower ID '{borrower_id}' already exists")

    # Validate class exists if provided
    if class_id is not None:
        class_obj = db.query(Class).filter(Class.id == class_id).first()
        if not class_obj:
            from src.bcd_api.core.exceptions import NotFoundException
            raise NotFoundException("Class", class_id)

    # Create borrower
    full_name = f"{first_name} {last_name}"
    borrower = Borrower(
        borrower_id=borrower_id,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        role=role,
        class_id=class_id,
        active=True,
        email=email,
        phone=phone,
        notes=notes,
    )

    db.add(borrower)
    db.commit()
    db.refresh(borrower)

    logger.info(f"Created borrower {borrower_id} ({full_name}) - Role: {role}")
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


def get_borrower_by_id(db: Session, borrower_id: str) -> Borrower:
    """
    Retrieve a borrower by their borrower_id.

    Args:
        db: Database session
        borrower_id: Borrower ID to lookup

    Returns:
        Borrower object

    Raises:
        NotFoundError: Borrower not found
    """
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        from src.bcd_api.core.exceptions import BorrowerNotFoundException
        raise BorrowerNotFoundException(borrower_id)

    return borrower


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
) -> tuple[List[Borrower], int]:
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
    from datetime import date

    from sqlalchemy import and_

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
    from src.bcd_api.models.class_model import Class as ClassModel
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
        NotFoundError: Borrower not found
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
            CirculationTransaction.due_date < datetime.now().date(),
        )
        .scalar()
    )

    return {
        "borrower": borrower,
        "current_loans_count": current_loans_count,
        "total_checkouts": total_checkouts,
        "overdue_count": overdue_count,
    }


_UNSET = object()  # Sentinel value for "not provided"


def update_borrower(
    db: Session,
    borrower_id: str,
    new_borrower_id: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role: Optional[str] = None,
    class_id=_UNSET,  # Use sentinel to distinguish None (unassign) from not provided
    email: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None,
    active: Optional[bool] = None,
    blocked_reason: Optional[str] = None,
) -> Borrower:
    """
    Update borrower information.

    Args:
        db: Database session
        borrower_id: Current borrower ID (for lookup)
        new_borrower_id: New borrower ID (if changing the ID)
        first_name: New first name (or None to skip)
        last_name: New last name (or None to skip)
        role: New role (student/teacher/staff) (or None to skip)
        class_id: New class ID, None to unassign, or omit to keep current
        email: New email (or None to skip)
        phone: New phone (or None to skip)
        notes: New notes (or None to skip)
        active: New active status (or None to skip)
        blocked_reason: New blocked reason (or None to skip)

    Returns:
        Updated Borrower object

    Raises:
        NotFoundError: Borrower not found
        DuplicateError: New borrower ID already exists
        ValidationError: Invalid borrower ID format or role
    """
    borrower = get_borrower_by_id(db, borrower_id)

    # Track old role and class for student count updates
    old_role = borrower.role
    old_class_id = borrower.class_id
    class_id_changed = class_id is not _UNSET
    new_class_id = class_id if class_id_changed else old_class_id

    # Update borrower_id if provided
    if new_borrower_id is not None and new_borrower_id != borrower_id:
        # Validate ID format against system settings
        settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
        if settings:
            if not validate_id_format(new_borrower_id, settings.id_validation_regex):
                from src.bcd_api.core.exceptions import InvalidIDFormatException
                raise InvalidIDFormatException("borrower_id", new_borrower_id, settings.id_format)

        # Check for duplicate borrower_id
        existing = db.query(Borrower).filter(Borrower.borrower_id == new_borrower_id).first()
        if existing:
            raise DuplicateError(f"Borrower ID '{new_borrower_id}' already exists")

        borrower.borrower_id = new_borrower_id
        # Barcode is auto-computed from borrower_id (property)

    # Update role if provided
    if role is not None:
        # Validate role
        try:
            role_enum = BorrowerRole(role) if isinstance(role, str) else role
        except ValueError:
            from src.bcd_api.core.exceptions import InvalidIDFormatException
            valid_roles = ', '.join([r.value for r in BorrowerRole])
            raise InvalidIDFormatException("role", role, valid_roles)

        borrower.role = role_enum.value

    # Update fields if provided
    if first_name is not None:
        borrower.first_name = first_name
    if last_name is not None:
        borrower.last_name = last_name
    if first_name is not None or last_name is not None:
        borrower.full_name = f"{borrower.first_name} {borrower.last_name}"

    if class_id_changed:
        # Validate class exists (unless setting to None)
        if class_id is not None:
            class_obj = db.query(Class).filter(Class.id == class_id).first()
            if not class_obj:
                from src.bcd_api.core.exceptions import NotFoundException
                raise NotFoundException("Class", class_id)
        borrower.class_id = class_id

    if email is not None:
        borrower.email = email
    if phone is not None:
        borrower.phone = phone
    if notes is not None:
        borrower.notes = notes
    if active is not None:
        borrower.active = active
    if blocked_reason is not None:
        borrower.blocked_reason = blocked_reason

    borrower.updated_at = datetime.now()

    db.commit()
    db.refresh(borrower)

    # Determine final role after update
    final_role = borrower.role

    return borrower


def unblock_borrower(db: Session, borrower_id: str) -> Borrower:
    """
    Unblock a borrower by setting active=True and clearing blocked_reason.

    Args:
        db: Database session
        borrower_id: Borrower ID

    Returns:
        Updated Borrower object

    Raises:
        NotFoundError: Borrower not found
    """
    borrower = get_borrower_by_id(db, borrower_id)

    borrower.active = True
    borrower.blocked_reason = None
    borrower.updated_at = datetime.now()

    db.commit()
    db.refresh(borrower)

    return borrower


def block_borrower(db: Session, borrower_id: str, reason: str) -> Borrower:
    """
    Block a borrower by setting active=False and setting blocked_reason.

    Args:
        db: Database session
        borrower_id: Borrower ID
        reason: Reason for blocking

    Returns:
        Updated Borrower object

    Raises:
        NotFoundError: Borrower not found
    """
    borrower = get_borrower_by_id(db, borrower_id)

    borrower.active = False
    borrower.blocked_reason = reason
    borrower.updated_at = datetime.now()

    db.commit()
    db.refresh(borrower)

    return borrower


# Bulk operations

def bulk_change_class(
    db: Session,
    borrower_ids: List[str],
    new_class_id: Optional[int]
) -> dict:
    """
    Change class for multiple borrowers in a single atomic transaction.

    All borrowers will be updated to the new class, or none will be updated
    if any error occurs (atomic operation with rollback).

    Args:
        db: Database session
        borrower_ids: List of borrower IDs to update
        new_class_id: New class ID (or None to unassign from class)

    Returns:
        Dictionary with operation results:
        {
            "total_count": int,
            "successful_count": int,
            "failed_count": int,
            "operation": str
        }

    Raises:
        ClassNotFoundException: If new_class_id doesn't exist
        BorrowerNotFoundException: If any borrower_id doesn't exist
    """
    total_count = len(borrower_ids)

    if total_count == 0:
        return {
            "total_count": 0,
            "successful_count": 0,
            "failed_count": 0,
            "operation": "bulk_change_class"
        }

    # Validate new class exists if not None
    if new_class_id is not None:
        class_obj = db.query(Class).filter(Class.id == new_class_id).first()
        if not class_obj:
            from src.bcd_api.core.exceptions import ClassNotFoundException
            raise ClassNotFoundException(new_class_id)

    # Get all borrowers (will raise if any not found)
    borrowers = []
    for borrower_id in borrower_ids:
        borrower = get_borrower_by_id(db, borrower_id)
        borrowers.append(borrower)

    # Update all borrowers
    for borrower in borrowers:
        # Update borrower class
        borrower.class_id = new_class_id
        borrower.updated_at = datetime.now()

    # Commit transaction
    db.commit()

    logger.info(f"Bulk changed class for {total_count} borrowers to class {new_class_id}")

    return {
        "total_count": total_count,
        "successful_count": total_count,
        "failed_count": 0,
        "operation": "bulk_change_class"
    }


def bulk_change_role(
    db: Session,
    borrower_ids: List[str],
    new_role: str
) -> dict:
    """
    Change role for multiple borrowers in a single atomic transaction.

    All borrowers will be updated to the new role, or none will be updated
    if any error occurs (atomic operation with rollback).

    Args:
        db: Database session
        borrower_ids: List of borrower IDs to update
        new_role: New role (student, teacher, staff)

    Returns:
        Dictionary with operation results:
        {
            "total_count": int,
            "successful_count": int,
            "failed_count": int,
            "operation": str
        }

    Raises:
        ValidationError: If new_role is invalid
        BorrowerNotFoundException: If any borrower_id doesn't exist
    """
    total_count = len(borrower_ids)

    if total_count == 0:
        return {
            "total_count": 0,
            "successful_count": 0,
            "failed_count": 0,
            "operation": "bulk_change_role"
        }

    # Validate role
    try:
        BorrowerRole(new_role)
    except ValueError:
        from src.bcd_api.core.exceptions import InvalidIDFormatException
        valid_roles = ', '.join([r.value for r in BorrowerRole])
        raise InvalidIDFormatException("role", new_role, valid_roles)

    # Get all borrowers (will raise if any not found)
    borrowers = []
    for borrower_id in borrower_ids:
        borrower = get_borrower_by_id(db, borrower_id)
        borrowers.append(borrower)

    # Update all borrowers
    for borrower in borrowers:
        # Update borrower role
        borrower.role = new_role
        borrower.updated_at = datetime.now()

    # Commit transaction
    db.commit()

    logger.info(f"Bulk changed role for {total_count} borrowers to {new_role}")

    return {
        "total_count": total_count,
        "successful_count": total_count,
        "failed_count": 0,
        "operation": "bulk_change_role"
    }


def bulk_delete_borrowers(
    db: Session,
    borrower_ids: List[str]
) -> dict:
    """
    Delete multiple borrowers in a single atomic transaction.

    All borrowers and their circulation history will be deleted via CASCADE,
    or none will be deleted if any error occurs (atomic operation with rollback).

    Args:
        db: Database session
        borrower_ids: List of borrower IDs to delete

    Returns:
        Dictionary with operation results:
        {
            "total_count": int,
            "successful_count": int,
            "failed_count": int,
            "operation": str
        }

    Raises:
        BorrowerNotFoundException: If any borrower_id doesn't exist
    """
    total_count = len(borrower_ids)

    if total_count == 0:
        return {
            "total_count": 0,
            "successful_count": 0,
            "failed_count": 0,
            "operation": "bulk_delete_borrowers"
        }

    # Fetch all borrowers in ONE query
    borrowers = db.query(Borrower).filter(
        Borrower.borrower_id.in_(borrower_ids)
    ).all()

    # Verify all borrower_ids were found
    if len(borrowers) != len(borrower_ids):
        found_ids = {b.borrower_id for b in borrowers}
        missing_ids = set(borrower_ids) - found_ids
        from src.bcd_api.core.exceptions import BorrowerNotFoundException
        raise BorrowerNotFoundException(
            borrower_id=', '.join(missing_ids)
        )

    # Validate: Check for active loans in ONE batch query
    from src.bcd_api.models.circulation import CirculationTransaction

    internal_ids = [b.id for b in borrowers]

    borrower_with_loan = db.query(
        Borrower.borrower_id,
        Borrower.full_name,
        func.count(CirculationTransaction.id).label('loan_count')
    ).join(
        CirculationTransaction,
        CirculationTransaction.borrower_id == Borrower.id
    ).filter(
        Borrower.id.in_(internal_ids),
        CirculationTransaction.return_date.is_(None)
    ).group_by(
        Borrower.id, Borrower.borrower_id, Borrower.full_name
    ).first()

    if borrower_with_loan:
        from src.bcd_api.core.exceptions import BorrowerHasActiveLoansException
        raise BorrowerHasActiveLoansException(
            borrower_id=borrower_with_loan.borrower_id,
            borrower_name=borrower_with_loan.full_name,
            active_loan_count=borrower_with_loan.loan_count
        )

    # Delete all borrowers
    for borrower in borrowers:
        # Delete borrower (CASCADE will delete circulation history)
        db.delete(borrower)

    # Commit transaction
    db.commit()

    logger.info(f"Bulk deleted {total_count} borrowers")

    return {
        "total_count": total_count,
        "successful_count": total_count,
        "failed_count": 0,
        "operation": "bulk_delete_borrowers"
    }


def enrich_borrower(db: Session, borrower: Borrower, settings: Any = None) -> Borrower:
    """Enrich a single borrower object with class, circulation, and limit stats."""
    from datetime import date
    from sqlalchemy import and_
    from ..models import Class
    from ..models.circulation import CirculationTransaction
    from . import settings_service

    if settings is None:
        settings = settings_service.get_settings(db)

    # Get current loans count
    if hasattr(db, "query"):
        from .circulation.query_filters import active_loan_predicate, overdue_loan_predicate
        from .circulation.policy import CirculationPolicy

        current_loans_count = db.query(CirculationTransaction).filter(
            and_(
                CirculationTransaction.borrower_id == borrower.id,
                active_loan_predicate()
            )
        ).count()

        # Get overdue count
        overdue_count = db.query(CirculationTransaction).filter(
            and_(
                CirculationTransaction.borrower_id == borrower.id,
                overdue_loan_predicate(date.today())
            )
        ).count()
    else:
        from .circulation.policy import CirculationPolicy
        current_loans_count = getattr(borrower, "current_loans_count", 0)
        overdue_count = getattr(borrower, "overdue_count", 0)

    # Determine loan limit based on role
    loan_limit = CirculationPolicy.from_settings(settings).loan_limit_for(borrower.role)

    # Class details
    class_name, homeroom_teacher = None, None
    if borrower.class_id and hasattr(db, "query"):
        class_obj = db.query(Class).filter(Class.id == borrower.class_id).first()
        if class_obj:
            class_name = class_obj.name
            homeroom_teacher = class_obj.homeroom_teacher

    borrower.current_loans_count = current_loans_count
    borrower.loan_limit = loan_limit
    borrower.loan_limit_warning = settings.loan_limit_warning
    borrower.overdue_count = overdue_count
    borrower.class_name = class_name
    borrower.homeroom_teacher = homeroom_teacher

    return borrower

