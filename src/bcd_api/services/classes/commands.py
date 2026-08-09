"""Classes Commands - Creating, updating, and deleting classes.

Each public command wraps its mutations inside an atomic transaction (try-commit-rollback).
Each command delegates to an `_in_transaction` variant for parent-controlled mutations.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ...core.exceptions import (
    DuplicateError,
    NotFoundException,
    ClassNotFoundException,
)
from ...models.class_model import Class
from ...models.borrower import Borrower


def create_class_in_transaction(
    db: Session,
    name: str,
    homeroom_teacher: Optional[str] = None,
    notes: Optional[str] = None,
    average_age: Optional[int] = None,
) -> Class:
    """Create a new class (in-transaction helper, no commit)."""
    # Check for duplicate class name
    existing = db.query(Class).filter(Class.name == name).first()
    if existing:
        raise DuplicateError(f"Class '{name}' already exists")

    # Create class
    class_obj = Class(
        name=name,
        homeroom_teacher=homeroom_teacher,
        notes=notes,
        average_age=average_age,
    )

    db.add(class_obj)
    return class_obj


def create_class(
    db: Session,
    name: str,
    homeroom_teacher: Optional[str] = None,
    notes: Optional[str] = None,
    average_age: Optional[int] = None,
) -> Class:
    """Create a new class (autonomous, handles commit)."""
    try:
        class_obj = create_class_in_transaction(
            db, name, homeroom_teacher, notes, average_age
        )
        db.flush()
        db.commit()
        db.refresh(class_obj)
        return class_obj
    except Exception:
        db.rollback()
        raise


def update_class_in_transaction(
    db: Session,
    class_id: int,
    name: Optional[str] = None,
    homeroom_teacher: Optional[str] = None,
    notes: Optional[str] = None,
    average_age: Optional[int] = None,
) -> Class:
    """Update class information (in-transaction helper, no commit)."""
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise NotFoundException("Class", class_id)

    # Update fields if provided
    if name is not None:
        # Check for duplicate name
        existing = (
            db.query(Class)
            .filter(Class.name == name, Class.id != class_id)
            .first()
        )
        if existing:
            raise DuplicateError(f"Class '{name}' already exists")
        class_obj.name = name

    if homeroom_teacher is not None:
        class_obj.homeroom_teacher = homeroom_teacher
    if notes is not None:
        class_obj.notes = notes
    if average_age is not None:
        class_obj.average_age = average_age

    class_obj.updated_at = datetime.now()
    return class_obj


def update_class(
    db: Session,
    class_id: int,
    name: Optional[str] = None,
    homeroom_teacher: Optional[str] = None,
    notes: Optional[str] = None,
    average_age: Optional[int] = None,
) -> Class:
    """Update class information (autonomous, handles commit)."""
    try:
        class_obj = update_class_in_transaction(
            db, class_id, name, homeroom_teacher, notes, average_age
        )
        db.flush()
        db.commit()
        db.refresh(class_obj)
        return class_obj
    except Exception:
        db.rollback()
        raise


def delete_class_in_transaction(db: Session, class_id: int) -> None:
    """Delete a class (in-transaction helper, no commit)."""
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise NotFoundException("Class", class_id)

    db.delete(class_obj)


def delete_class(db: Session, class_id: int) -> None:
    """Delete a class (autonomous, handles commit)."""
    try:
        delete_class_in_transaction(db, class_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_class_with_unassignment_in_transaction(db: Session, class_id: int) -> None:
    """Delete a class and unassign all borrowers from it (in-transaction helper, no commit)."""
    # Verify class exists
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise ClassNotFoundException(class_id)

    # Unassign all borrowers from this class
    db.query(Borrower).filter(Borrower.class_id == class_id).update(
        {"class_id": None}, synchronize_session=False
    )

    # Delete the class
    db.delete(class_obj)


def delete_class_with_unassignment(db: Session, class_id: int) -> None:
    """Delete a class and unassign all borrowers from it (autonomous, handles commit)."""
    try:
        delete_class_with_unassignment_in_transaction(db, class_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
