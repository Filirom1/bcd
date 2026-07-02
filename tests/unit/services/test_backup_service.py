"""
Unit Tests for Backup Service

Tests all backup service functions with various scenarios.
"""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.bcd_api.services import backup_service
from src.bcd_api.services.backup_service import BackupMetadata


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create a simple test database
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test_table (name) VALUES ('test_data')")
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_settings(temp_db):
    """Mock settings with temporary database path"""
    with patch('src.bcd_api.services.backup_service.settings') as mock:
        mock.database_url = f"sqlite:///{temp_db}"
        mock.backups_dir_path = ""
        yield mock


class TestBackupMetadata:
    """Test BackupMetadata class"""

    def test_backup_metadata_creation(self, temp_db):
        """Test creating BackupMetadata from a file"""
        metadata = BackupMetadata(temp_db)

        assert metadata.file_path == temp_db
        assert metadata.filename == temp_db.name
        assert metadata.size_bytes > 0
        assert metadata.size_mb > 0
        assert isinstance(metadata.created_at, datetime)
        assert metadata.age_days >= 0

    def test_backup_metadata_to_dict(self, temp_db):
        """Test converting metadata to dictionary"""
        metadata = BackupMetadata(temp_db)
        data = metadata.to_dict()

        assert "filename" in data
        assert "file_path" in data
        assert "size_mb" in data
        assert "size_bytes" in data
        assert "created_at" in data
        assert "age_days" in data
        assert data["filename"] == temp_db.name


class TestGetDatabasePath:
    """Test get_database_path function"""

    def test_get_database_path_sqlite(self, mock_settings, temp_db):
        """Test extracting database path from SQLite URL"""
        path = backup_service.get_database_path()
        assert path == temp_db

    def test_get_database_path_relative(self):
        """Test handling relative database paths"""
        with patch('src.bcd_api.services.backup_service.settings') as mock:
            mock.database_url = "sqlite:///./test.db"
            path = backup_service.get_database_path()
            assert path.name == "test.db"
            assert path.is_absolute()

    def test_get_database_path_non_sqlite(self):
        """Test error handling for non-SQLite databases"""
        with patch('src.bcd_api.services.backup_service.settings') as mock:
            mock.database_url = "postgresql://localhost/test"

            with pytest.raises(ValueError, match="only supports SQLite"):
                backup_service.get_database_path()


class TestCreateBackup:
    """Test create_backup function"""

    def test_create_backup_default_location(self, mock_settings, temp_db):
        """Test creating backup with default location"""
        # Mock engine.dispose()
        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            metadata = backup_service.create_backup()

            assert metadata.file_path.exists()
            assert metadata.file_path.parent.name == "backups"
            assert metadata.filename.startswith("bcd_backup_")
            assert metadata.filename.endswith(".db")
            assert metadata.size_mb > 0

            # Cleanup
            metadata.file_path.unlink()

    def test_create_backup_custom_location(self, mock_settings, temp_db, temp_backup_dir):
        """Test creating backup with custom output path"""
        custom_path = temp_backup_dir / "custom_backup.db"

        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            metadata = backup_service.create_backup(output_path=str(custom_path))

            assert metadata.file_path == custom_path
            assert custom_path.exists()
            assert metadata.size_mb > 0

    def test_create_backup_creates_directory(self, mock_settings, temp_db, temp_backup_dir):
        """Test that backup creates parent directories if they don't exist"""
        nested_path = temp_backup_dir / "nested" / "dir" / "backup.db"

        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            metadata = backup_service.create_backup(output_path=str(nested_path))

            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_create_backup_database_not_found(self):
        """Test error handling when database file doesn't exist"""
        with patch('src.bcd_api.services.backup_service.settings') as mock:
            mock.database_url = "sqlite:///nonexistent.db"

            with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
                mock_engine.dispose = MagicMock()

                with pytest.raises(FileNotFoundError):
                    backup_service.create_backup()

    def test_create_backup_timestamp_format(self, mock_settings, temp_db):
        """Test that backup filename includes valid timestamp"""
        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            metadata = backup_service.create_backup()
            filename = metadata.filename

            # Should be: bcd_backup_YYYYMMDD_HHMMSS.db
            assert filename.startswith("bcd_backup_")
            assert filename.endswith(".db")

            # Extract timestamp
            timestamp_str = filename.replace("bcd_backup_", "").replace(".db", "")
            # Should parse without error
            datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            # Cleanup
            metadata.file_path.unlink()


