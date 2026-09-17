"""Book-cover administration endpoints."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ....core.deps import get_db
from ....services.cover_download_service import cover_download_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Preserve the shared manager state and public compatibility names.
_download_lock = cover_download_manager._lock
_download_status = cover_download_manager._status
_download_missing_covers_task = cover_download_manager._run_missing_cover_download


@router.post("/covers/backfill")
def backfill_covers(db: Session = Depends(get_db)):
    """Associate existing cached cover files with bibliographic records."""
    from . import admin_service, app_settings

    result = admin_service.backfill_covers_logic(db, app_settings.covers_dir_path)
    logger.info("Cover backfill: %s/%s records updated", result["updated"], result["scanned"])
    return result


@router.post("/covers/download-missing")
def start_download_missing_covers(background_tasks: BackgroundTasks):
    """Start a background task to download missing covers."""
    return cover_download_manager.start_missing_cover_download(background_tasks)


@router.get("/covers/download-missing/status")
def get_download_missing_covers_status():
    """Get the status of the background cover download task."""
    return cover_download_manager.get_status()


@router.post("/covers/download-missing/cancel")
def cancel_download_missing_covers():
    """Cancel the background cover download task."""
    return cover_download_manager.cancel()
