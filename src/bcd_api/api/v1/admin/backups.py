"""Database backup administration endpoints."""

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ....core.deps import get_db

router = APIRouter()


def _service():
    """Resolve the service through the compatibility package namespace.

    Keeping this lookup lazy preserves the historic ``admin.backup_service``
    patch point used by API consumers and tests.
    """
    from . import backup_service

    return backup_service


@router.post("/backup")
def create_backup_endpoint(db: Session = Depends(get_db)):
    """Create a backup of the database."""
    backup_service = _service()
    try:
        db.close()
        backup_metadata = backup_service.create_backup()
        return {
            "success": True,
            "backup": backup_metadata.to_dict(),
            "message": f"Backup created successfully: {backup_metadata.filename}",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(exc)}")


@router.get("/backups")
def list_backups_endpoint():
    """List all available database backups with metadata."""
    backup_service = _service()
    try:
        backups = backup_service.list_backups()
        return {
            "success": True,
            "count": len(backups),
            "backups": [backup.to_dict() for backup in backups],
            "database_info": backup_service.get_database_size(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(exc)}")


@router.post("/restore")
def restore_backup_endpoint(
    backup_file: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
):
    """Restore the database from a backup after explicit confirmation."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Restore operation requires explicit confirmation (confirm=true)",
        )

    backup_service = _service()
    try:
        db.close()
        success = backup_service.restore_backup(backup_file)
        return {
            "success": success,
            "message": "Database restored successfully",
            "restored_from": backup_file,
            "warning": "A safety backup was created in ./backups/pre_restore/",
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(exc)}")


@router.get("/backups/{filename}/download")
def download_backup_endpoint(filename: str):
    """Download a specific backup file."""
    backup_service = _service()
    try:
        backup_dir = backup_service._get_backups_dir()
        safe_filename = Path(filename).name
        backup_path = (backup_dir / safe_filename).resolve()

        if not backup_path.exists() or not str(backup_path).startswith(str(backup_dir.resolve())):
            raise HTTPException(status_code=404, detail=f"Backup file not found: {filename}")

        return FileResponse(
            path=backup_path,
            media_type="application/x-sqlite3",
            filename=safe_filename,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(exc)}")


@router.post("/backups/import")
async def import_backup_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and import/restore a database backup file."""
    backup_service = _service()
    try:
        backup_dir = backup_service._get_backups_dir()
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_filepath = backup_dir / f"imported_backup_{timestamp}.db"

        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not backup_service.verify_backup(str(temp_filepath)):
            if temp_filepath.exists():
                temp_filepath.unlink()
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid SQLite database or integrity check failed.",
            )

        db.close()
        success = backup_service.restore_backup(str(temp_filepath))
        return {
            "success": success,
            "message": "Database successfully imported and restored.",
            "backup_file": str(temp_filepath),
            "warning": "A safety backup of the previous database was created in ./backups/pre_restore/",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database import failed: {str(exc)}")


@router.delete("/backups/cleanup")
def cleanup_old_backups_endpoint(keep_days: int = 30):
    """Delete backups older than the specified number of days."""
    backup_service = _service()
    try:
        deleted_count = backup_service.cleanup_old_backups(keep_days=keep_days)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "keep_days": keep_days,
            "message": f"Deleted {deleted_count} backup(s) older than {keep_days} days",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(exc)}")


@router.get("/backups/verify/{filename}")
def verify_backup_endpoint(filename: str):
    """Verify backup file integrity."""
    backup_service = _service()
    try:
        backup_dir = backup_service._get_backups_dir()
        backup_path = backup_dir / filename
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail=f"Backup file not found: {filename}")

        is_valid = backup_service.verify_backup(str(backup_path))
        return {
            "success": True,
            "valid": is_valid,
            "filename": filename,
            "message": "Backup is valid" if is_valid else "Backup verification failed",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(exc)}")
