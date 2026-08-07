"""Classes Queries - Read-only queries for class/grade level management.

No mutations, commits, or rollbacks.
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import case

from ...core.exceptions import NotFoundException
from ...models.class_model import Class


def get_class_by_id(db: Session, class_id: int) -> Class:
    """Retrieve a class by ID.

    Args:
        db: Database session
        class_id: Class ID

    Returns:
        Class object

    Raises:
        NotFoundException: Class not found
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise NotFoundException("Class", class_id)
    return class_obj


def get_class_by_name(db: Session, name: str) -> Optional[Class]:
    """Retrieve a class by name.

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
    """List classes with pagination.

    Args:
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of Class objects ordered by name
    """
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
