"""
Admin API Endpoints

REST API for system administration.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
from pydantic import BaseModel
import shutil
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

from ...core.deps import get_db
from ...core import mdns as mdns_module
from ...core.exceptions import (
    NotFoundError,
    BorrowerNotFoundException,
    ClassNotFoundException,
    ValidationError,
)
from ...core.config import settings as app_settings
from ...services import settings_service, backup_service, archive_service, borrower_service, catalog_service, inventory_service
from ...schemas.system_settings import SystemSettingsResponse
from ...schemas.admin import (
    BulkChangeClassRequest,
    BulkChangeRoleRequest,
    BulkDeleteRequest,
    BulkOperationResult,
    BulkEditRecordsRequest,
    BulkDeleteRecordsRequest,
)
from ...schemas.inventory import (
    OrphanRecordsResponse,
    OrphanDeleteResponse
)

router = APIRouter(prefix="/admin", tags=["admin"])


class SettingsUpdate(BaseModel):
    """Schema for updating settings."""
    updates: Dict[str, Any]


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db)
):
    """
    Get current system settings.

    Args:
        db: Database session

    Returns:
        System settings (JSON)

    Raises:
        404: Settings not found
    """
    settings = settings_service.get_settings(db)
    return settings


@router.put("/settings")
async def update_settings(
    settings_update: SettingsUpdate,
    db: Session = Depends(get_db),
):
    """
    Update system settings.

    Args:
        settings_update: Settings update data (JSON)
        db: Database session

    Returns:
        Updated system settings (JSON)

    Raises:
        404: Settings not found
    """
    settings = settings_service.update_settings(db, settings_update.updates)

    # Restart mDNS when library_code changes (non-fatal if it fails)
    if "library_code" in settings_update.updates:
        try:
            new_library_code = getattr(settings, "library_code", None)
            port = mdns_module.get_server_port(app_settings.api_port)
            await mdns_module.restart_mdns(new_library_code, port)
        except Exception as exc:
            logger.warning(f"mDNS restart after settings update failed (non-fatal): {exc}")

    return settings


@router.post("/settings/reset", response_model=SystemSettingsResponse)
def reset_settings(db: Session = Depends(get_db)):
    """
    Reset all settings to default values.

    Args:
        db: Database session

    Returns:
        Reset system settings
    """
    settings = settings_service.reset_to_defaults(db)
    return settings


@router.post("/backup")
def create_backup_endpoint(db: Session = Depends(get_db)):
    """
    Create a backup of the database.

    Uses the comprehensive backup service (FR-048).

    Args:
        db: Database session

    Returns:
        Backup file information with metadata

    Raises:
        500: Backup creation failed
    """
    try:
        # Close session to ensure consistent backup
        db.close()

        # Create backup using backup service
        backup_metadata = backup_service.create_backup()

        return {
            "success": True,
            "backup": backup_metadata.to_dict(),
            "message": f"Backup created successfully: {backup_metadata.filename}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Backup failed: {str(e)}"
        )


@router.get("/backups")
def list_backups_endpoint():
    """
    List all available database backups with metadata.

    Returns backups sorted by creation time (newest first).

    Returns:
        List of backup metadata dictionaries
    """
    try:
        backups = backup_service.list_backups()

        return {
            "success": True,
            "count": len(backups),
            "backups": [b.to_dict() for b in backups],
            "database_info": backup_service.get_database_size()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list backups: {str(e)}"
        )


@router.post("/restore")
def restore_backup_endpoint(
    backup_file: str,
    confirm: bool = False,
    db: Session = Depends(get_db)
):
    """
    Restore database from a backup file.

    DANGEROUS OPERATION: This will overwrite the current database!
    Requires explicit confirmation parameter.

    Args:
        backup_file: Path to the backup file to restore
        confirm: Must be True to proceed with restore
        db: Database session

    Returns:
        Restore status and safety backup location

    Raises:
        400: Missing confirmation or invalid backup file
        404: Backup file not found
        500: Restore operation failed
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Restore operation requires explicit confirmation (confirm=true)"
        )

    try:
        # Close session before restore
        db.close()

        # Perform restore (creates safety backup automatically)
        success = backup_service.restore_backup(backup_file)

        return {
            "success": success,
            "message": "Database restored successfully",
            "restored_from": backup_file,
            "warning": "A safety backup was created in ./backups/pre_restore/"
        }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Restore failed: {str(e)}"
        )


