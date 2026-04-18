"""
Class Service

Handles business logic for class/grade level management including:
- Creating classes
- Listing classes
- Retrieving class details
- Managing class assignments
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import NotFoundError, DuplicateError
from src.bcd_api.models.class_model import Class


def create_class(
    db: Session,
    name: str,
    homeroom_teacher: Optional[str] = None,
    notes: Optional[str] = None,
    average_age: Optional[int] = None,
) -> Class:
    """
    Create a new class.

    Args:
        db: Database session
        name: Class name (e.g., "CP-A", "CE1-B")
        homeroom_teacher: Optional homeroom teacher name
        notes: Optional notes

    Returns:
        Created Class object

    Raises:
        DuplicateError: Class name already exists
    """
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
    db.commit()
    db.refresh(class_obj)

    return class_obj


def get_class_by_id(db: Session, class_id: int) -> Class:
    """
    Retrieve a class by ID.

    Args:
        db: Database session
        class_id: Class ID

    Returns:
        Class object

    Raises:
        NotFoundError: Class not found
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        from src.bcd_api.core.exceptions import NotFoundException
        raise NotFoundException("Class", class_id)

    return class_obj


def get_class_by_name(db: Session, name: str) -> Optional[Class]:
    """
    Retrieve a class by name.

    Args:
        db: Database session
        name: Class name

    Returns:
        Class object or None if not found
    """
    return db.query(Class).filter(Class.name == name).first()


def list_classes(
    db: Session,
    limit: int = 100,
    offset: int = 0,
) -> List[Class]:
    """
    List classes with pagination.

    Args:
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of Class objects ordered by name
    """
    from sqlalchemy import case

    query = db.query(Class)

    # Sort by average_age (nulls last), then by name
    query = query.order_by(
        case((Class.average_age.is_(None), 1), else_=0),
        Class.average_age,
        Class.name,
    )

    # Apply pagination
    query = query.limit(limit).offset(offset)

    return query.all()


def update_class(
    db: Session,
    class_id: int,
    name: Optional[str] = None,
    homeroom_teacher: Optional[str] = None,
    notes: Optional[str] = None,
    average_age: Optional[int] = None,
) -> Class:
    """
    Update class information.

    Args:
        db: Database session
        class_id: Class ID
        name: Optional new name
        homeroom_teacher: Optional new homeroom teacher
        notes: Optional new notes

    Returns:
        Updated Class object

    Raises:
        NotFoundError: Class not found
        DuplicateError: Class name already exists
    """
    class_obj = get_class_by_id(db, class_id)

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

    db.commit()
    db.refresh(class_obj)

    return class_obj


def delete_class(db: Session, class_id: int) -> None:
    """
    Delete a class.

    Args:
        db: Database session
        class_id: Class ID

    Raises:
        NotFoundError: Class not found
    """
    class_obj = get_class_by_id(db, class_id)

    db.delete(class_obj)
    db.commit()


def delete_class_with_unassignment(db: Session, class_id: int) -> None:
    """
    Delete a class and unassign all borrowers from it.

    This method:
    1. Verifies the class exists
    2. Unassigns all borrowers from the class (sets class_id to NULL)
    3. Deletes the class

    Args:
        db: Database session
        class_id: Class ID

    Raises:
        ClassNotFoundException: Class not found
    """
    from src.bcd_api.core.exceptions import ClassNotFoundException
    from src.bcd_api.models.borrower import Borrower

    # Verify class exists
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise ClassNotFoundException(class_id)

    # Unassign all borrowers from this class
    db.query(Borrower).filter(Borrower.class_id == class_id).update(
        {"class_id": None}, synchronize_session=False
    )

    # Reset student count to 0
    class_obj.student_count = 0

    # Delete the class
    db.delete(class_obj)
    db.commit()


def update_class_student_count(db: Session, class_id: int, delta: int) -> None:
    """
    Update the student count for a class.

    This is a helper function called by borrower_service when students
    are assigned/unassigned from classes.

    Args:
        db: Database session
        class_id: Class ID (or None to skip)
        delta: Change in student count (+1 for assignment, -1 for unassignment)
    """
    if class_id is None:
        return

    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if class_obj:
        class_obj.student_count = max(0, class_obj.student_count + delta)
        class_obj.updated_at = datetime.now()
        db.commit()
