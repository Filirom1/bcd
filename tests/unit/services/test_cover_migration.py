from pathlib import Path
from unittest.mock import MagicMock

from src.bcd_api.services.external.cover import migrate_covers_to_isbn13


def test_migrate_covers_renames_isbn10_and_writes_sentinel(tmp_path):
    source = tmp_path / "2211056466.jpg"
    source.write_bytes(b"image")
    db = MagicMock()
    migrate_covers_to_isbn13(tmp_path, db=db)
    destination = tmp_path / "9782211056465.jpg"
    assert destination.exists()
    assert not source.exists()
    assert (tmp_path / ".isbn13").exists()
    db.commit.assert_called_once()
    db.execute.assert_called_once()


def test_migrate_covers_skips_existing_sentinel(tmp_path):
    sentinel = tmp_path / ".isbn13"
    sentinel.write_text("")
    source = tmp_path / "2211056466.jpg"
    source.write_bytes(b"image")
    db = MagicMock()
    migrate_covers_to_isbn13(tmp_path, db=db)
    assert source.exists()
    db.execute.assert_not_called()


def test_migrate_covers_ignores_missing_directory(tmp_path):
    missing = tmp_path / "missing"
    migrate_covers_to_isbn13(missing)
    assert not missing.exists()
