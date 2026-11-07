"""Background task manager for downloading missing book covers."""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import BackgroundTasks

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.bibliographic_record import BibliographicRecord
from ..models.system_settings import SystemSettings
from .admin_service import clean_broken_cover_references, get_records_without_covers
from .external.cover import download_cover, find_cached_cover, snapshot_cover_source_settings

logger = logging.getLogger(__name__)


class CoverDownloadManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {
            "running": False,
            "scanning": False,
            "processed": 0,
            "total": 0,
            "found": 0,
            "last_processed_isbn": None,
            "cancelled": False,
            "error": None,
        }

    def start_missing_cover_download(self, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Start a background task to download covers for records with an ISBN but no cover."""
        with self._lock:
            if self._status["running"] or self._status["scanning"]:
                return {
                    "status": "already_running",
                    "message": "Cover download is already running.",
                }
            self._status["running"] = True
            self._status["scanning"] = True
            self._status["processed"] = 0
            self._status["total"] = 0
            self._status["found"] = 0
            self._status["last_processed_isbn"] = None
            self._status["cancelled"] = False
            self._status["error"] = None

        background_tasks.add_task(self._run_missing_cover_download)
        return {"status": "started", "message": "Background cover download started."}

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the background cover download task."""
        with self._lock:
            return self._status.copy()

    def cancel(self) -> Dict[str, Any]:
        """Cancel the background cover download task."""
        with self._lock:
            if self._status["running"] or self._status["scanning"]:
                self._status["running"] = False
                self._status["cancelled"] = True
                return {"status": "cancelling", "message": "Cover download cancellation requested."}
            return {"status": "not_running", "message": "Cover download is not running."}

    def _run_missing_cover_download(self) -> None:
        """Private task execution loop."""
        covers_dir = (
            Path(settings.covers_dir_path) if settings.covers_dir_path else Path("data/covers")
        )
        to_download = []

        db = SessionLocal()
        source_settings = None
        delay_seconds = 60
        try:
            system_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
            source_settings = snapshot_cover_source_settings(system_settings)
            if system_settings is not None:
                delay_seconds = system_settings.cover_download_delay_seconds

            # Clear stale database references so this action can be used to
            # retry covers whose files were deleted.
            clean_broken_cover_references(db, str(covers_dir))

            # First match any existing covers already in cache
            records = get_records_without_covers(db)

            for r in records:
                fname = find_cached_cover(r.isbn, covers_dir=covers_dir)
                if fname:
                    r.cover_image = fname
                    db.commit()
                    continue
                to_download.append((r.id, r.isbn))
        except Exception as e:
            logger.error(f"Error scanning/backfilling existing covers: {e}", exc_info=True)
            with self._lock:
                self._status["running"] = False
                self._status["scanning"] = False
                self._status["error"] = "scan_failed"
            return
        finally:
            db.close()

        total = len(to_download)
        with self._lock:
            self._status["scanning"] = False
            self._status["total"] = total
            self._status["processed"] = 0
            self._status["found"] = 0
            self._status["running"] = bool(to_download) and not self._status["cancelled"]

        try:
            for idx, (rec_id, isbn) in enumerate(to_download):
                with self._lock:
                    if not self._status["running"]:
                        break

                try:
                    fname = download_cover(
                        isbn, covers_dir=covers_dir, source_settings=source_settings
                    )
                    if fname:
                        db_update = SessionLocal()
                        try:
                            rec = (
                                db_update.query(BibliographicRecord)
                                .filter(BibliographicRecord.id == rec_id)
                                .first()
                            )
                            if rec:
                                rec.cover_image = fname
                                db_update.commit()
                                with self._lock:
                                    self._status["found"] += 1
                        finally:
                            db_update.close()
                except Exception as e:
                    logger.error(f"Error downloading cover for ISBN {isbn}: {e}")

                with self._lock:
                    self._status["processed"] = idx + 1
                    self._status["last_processed_isbn"] = isbn

                if delay_seconds > 0 and idx + 1 < total:
                    time.sleep(delay_seconds)

        except Exception as e:
            logger.error(f"Background cover download loop failed: {e}")
        finally:
            with self._lock:
                self._status["running"] = False


# Global singleton instance
cover_download_manager = CoverDownloadManager()
