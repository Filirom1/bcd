from datetime import date
from unittest.mock import MagicMock

from src.bcd_api.api.v1 import admin


def test_cover_download_status_and_cancel():
    admin._download_status.update(running=True, processed=2, total=5, found=1)
    status = admin.get_download_missing_covers_status()
    assert status["running"] is True
    assert admin.cancel_download_missing_covers()["status"] == "cancelling"
    assert admin.cancel_download_missing_covers()["status"] == "not_running"


def test_start_cover_download_schedules_task():
    admin._download_status["running"] = False
    background = MagicMock()
    result = admin.start_download_missing_covers(background)
    assert result["status"] == "started"
    background.add_task.assert_called_once_with(admin._download_missing_covers_task)
    admin._download_status["running"] = False


def test_start_cover_download_does_not_duplicate_running_task():
    admin._download_status["running"] = True
    background = MagicMock()
    result = admin.start_download_missing_covers(background)
    assert result["status"] == "already_running"
    background.add_task.assert_not_called()
    admin._download_status["running"] = False


def test_backfill_covers_updates_cached_records(monkeypatch, tmp_path):
    record = MagicMock(isbn="123", cover_image=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [record]
    monkeypatch.setattr(admin.app_settings, "covers_dir_path", str(tmp_path))
    monkeypatch.setattr("src.bcd_api.services.external.cover.find_cached_cover", lambda isbn, covers_dir: "123.jpg")
    result = admin.backfill_covers(db)
    assert result == {"updated": 1, "scanned": 1}
    assert record.cover_image == "123.jpg"
    db.commit.assert_called_once()