class TestVerifyBackup:
    """Test verify_backup function"""

    def test_verify_valid_backup(self, temp_db):
        """Test verifying a valid SQLite backup"""
        result = backup_service.verify_backup(str(temp_db))
        assert result is True

    def test_verify_invalid_file(self, temp_backup_dir):
        """Test verifying an invalid file"""
        invalid_file = temp_backup_dir / "invalid.db"
        invalid_file.write_text("not a database")

        result = backup_service.verify_backup(str(invalid_file))
        assert result is False

    def test_verify_nonexistent_file(self):
        """Test verifying a file that doesn't exist"""
        result = backup_service.verify_backup("/nonexistent/file.db")
        assert result is False

    def test_verify_corrupted_database(self, temp_backup_dir):
        """Test verifying a corrupted SQLite database"""
        corrupt_db = temp_backup_dir / "corrupt.db"

        # Create a database and then corrupt it
        conn = sqlite3.connect(str(corrupt_db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        # Truncate the file to corrupt it
        with open(corrupt_db, 'r+b') as f:
            f.truncate(100)  # Corrupt by truncating

        result = backup_service.verify_backup(str(corrupt_db))
        assert result is False


class TestListBackups:
    """Test list_backups function"""

    def test_list_backups_empty_directory(self, temp_backup_dir):
        """Test listing backups when directory is empty"""
        backups = backup_service.list_backups(backup_dir=str(temp_backup_dir))
        assert backups == []

    def test_list_backups_nonexistent_directory(self):
        """Test listing backups when directory doesn't exist"""
        backups = backup_service.list_backups(backup_dir="/nonexistent/dir")
        assert backups == []

    def test_list_backups_multiple_files(self, temp_backup_dir, temp_db):
        """Test listing multiple backup files"""
        # Create multiple backup files
        backup1 = temp_backup_dir / "backup1.db"
        backup2 = temp_backup_dir / "backup2.db"
        backup3 = temp_backup_dir / "backup3.db"

        import shutil
        shutil.copy2(temp_db, backup1)
        shutil.copy2(temp_db, backup2)
        shutil.copy2(temp_db, backup3)

        backups = backup_service.list_backups(backup_dir=str(temp_backup_dir))

        assert len(backups) == 3
        assert all(isinstance(b, BackupMetadata) for b in backups)
        assert all(b.file_path.exists() for b in backups)

    def test_list_backups_sorted_by_date(self, temp_backup_dir, temp_db):
        """Test that backups are sorted by creation time (newest first)"""
        import os
        import shutil

        # Create backups and set mtimes explicitly to avoid copy2 timestamp preservation
        backup1 = temp_backup_dir / "old.db"
        shutil.copy(temp_db, backup1)
        os.utime(backup1, (1_000_000, 1_000_000))

        backup2 = temp_backup_dir / "new.db"
        shutil.copy(temp_db, backup2)
        os.utime(backup2, (2_000_000, 2_000_000))

        backups = backup_service.list_backups(backup_dir=str(temp_backup_dir))

        # Newest should be first
        assert backups[0].filename == "new.db"
        assert backups[1].filename == "old.db"

    def test_list_backups_ignores_non_db_files(self, temp_backup_dir, temp_db):
        """Test that only .db files are listed"""
        import shutil

        # Create .db file
        backup = temp_backup_dir / "backup.db"
        shutil.copy2(temp_db, backup)

        # Create non-.db files
        (temp_backup_dir / "readme.txt").write_text("test")
        (temp_backup_dir / "backup.sql").write_text("test")

        backups = backup_service.list_backups(backup_dir=str(temp_backup_dir))

        assert len(backups) == 1
        assert backups[0].filename == "backup.db"


class TestCleanupOldBackups:
    """Test cleanup_old_backups function"""

    def test_cleanup_no_old_backups(self, temp_backup_dir, temp_db):
        """Test cleanup when all backups are recent"""
        import shutil

        # Create recent backup
        backup = temp_backup_dir / "recent.db"
        shutil.copy2(temp_db, backup)

        deleted_count = backup_service.cleanup_old_backups(
            keep_days=30,
            backup_dir=str(temp_backup_dir)
        )

        assert deleted_count == 0
        assert backup.exists()

    def test_cleanup_old_backups(self, temp_backup_dir, temp_db):
        """Test cleanup deletes old backups"""
        import os
        import shutil
        import time

        # Create old backup (modify timestamp)
        old_backup = temp_backup_dir / "old.db"
        shutil.copy2(temp_db, old_backup)

        # Set modification time to 60 days ago
        old_time = time.time() - (60 * 24 * 60 * 60)
        os.utime(old_backup, (old_time, old_time))

        # Create recent backup
        recent_backup = temp_backup_dir / "recent.db"
        shutil.copy2(temp_db, recent_backup)

        deleted_count = backup_service.cleanup_old_backups(
            keep_days=30,
            backup_dir=str(temp_backup_dir)
        )

        assert deleted_count == 1
        assert not old_backup.exists()
        assert recent_backup.exists()

    def test_cleanup_custom_retention(self, temp_backup_dir, temp_db):
        """Test cleanup with custom retention period"""
        import os
        import shutil
        import time

        backup = temp_backup_dir / "backup.db"
        shutil.copy2(temp_db, backup)

        # Set to 8 days old
        old_time = time.time() - (8 * 24 * 60 * 60)
        os.utime(backup, (old_time, old_time))

        # Should NOT delete with 30-day retention
        deleted_count = backup_service.cleanup_old_backups(
            keep_days=30,
            backup_dir=str(temp_backup_dir)
        )
        assert deleted_count == 0
        assert backup.exists()

        # Should delete with 7-day retention
        deleted_count = backup_service.cleanup_old_backups(
            keep_days=7,
            backup_dir=str(temp_backup_dir)
        )
        assert deleted_count == 1
        assert not backup.exists()


class TestRestoreBackup:
    """Test restore_backup function"""

    def test_restore_valid_backup(self, mock_settings, temp_db, temp_backup_dir):
        """Test restoring from a valid backup"""
        import shutil

        # Create backup
        backup_file = temp_backup_dir / "backup.db"
        shutil.copy2(temp_db, backup_file)

        # Modify original database
        conn = sqlite3.connect(str(temp_db))
        conn.execute("INSERT INTO test_table (name) VALUES ('new_data')")
        conn.commit()
        conn.close()

        # Restore from backup
        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            result = backup_service.restore_backup(str(backup_file))
            assert result is True

        # Verify data was restored (should not have 'new_data')
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM test_table")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "test_data"

    def test_restore_nonexistent_backup(self, mock_settings, temp_db):
        """Test error handling when backup file doesn't exist"""
        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            with pytest.raises(FileNotFoundError):
                backup_service.restore_backup("/nonexistent/backup.db")

    def test_restore_invalid_backup(self, mock_settings, temp_db, temp_backup_dir):
        """Test error handling for invalid backup file"""
        invalid_backup = temp_backup_dir / "invalid.db"
        invalid_backup.write_text("not a database")

        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            with pytest.raises(ValueError, match="not a valid SQLite database"):
                backup_service.restore_backup(str(invalid_backup))

    def test_restore_creates_safety_backup(self, mock_settings, temp_db, temp_backup_dir):
        """Test that restore creates a safety backup"""
        import shutil

        backup_file = temp_backup_dir / "backup.db"
        shutil.copy2(temp_db, backup_file)

        with patch('src.bcd_api.services.backup_service.engine') as mock_engine:
            mock_engine.dispose = MagicMock()

            backup_service.restore_backup(str(backup_file))

        # Check that safety backup was created
        safety_dir = Path("./backups/pre_restore")
        assert safety_dir.exists()

        safety_backups = list(safety_dir.glob("pre_restore_*.db"))
        assert len(safety_backups) > 0


class TestGetDatabaseSize:
    """Test get_database_size function"""

    def test_get_database_size(self, mock_settings, temp_db):
        """Test getting database size information"""
        size_info = backup_service.get_database_size()

        assert "size_bytes" in size_info
        assert "size_mb" in size_info
        assert "path" in size_info
        assert size_info["size_bytes"] > 0
        assert size_info["size_mb"] > 0
        assert str(temp_db) in size_info["path"]

    def test_get_database_size_error_handling(self):
        """Test error handling when database doesn't exist"""
        with patch('src.bcd_api.services.backup_service.settings') as mock:
            mock.database_url = "sqlite:///nonexistent.db"

            size_info = backup_service.get_database_size()

            assert size_info["size_bytes"] == 0
            assert size_info["size_mb"] == 0.0
            assert size_info["path"] == "unknown"
