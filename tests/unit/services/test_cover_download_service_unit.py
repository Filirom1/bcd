import unittest.mock as mock

from fastapi import BackgroundTasks

from src.bcd_api.services.cover_download_service import CoverDownloadManager


def test_cover_download_manager_lifecycle():
    manager = CoverDownloadManager()

    # Initial status
    status = manager.get_status()
    assert status["running"] is False

    # Start when not running
    bg_tasks = BackgroundTasks()
    res = manager.start_missing_cover_download(bg_tasks)
    assert res["status"] == "started"
    assert len(bg_tasks.tasks) == 1

    # Start when already running
    res_double = manager.start_missing_cover_download(bg_tasks)
    assert res_double["status"] == "already_running"

    # Cancel when running
    res_cancel = manager.cancel()
    assert res_cancel["status"] == "cancelling"
    assert manager.get_status()["cancelled"] is True

    # Cancel when not running
    manager._status["running"] = False
    manager._status["scanning"] = False
    res_cancel_again = manager.cancel()
    assert res_cancel_again["status"] == "not_running"


@mock.patch("src.bcd_api.services.cover_download_service.SessionLocal")
@mock.patch("src.bcd_api.services.cover_download_service.get_records_without_covers")
@mock.patch("src.bcd_api.services.cover_download_service.find_cached_cover")
@mock.patch("src.bcd_api.services.cover_download_service.download_cover")
@mock.patch("src.bcd_api.services.cover_download_service.time.sleep")  # avoid 60s sleep!
def test_run_missing_cover_download_loop(
    mock_sleep, mock_download_cover, mock_find_cached, mock_get_records, mock_session_local
):
    manager = CoverDownloadManager()

    # Create dummy records
    rec1 = mock.MagicMock()
    rec1.id = 1
    rec1.isbn = "9781234567890"
    rec1.cover_image = None

    rec2 = mock.MagicMock()
    rec2.id = 2
    rec2.isbn = "9780000000000"
    rec2.cover_image = None

    mock_get_records.return_value = [rec1, rec2]

    # rec1 will be found in cache
    mock_find_cached.side_effect = lambda isbn, covers_dir: (
        "cached.jpg" if isbn == "9781234567890" else None
    )

    # rec2 will be downloaded
    mock_download_cover.return_value = "downloaded.jpg"

    # Mock DB queries
    mock_db = mock.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_session_local.return_value = mock_db

    # Executing background loop
    manager._run_missing_cover_download()

    assert rec1.cover_image == "cached.jpg"
    mock_download_cover.assert_called_once_with(
        "9780000000000", covers_dir=mock.ANY, source_settings=mock.ANY
    )
    mock_sleep.assert_not_called()
    status = manager.get_status()
    assert status["running"] is False
    assert status["scanning"] is False
    assert status["processed"] == 1
    assert status["total"] == 1


@mock.patch("src.bcd_api.services.cover_download_service.SessionLocal")
@mock.patch("src.bcd_api.services.cover_download_service.get_records_without_covers")
@mock.patch("src.bcd_api.services.cover_download_service.find_cached_cover")
@mock.patch("src.bcd_api.services.cover_download_service.download_cover")
@mock.patch("src.bcd_api.services.cover_download_service.time.sleep")
@mock.patch("src.bcd_api.services.cover_download_service.clean_broken_cover_references")
def test_run_missing_cover_download_uses_configured_delay_between_records(
    mock_clean,
    mock_sleep,
    mock_download_cover,
    mock_find_cached,
    mock_get_records,
    mock_session_local,
):
    from types import SimpleNamespace

    manager = CoverDownloadManager()
    records = [
        mock.MagicMock(id=1, isbn="9781234567890"),
        mock.MagicMock(id=2, isbn="9780000000000"),
    ]
    mock_get_records.return_value = records
    mock_find_cached.return_value = None
    mock_download_cover.return_value = None

    mock_db = mock.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        cover_download_delay_seconds=7
    )
    mock_session_local.return_value = mock_db
    manager._status.update(running=True, scanning=True)

    manager._run_missing_cover_download()

    mock_sleep.assert_called_once_with(7)
    assert manager.get_status()["processed"] == 2


@mock.patch("src.bcd_api.services.cover_download_service.SessionLocal")
@mock.patch("src.bcd_api.services.cover_download_service.get_records_without_covers")
@mock.patch("src.bcd_api.services.cover_download_service.clean_broken_cover_references")
def test_run_missing_cover_download_reports_empty_scan(
    mock_clean, mock_get_records, mock_session_local
):
    manager = CoverDownloadManager()
    mock_get_records.return_value = []
    mock_db = mock.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_session_local.return_value = mock_db

    manager._status.update(running=True, scanning=True)
    manager._run_missing_cover_download()

    assert manager.get_status() == {
        "running": False,
        "scanning": False,
        "processed": 0,
        "total": 0,
        "found": 0,
        "last_processed_isbn": None,
        "cancelled": False,
        "error": None,
    }


@mock.patch("src.bcd_api.services.cover_download_service.SessionLocal")
@mock.patch("src.bcd_api.services.cover_download_service.get_records_without_covers")
@mock.patch("src.bcd_api.services.cover_download_service.clean_broken_cover_references")
def test_run_missing_cover_download_reports_scan_error(
    mock_clean, mock_get_records, mock_session_local
):
    manager = CoverDownloadManager()
    mock_get_records.side_effect = RuntimeError("database unavailable")
    mock_db = mock.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_session_local.return_value = mock_db

    manager._status.update(running=True, scanning=True)
    manager._run_missing_cover_download()

    status = manager.get_status()
    assert status["running"] is False
    assert status["scanning"] is False
    assert status["error"] == "scan_failed"
