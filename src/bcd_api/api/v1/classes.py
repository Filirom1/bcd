"""
Classes API Endpoints

Provides REST API endpoints for class/grade level management.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ...core.deps import get_db
from ...schemas.class_schema import (
    ClassCreate,
    ClassResponse,
    ClassUpdate,
)
from ...services import class_service


router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    request: ClassCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new class.

    **Errors**:
    - 409: Class name already exists
    """
    class_obj = class_service.create_class(
        db=db,
        name=request.name,
        homeroom_teacher=request.homeroom_teacher,
        notes=request.notes,
        average_age=request.average_age,
    )
    return class_obj


@router.get("/{class_id}", response_model=ClassResponse)
def get_class(
    class_id: int,
    db: Session = Depends(get_db)
):
    """
    Get class details by ID.

    **Errors**:
    - 404: Class not found
    """
    class_obj = class_service.get_class_by_id(db, class_id)
    return class_obj


@router.get("", response_model=List[ClassResponse])
def list_classes(
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    List classes with pagination.

    Results are ordered by class name.

    **Query Parameters**:
    - limit: Maximum number of results (1-500, default 100)
    - offset: Pagination offset (default 0)
    """
    classes = class_service.list_classes(
        db=db,
        limit=limit,
        offset=offset,
    )
    return classes


@router.patch("/{class_id}", response_model=ClassResponse)
def update_class(
    class_id: int,
    request: ClassUpdate,
    db: Session = Depends(get_db)
):
    """
    Update class information.

    **Errors**:
    - 404: Class not found
    - 409: New name already exists
    """
    class_obj = class_service.update_class(
        db=db,
        class_id=class_id,
        name=request.name,
        homeroom_teacher=request.homeroom_teacher,
        notes=request.notes,
        average_age=request.average_age,
    )
    return class_obj


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a class and unassign all borrowers from it.

    This endpoint will:
    1. Set class_id to NULL for all borrowers assigned to this class
    2. Delete the class

    **Errors**:
    - 404: Class not found
    """
    class_service.delete_class_with_unassignment(db, class_id)
    return None
