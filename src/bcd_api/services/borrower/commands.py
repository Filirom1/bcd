"""Commands module for the borrower domain."""

import logging
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import (
    DuplicateError,
    BorrowerNotFoundException,
    ClassNotFoundException,
    BorrowerHasActiveLoansException,
)
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.system_settings import SystemSettings
from src.shared.constants import BorrowerRole
from ._validation import validate_role, validate_borrower_id, require_class, full_name

logger = logging.getLogger(__name__)

_UNSET = object()


def _get_borrower_or_raise(db: Session, borrower_id: str) -> Borrower:
    """Retrieve borrower or raise BorrowerNotFoundException."""
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise BorrowerNotFoundException(borrower_id)
    return borrower


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
    try:
        # Validate role
        validated_role = validate_role(role)

        # Validate ID format against system settings
        settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
        validate_borrower_id(borrower_id, settings)

        # Check for duplicate borrower_id
        existing = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
        if existing:
            raise DuplicateError(f"Borrower ID '{borrower_id}' already exists")

        # Validate class exists if provided
        if class_id is not None:
            require_class(db, class_id)

        # Create borrower
        name_full = full_name(first_name, last_name)
        borrower = Borrower(
            borrower_id=borrower_id,
            first_name=first_name,
            last_name=last_name,
            full_name=name_full,
            role=validated_role,
            class_id=class_id,
            active=True,
            email=email,
            phone=phone,
            notes=notes,
        )

        db.add(borrower)
        db.commit()
        db.refresh(borrower)

        logger.info(f"Created borrower {borrower_id} ({name_full}) - Role: {role}")
        return borrower
    except Exception:
        db.rollback()
        raise


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
    try:
        borrower = _get_borrower_or_raise(db, borrower_id)

        class_id_changed = class_id is not _UNSET

        # Update borrower_id if provided
        if new_borrower_id is not None and new_borrower_id != borrower_id:
            # Validate ID format against system settings
            settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
            validate_borrower_id(new_borrower_id, settings)

            # Check for duplicate borrower_id
            existing = db.query(Borrower).filter(Borrower.borrower_id == new_borrower_id).first()
            if existing:
                raise DuplicateError(f"Borrower ID '{new_borrower_id}' already exists")

            borrower.borrower_id = new_borrower_id

        # Update role if provided
        if role is not None:
            validated_role = validate_role(role)
            borrower.role = validated_role

        # Update fields if provided
        if first_name is not None:
            borrower.first_name = first_name
        if last_name is not None:
            borrower.last_name = last_name
        if first_name is not None or last_name is not None:
            borrower.full_name = full_name(borrower.first_name, borrower.last_name)

        if class_id_changed:
            # Validate class exists (unless setting to None)
            if class_id is not None:
                require_class(db, class_id)
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
        return borrower
    except Exception:
        db.rollback()
        raise


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
    try:
        borrower = _get_borrower_or_raise(db, borrower_id)

        borrower.active = True
        borrower.blocked_reason = None
        borrower.updated_at = datetime.now()

        db.commit()
        db.refresh(borrower)
        return borrower
    except Exception:
        db.rollback()
        raise


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
    try:
        borrower = _get_borrower_or_raise(db, borrower_id)

        borrower.active = False
        borrower.blocked_reason = reason
        borrower.updated_at = datetime.now()

        db.commit()
        db.refresh(borrower)
        return borrower
    except Exception:
        db.rollback()
        raise


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

    try:
        # Validate new class exists if not None
        if new_class_id is not None:
            class_obj = db.query(Class).filter(Class.id == new_class_id).first()
            if not class_obj:
                raise ClassNotFoundException(new_class_id)

        # Get all borrowers (will raise if any not found)
        borrowers = []
        for borrower_id in borrower_ids:
            borrower = _get_borrower_or_raise(db, borrower_id)
            borrowers.append(borrower)

        # Update all borrowers
        for borrower in borrowers:
            borrower.class_id = new_class_id
            borrower.updated_at = datetime.now()

        db.commit()

        logger.info(f"Bulk changed class for {total_count} borrowers to class {new_class_id}")

        return {
            "total_count": total_count,
            "successful_count": total_count,
            "failed_count": 0,
            "operation": "bulk_change_class"
        }
    except Exception:
        db.rollback()
        raise


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

    try:
        # Validate role
        validated_role = validate_role(new_role)

        # Get all borrowers (will raise if any not found)
        borrowers = []
        for borrower_id in borrower_ids:
            borrower = _get_borrower_or_raise(db, borrower_id)
            borrowers.append(borrower)

        # Update all borrowers
        for borrower in borrowers:
            borrower.role = validated_role
            borrower.updated_at = datetime.now()

        db.commit()

        logger.info(f"Bulk changed role for {total_count} borrowers to {new_role}")

        return {
            "total_count": total_count,
            "successful_count": total_count,
            "failed_count": 0,
            "operation": "bulk_change_role"
        }
    except Exception:
        db.rollback()
        raise


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

    try:
        # Fetch all borrowers in ONE query
        borrowers = db.query(Borrower).filter(
            Borrower.borrower_id.in_(borrower_ids)
        ).all()

        # Verify all borrower_ids were found
        if len(borrowers) != len(borrower_ids):
            found_ids = {b.borrower_id for b in borrowers}
            missing_ids = set(borrower_ids) - found_ids
            raise BorrowerNotFoundException(
                borrower_id=', '.join(missing_ids)
            )

        # Validate: Check for active loans in ONE batch query
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
            raise BorrowerHasActiveLoansException(
                borrower_id=borrower_with_loan.borrower_id,
                borrower_name=borrower_with_loan.full_name,
                active_loan_count=borrower_with_loan.loan_count
            )

        # Delete all borrowers
        for borrower in borrowers:
            db.delete(borrower)

        db.commit()

        logger.info(f"Bulk deleted {total_count} borrowers")

        return {
            "total_count": total_count,
            "successful_count": total_count,
            "failed_count": 0,
            "operation": "bulk_delete_borrowers"
        }
    except Exception:
        db.rollback()
        raise
