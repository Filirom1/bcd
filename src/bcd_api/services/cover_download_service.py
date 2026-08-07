"""Background task manager for downloading missing book covers."""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks

from ..core.database import SessionLocal
from ..models.bibliographic_record import BiblographicRecord
from .admin_service import get_records_without_covers, backfill_covers_logic
from .external.cover import download_cover, find_cached_cover

logger = logging.getLogger(__name__)


class CoverDownloadManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {
            "running": False,
            "processed": 0,
            "total": 0,
            "found": 0,
            "last_processed_isbn": None,
        }

    def start_missing_cover_download(self, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Start a background task to download covers for records with an ISBN but no cover."""
        with self._lock:
            if self._status["running"]:
                return {"status": "already_running", "message": "Cover download is already running."}
            self._status["running"] = True
            self._status["processed"] = 0
            self._status["total"] = 0
            self._status["found"] = 0
            self._status["last_processed_isbn"] = None

        background_tasks.add_task(self._run_missing_cover_download)
        return {"status": "started", "message": "Background cover download started."}

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the background cover download task."""
        with self._lock:
            return self._status.copy()

    def cancel(self) -> Dict[str, Any]:
        """Cancel the background cover download task."""
        with self._lock:
            if self._status["running"]:
                self._status["running"] = False
                return {"status": "cancelling", "message": "Cover download cancellation requested."}
            return {"status": "not_running", "message": "Cover download is not running."}

    def _run_missing_cover_download(self) -> None:
        """Private task execution loop."""
        covers_dir = Path("data/covers")
        to_download = []

        db = SessionLocal()
        try:
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
            logger.error(f"Error scanning/backfilling existing covers: {e}")
        finally:
            db.close()

        total = len(to_download)
        with self._lock:
            self._status["total"] = total
            self._status["processed"] = 0
            self._status["found"] = 0
            self._status["running"] = True

        try:
            for idx, (rec_id, isbn) in enumerate(to_download):
                with self._lock:
                    if not self._status["running"]:
                        break

                try:
                    fname = download_cover(isbn, covers_dir=covers_dir)
                    if fname:
                        db_update = SessionLocal()
                        try:
                            rec = db_update.query(BiblographicRecord).filter(BiblographicRecord.id == rec_id).first()
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

                # Sleep to avoid rate limits (1 request per second typically, but 60.0s for bulk)
                time.sleep(60.0)

        except Exception as e:
            logger.error(f"Background cover download loop failed: {e}")
        finally:
            with self._lock:
                self._status["running"] = False


# Global singleton instance
cover_download_manager = CoverDownloadManager()
