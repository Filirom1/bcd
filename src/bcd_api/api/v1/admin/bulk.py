"""Bulk borrower, catalog, and inventory administration endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ....core.deps import get_db
from ....core.exceptions import (
    BorrowerNotFoundException,
    ClassNotFoundException,
    NotFoundError,
    ValidationError,
)
from ....schemas.admin import (
    BulkChangeClassRequest,
    BulkChangeRoleRequest,
    BulkDeleteRecordsRequest,
    BulkDeleteRequest,
    BulkEditRecordsRequest,
    BulkOperationResult,
)
from ....schemas.inventory import OrphanDeleteResponse, OrphanRecordsResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _services():
    from . import borrower_service, catalog_service, inventory_service

    return borrower_service, catalog_service, inventory_service


@router.post("/borrowers/bulk-change-class", response_model=BulkOperationResult)
def bulk_change_class_endpoint(
    request: BulkChangeClassRequest,
    db: Session = Depends(get_db),
):
    """Change class for multiple borrowers atomically."""
    borrower_service, _, _ = _services()
    result = borrower_service.bulk_change_class(
        db=db,
        borrower_ids=request.borrower_ids,
        new_class_id=request.target_class_id,
    )
    return BulkOperationResult(**result)


@router.post("/borrowers/bulk-change-role", response_model=BulkOperationResult)
def bulk_change_role_endpoint(
    request: BulkChangeRoleRequest,
    db: Session = Depends(get_db),
):
    """Change role for multiple borrowers atomically."""
    borrower_service, _, _ = _services()
    result = borrower_service.bulk_change_role(
        db=db,
        borrower_ids=request.borrower_ids,
        new_role=request.target_role,
    )
    return BulkOperationResult(**result)


@router.post("/borrowers/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_borrowers_endpoint(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
):
    """Delete multiple borrowers atomically."""
    borrower_service, _, _ = _services()
    result = borrower_service.bulk_delete_borrowers(db=db, borrower_ids=request.borrower_ids)
    return BulkOperationResult(**result)


@router.post("/catalog/bulk-edit", response_model=BulkOperationResult)
def bulk_edit_records_endpoint(
    request: BulkEditRecordsRequest,
    db: Session = Depends(get_db),
):
    """Bulk edit bibliographic records."""
    _, catalog_service, _ = _services()
    try:
        result = catalog_service.bulk_edit_records(
            db=db,
            record_ids=request.record_ids,
            level=request.level,
            target_audience=request.target_audience,
            language=request.language,
            medium_type=request.medium_type,
            publisher=request.publisher,
            collection=request.collection,
            binding_type=request.binding_type,
        )
        return BulkOperationResult(**result)
    except Exception as exc:
        logger.error("Bulk edit records failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Bulk edit records failed: {str(exc)}")


@router.post("/catalog/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_records_endpoint(
    request: BulkDeleteRecordsRequest,
    db: Session = Depends(get_db),
):
    """Bulk delete bibliographic records."""
    _, catalog_service, _ = _services()
    result = catalog_service.bulk_delete_records(db=db, record_ids=request.record_ids)
    return BulkOperationResult(**result)


@router.get("/catalog/orphan-records", response_model=OrphanRecordsResponse)
def get_orphan_records_endpoint(db: Session = Depends(get_db)):
    """Get bibliographic records that have no items."""
    _, _, inventory_service = _services()
    try:
        return OrphanRecordsResponse(**inventory_service.get_orphan_records(db))
    except Exception as exc:
        logger.error("Error getting orphan records: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get orphan records: {str(exc)}")


@router.delete("/catalog/orphan-records", response_model=OrphanDeleteResponse)
def delete_orphan_records_endpoint(db: Session = Depends(get_db)):
    """Delete all bibliographic records that have no items."""
    _, _, inventory_service = _services()
    try:
        return OrphanDeleteResponse(**inventory_service.delete_orphan_records(db))
    except Exception as exc:
        logger.error("Error deleting orphan records: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete orphan records: {str(exc)}")


@router.post("/borrowers/bulk-edit", response_model=BulkOperationResult)
def bulk_edit_borrowers_endpoint(
    operation: str,
    borrower_ids: list[str],
    target_class_id: int = None,
    target_role: str = None,
    db: Session = Depends(get_db),
):
    """Apply a class or role change to multiple borrowers."""
    borrower_service, _, _ = _services()
    try:
        if operation == "change_class":
            if target_class_id is None:
                raise ValidationError("target_class_id required for change_class operation")
            result = borrower_service.bulk_change_class(
                db=db, borrower_ids=borrower_ids, new_class_id=target_class_id
            )
        elif operation == "change_role":
            if target_role is None:
                raise ValidationError("target_role required for change_role operation")
            result = borrower_service.bulk_change_role(
                db=db, borrower_ids=borrower_ids, new_role=target_role
            )
        else:
            raise ValidationError(f"Unknown operation: {operation}")

        return BulkOperationResult(**result)
    except (ClassNotFoundException, BorrowerNotFoundException, NotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Bulk edit borrowers failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Bulk edit borrowers failed: {str(exc)}")