@router.delete("/backups/cleanup")
def cleanup_old_backups_endpoint(keep_days: int = 30):
    """
    Delete backups older than specified days.

    Args:
        keep_days: Number of days to keep backups (default: 30)

    Returns:
        Count of deleted backups
    """
    try:
        deleted_count = backup_service.cleanup_old_backups(keep_days=keep_days)

        return {
            "success": True,
            "deleted_count": deleted_count,
            "keep_days": keep_days,
            "message": f"Deleted {deleted_count} backup(s) older than {keep_days} days"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.get("/backups/verify/{filename}")
def verify_backup_endpoint(filename: str):
    """
    Verify backup file integrity.

    Args:
        filename: Name of backup file to verify (in ./backups/)

    Returns:
        Verification status
    """
    try:
        backup_path = Path("./backups") / filename

        if not backup_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Backup file not found: {filename}"
            )

        is_valid = backup_service.verify_backup(str(backup_path))

        return {
            "success": True,
            "valid": is_valid,
            "filename": filename,
            "message": "Backup is valid" if is_valid else "Backup verification failed"
        }

    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )


@router.get("/archive/stats")
def get_archive_stats(db: Session = Depends(get_db)):
    """
    Get statistics about archived circulation transactions.

    Args:
        db: Database session

    Returns:
        Archive statistics (count, date ranges, size)
    """
    try:
        stats = archive_service.get_archive_stats(db)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get archive stats: {str(e)}"
        )


@router.post("/archive")
def archive_transactions(
    older_than_years: int = 5,
    dry_run: bool = False,
    db: Session = Depends(get_db)
):
    """
    Archive old circulation transactions to prevent database bloat.

    Args:
        older_than_years: Archive transactions older than this many years (default: 5)
        dry_run: If True, only return count without actually archiving
        db: Database session

    Returns:
        Archive operation results (count, date range, size reduction)

    Raises:
        400: Invalid parameters
        500: Archive operation failed
    """
    try:
        result = archive_service.archive_old_transactions(
            db=db,
            older_than_years=older_than_years,
            dry_run=dry_run
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Archive operation failed: {str(e)}"
        )


@router.get("/archive/transactions")
def get_archived_transactions(
    borrower_id: int = None,
    item_id: int = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Query archived circulation transactions.

    Args:
        borrower_id: Filter by borrower ID (optional)
        item_id: Filter by item ID (optional)
        limit: Maximum number of records (default: 100)
        offset: Number of records to skip (default: 0)
        db: Database session

    Returns:
        List of archived transactions
    """
    try:
        transactions = archive_service.get_archived_transactions(
            db=db,
            borrower_id=borrower_id,
            item_id=item_id,
            limit=limit,
            offset=offset
        )
        return {
            "transactions": transactions,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query archived transactions: {str(e)}"
        )


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Check system health and database connectivity.

    Args:
        db: Database session

    Returns:
        Health status information
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))

        # Get database statistics
        from ...models.borrower import Borrower
        from ...models.bibliographic_record import BiblographicRecord
        from ...models.item import Item
        from ...models.circulation import CirculationTransaction

        borrower_count = db.query(Borrower).count()
        biblio_count = db.query(BiblographicRecord).count()
        item_count = db.query(Item).count()
        circulation_count = db.query(CirculationTransaction).count()

        return {
            "status": "healthy",
            "database": "connected",
            "counts": {
                "borrowers": borrower_count,
                "bibliographic_records": biblio_count,
                "items": item_count,
                "circulations": circulation_count,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


# Bulk borrower operations

@router.post("/borrowers/bulk-change-class", response_model=BulkOperationResult)
def bulk_change_class_endpoint(
    request: BulkChangeClassRequest,
    db: Session = Depends(get_db)
):
    """
    Change class for multiple borrowers atomically.

    All borrowers will be updated to the new class, or none will be updated
    if any error occurs (atomic operation with rollback).

    Args:
        request: Bulk change class request
        db: Database session

    Returns:
        Operation results (total_count, successful_count, failed_count)

    Raises:
        404: Class or borrower not found
        400: Validation error
    """
    result = borrower_service.bulk_change_class(
        db=db,
        borrower_ids=request.borrower_ids,
        new_class_id=request.target_class_id
    )
    return BulkOperationResult(**result)


@router.post("/borrowers/bulk-change-role", response_model=BulkOperationResult)
def bulk_change_role_endpoint(
    request: BulkChangeRoleRequest,
    db: Session = Depends(get_db)
):
    """
    Change role for multiple borrowers atomically.

    All borrowers will be updated to the new role, or none will be updated
    if any error occurs (atomic operation with rollback).

    Args:
        request: Bulk change role request
        db: Database session

    Returns:
        Operation results (total_count, successful_count, failed_count)

    Raises:
        404: Borrower not found
        422: Invalid role
        400: Validation error
    """
    result = borrower_service.bulk_change_role(
        db=db,
        borrower_ids=request.borrower_ids,
        new_role=request.target_role
    )
    return BulkOperationResult(**result)


@router.post("/borrowers/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_borrowers_endpoint(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Delete multiple borrowers atomically.

    All borrowers and their circulation history will be deleted via CASCADE,
    or none will be deleted if any error occurs (atomic operation with rollback).

    Args:
        request: Bulk delete request
        db: Database session

    Returns:
        Operation results (total_count, successful_count, failed_count)

    Raises:
        404: Borrower not found
        400: Validation error
    """
    result = borrower_service.bulk_delete_borrowers(
        db=db,
        borrower_ids=request.borrower_ids
    )
    return BulkOperationResult(**result)


# === US5: Bulk Catalog Operations ===


@router.post("/catalog/bulk-edit", response_model=BulkOperationResult)
def bulk_edit_records_endpoint(
    request: BulkEditRecordsRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk edit bibliographic records (US5).

    Updates common fields for multiple records in a single atomic transaction.
    Null values mean "no change" to that field.

    Args:
        request: Bulk edit records request
        db: Database session

    Returns:
        Operation results (total_count, successful_count, failed_count)

    Raises:
        404: Record not found
        400: Validation error
    """
    try:
        result = catalog_service.bulk_edit_records(
            db=db,
            record_ids=request.record_ids,
            genre=request.genre,
            target_audience=request.target_audience,
            language=request.language,
            medium_type=request.medium_type
        )
        return BulkOperationResult(**result)

    except Exception as e:
        logger.error(f"Bulk edit records failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk edit records failed: {str(e)}")


@router.post("/catalog/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_records_endpoint(
    request: BulkDeleteRecordsRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk delete bibliographic records (US5).

    Deletes multiple records in a single atomic transaction.
    CASCADE delete removes associated items and circulation history.

    Args:
        request: Bulk delete records request
        db: Database session

    Returns:
        Operation results (total_count, successful_count, failed_count)

    Raises:
        404: Record not found
        400: Validation error
    """
    result = catalog_service.bulk_delete_records(
        db=db,
        record_ids=request.record_ids
    )
    return BulkOperationResult(**result)


@router.get("/catalog/orphan-records", response_model=OrphanRecordsResponse)
def get_orphan_records_endpoint(
    db: Session = Depends(get_db)
):
    """
    Get count and list of orphan bibliographic records (total_items = 0).

    **Returns:**
    - 200: Orphan records count and list (id, title, isbn)

    **Usage:** Admin dropdown in inventory page
    """
    try:
        result = inventory_service.get_orphan_records(db)
        return OrphanRecordsResponse(**result)

    except Exception as e:
        logger.error(f"Error getting orphan records: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get orphan records: {str(e)}")


@router.delete("/catalog/orphan-records", response_model=OrphanDeleteResponse)
def delete_orphan_records_endpoint(
    db: Session = Depends(get_db)
):
    """
    Delete all bibliographic records with total_items = 0.

    **Returns:**
    - 200: Number of records deleted

    **Usage:** Admin dropdown in inventory page (after confirmation)
    """
    try:
        result = inventory_service.delete_orphan_records(db)
        return OrphanDeleteResponse(**result)

    except Exception as e:
        logger.error(f"Error deleting orphan records: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete orphan records: {str(e)}")


# Add support for POST /admin/borrowers/bulk-edit to match frontend expectations
@router.post("/borrowers/bulk-edit", response_model=BulkOperationResult)
def bulk_edit_borrowers_endpoint(
    operation: str,
    borrower_ids: list[str],
    target_class_id: int = None,
    target_role: str = None,
    db: Session = Depends(get_db)
):
    """
    Unified bulk edit endpoint for borrowers (US3).

    Supports multiple operations via 'operation' field:
    - 'change_class': Change class for multiple borrowers
    - 'change_role': Change role for multiple borrowers

    Args:
        operation: Operation type ('change_class' or 'change_role')
        borrower_ids: List of borrower IDs
        target_class_id: Target class ID (for change_class operation)
        target_role: Target role (for change_role operation)
        db: Database session

    Returns:
        Operation results

    Raises:
        400: Invalid operation or missing parameters
    """
    try:
        if operation == 'change_class':
            if target_class_id is None:
                raise ValidationError("target_class_id required for change_class operation")
            result = borrower_service.bulk_change_class(
                db=db,
                borrower_ids=borrower_ids,
                new_class_id=target_class_id
            )
        elif operation == 'change_role':
            if target_role is None:
                raise ValidationError("target_role required for change_role operation")
            result = borrower_service.bulk_change_role(
                db=db,
                borrower_ids=borrower_ids,
                new_role=target_role
            )
        else:
            raise ValidationError(f"Unknown operation: {operation}")

        return BulkOperationResult(**result)

    except (ClassNotFoundException, BorrowerNotFoundException, NotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bulk edit borrowers failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk edit borrowers failed: {str(e)}")


@router.post("/covers/backfill")
def backfill_covers(db: Session = Depends(get_db)):
    """Associate existing cover files with bibliographic records.

    Scans records that have an ISBN but no cover_image set, checks if a
    matching .jpg exists in data/covers/, and updates the column.

    Returns:
        {"updated": N, "scanned": M}
    """
    from ...models.bibliographic_record import BiblographicRecord

    covers_dir = Path("data/covers")
    records = db.query(BiblographicRecord).filter(
        BiblographicRecord.cover_image == None,
        BiblographicRecord.isbn != None,
        BiblographicRecord.isbn != "",
    ).all()

    updated = 0
    for record in records:
        normalized = record.isbn.replace("-", "").replace(".", "").replace(" ", "")
        if (covers_dir / f"{normalized}.jpg").exists():
            record.cover_image = f"{normalized}.jpg"
            updated += 1

    if updated:
        db.commit()

    logger.info(f"Cover backfill: {updated}/{len(records)} records updated")
    return {"updated": updated, "scanned": len(records)}


@router.post("/data-maintenance/set-acquisition-dates")
def set_acquisition_dates_from_publication_year(db: Session = Depends(get_db)):
    """Set acquisition_date to publication_year for items missing acquisition_date.

    For items where:
    - acquisition_date is NULL
    - bibliographic_record.publication_year is not NULL

    Sets acquisition_date to January 1st of the publication year.

    Returns:
        {"updated_count": N}
    """
    from ...models.item import Item
    from ...models.bibliographic_record import BiblographicRecord
    from datetime import date

    # Find items without acquisition_date that have a publication_year
    items = (
        db.query(Item)
        .join(BiblographicRecord)
        .filter(
            Item.acquisition_date == None,
            BiblographicRecord.publication_year != None,
        )
        .all()
    )

    updated_count = 0
    for item in items:
        year = item.bibliographic_record.publication_year
        if year and 1000 <= year <= 2100:
            item.acquisition_date = date(year, 1, 1)
            updated_count += 1

    if updated_count:
        db.commit()

    logger.info(f"Acquisition date maintenance: {updated_count} items updated")
    return {"updated_count": updated_count}
