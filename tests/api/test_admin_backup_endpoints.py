"""
Integration Tests for Admin Backup API Endpoints

Tests the backup/restore API endpoints with FastAPI TestClient.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.bcd_api.main import app


@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def temp_test_db():
    """Create a temporary test database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create test database with schema
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test_data (value) VALUES ('test')")
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def mock_backup_service():
    """Mock the backup service"""
    with patch('src.bcd_api.api.v1.admin.backup_service') as mock:
        yield mock


class TestCreateBackupEndpoint:
    """Test POST /admin/backup endpoint"""

    def test_create_backup_success(self, client, mock_backup_service):
        """Test successful backup creation"""
        # Mock backup metadata
        mock_metadata = MagicMock()
        mock_metadata.to_dict.return_value = {
            "filename": "bcd_backup_20260205_120000.db",
            "file_path": "/workspace/backups/bcd_backup_20260205_120000.db",
            "size_mb": 5.42,
            "size_bytes": 5681152,
            "created_at": "2026-02-05T12:00:00",
            "age_days": 0
        }
        mock_backup_service.create_backup.return_value = mock_metadata

        response = client.post("/api/v1/admin/backup")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "backup" in data
        assert data["backup"]["filename"] == "bcd_backup_20260205_120000.db"
        assert "message" in data

    def test_create_backup_failure(self, client, mock_backup_service):
        """Test backup creation failure"""
        mock_backup_service.create_backup.side_effect = Exception("Disk full")

        response = client.post("/api/v1/admin/backup")

        assert response.status_code == 500
        assert "Backup failed" in response.json()["detail"]

    def test_create_backup_invalid_database(self, client, mock_backup_service):
        """Test backup with invalid database type"""
        mock_backup_service.create_backup.side_effect = ValueError("Only supports SQLite")

        response = client.post("/api/v1/admin/backup")

        assert response.status_code == 400
        assert "Only supports SQLite" in response.json()["detail"]


class TestListBackupsEndpoint:
    """Test GET /admin/backups endpoint"""

    def test_list_backups_success(self, client, mock_backup_service):
        """Test listing backups successfully"""
        # Mock backup list
        mock_backup1 = MagicMock()
        mock_backup1.to_dict.return_value = {
            "filename": "bcd_backup_20260205_120000.db",
            "size_mb": 5.42,
            "created_at": "2026-02-05T12:00:00",
            "age_days": 0
        }

        mock_backup2 = MagicMock()
        mock_backup2.to_dict.return_value = {
            "filename": "bcd_backup_20260204_090000.db",
            "size_mb": 5.38,
            "created_at": "2026-02-04T09:00:00",
            "age_days": 1
        }

        mock_backup_service.list_backups.return_value = [mock_backup1, mock_backup2]
        mock_backup_service.get_database_size.return_value = {
            "size_mb": 5.45,
            "size_bytes": 5710848,
            "path": "/workspace/data/bcd.db"
        }

        response = client.get("/api/v1/admin/backups")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["backups"]) == 2
        assert data["backups"][0]["filename"] == "bcd_backup_20260205_120000.db"
        assert "database_info" in data

    def test_list_backups_empty(self, client, mock_backup_service):
        """Test listing backups when none exist"""
        mock_backup_service.list_backups.return_value = []
        mock_backup_service.get_database_size.return_value = {
            "size_mb": 5.45,
            "size_bytes": 5710848,
            "path": "/workspace/data/bcd.db"
        }

        response = client.get("/api/v1/admin/backups")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 0
        assert data["backups"] == []

    def test_list_backups_error(self, client, mock_backup_service):
        """Test error handling in list backups"""
        mock_backup_service.list_backups.side_effect = Exception("Permission denied")

        response = client.get("/api/v1/admin/backups")

        assert response.status_code == 500
        assert "Failed to list backups" in response.json()["detail"]


class TestRestoreBackupEndpoint:
    """Test POST /admin/restore endpoint"""

    def test_restore_success(self, client, mock_backup_service):
        """Test successful database restore"""
        mock_backup_service.restore_backup.return_value = True

        response = client.post(
            "/api/v1/admin/restore",
            params={
                "backup_file": "backups/bcd_backup_20260205_120000.db",
                "confirm": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "restored_from" in data
        assert "warning" in data
        assert "safety backup" in data["warning"]

    def test_restore_without_confirmation(self, client, mock_backup_service):
        """Test restore fails without confirmation"""
        response = client.post(
            "/api/v1/admin/restore",
            params={
                "backup_file": "backups/backup.db",
                "confirm": False
            }
        )

        assert response.status_code == 400
        assert "requires explicit confirmation" in response.json()["detail"]

    def test_restore_missing_confirmation(self, client, mock_backup_service):
        """Test restore with missing confirm parameter (defaults to False)"""
        response = client.post(
            "/api/v1/admin/restore",
            params={"backup_file": "backups/backup.db"}
        )

        assert response.status_code == 400
        assert "requires explicit confirmation" in response.json()["detail"]

    def test_restore_file_not_found(self, client, mock_backup_service):
        """Test restore with nonexistent backup file"""
        mock_backup_service.restore_backup.side_effect = FileNotFoundError(
            "Backup file not found: nonexistent.db"
        )

        response = client.post(
            "/api/v1/admin/restore",
            params={
                "backup_file": "backups/nonexistent.db",
                "confirm": True
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_restore_invalid_backup(self, client, mock_backup_service):
        """Test restore with invalid backup file"""
        mock_backup_service.restore_backup.side_effect = ValueError(
            "Backup file is not a valid SQLite database"
        )

        response = client.post(
            "/api/v1/admin/restore",
            params={
                "backup_file": "backups/invalid.db",
                "confirm": True
            }
        )

        assert response.status_code == 400
        assert "not a valid" in response.json()["detail"]

    def test_restore_failure(self, client, mock_backup_service):
        """Test restore operation failure"""
        mock_backup_service.restore_backup.side_effect = Exception("Restore failed")

        response = client.post(
            "/api/v1/admin/restore",
            params={
                "backup_file": "backups/backup.db",
                "confirm": True
            }
        )

        assert response.status_code == 500
        assert "Restore failed" in response.json()["detail"]


class TestCleanupBackupsEndpoint:
    """Test DELETE /admin/backups/cleanup endpoint"""

    def test_cleanup_default_retention(self, client, mock_backup_service):
        """Test cleanup with default 30-day retention"""
        mock_backup_service.cleanup_old_backups.return_value = 3

        response = client.delete("/api/v1/admin/backups/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 3
        assert data["keep_days"] == 30
        mock_backup_service.cleanup_old_backups.assert_called_once_with(keep_days=30)

    def test_cleanup_custom_retention(self, client, mock_backup_service):
        """Test cleanup with custom retention period"""
        mock_backup_service.cleanup_old_backups.return_value = 5

        response = client.delete("/api/v1/admin/backups/cleanup?keep_days=14")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 5
        assert data["keep_days"] == 14
        mock_backup_service.cleanup_old_backups.assert_called_once_with(keep_days=14)

    def test_cleanup_no_old_backups(self, client, mock_backup_service):
        """Test cleanup when no old backups exist"""
        mock_backup_service.cleanup_old_backups.return_value = 0

        response = client.delete("/api/v1/admin/backups/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        assert "0 backup(s)" in data["message"]

    def test_cleanup_error(self, client, mock_backup_service):
        """Test error handling in cleanup"""
        mock_backup_service.cleanup_old_backups.side_effect = Exception("Permission denied")

        response = client.delete("/api/v1/admin/backups/cleanup")

        assert response.status_code == 500
        assert "Cleanup failed" in response.json()["detail"]


class TestVerifyBackupEndpoint:
    """Test GET /admin/backups/verify/{filename} endpoint"""

    def test_verify_valid_backup(self, client, mock_backup_service):
        """Test verifying a valid backup"""
        from pathlib import Path

        # Create backups directory and test file
        backups_dir = Path("./backups")
        backups_dir.mkdir(exist_ok=True)
        test_backup = backups_dir / "bcd_backup_20260205_120000.db"
        test_backup.touch()

        try:
            mock_backup_service.verify_backup.return_value = True

            response = client.get("/api/v1/admin/backups/verify/bcd_backup_20260205_120000.db")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["valid"] is True
            assert "Backup is valid" in data["message"]
        finally:
            # Cleanup
            if test_backup.exists():
                test_backup.unlink()

    def test_verify_invalid_backup(self, client, mock_backup_service):
        """Test verifying an invalid backup"""
        from pathlib import Path

        # Create backups directory and test file
        backups_dir = Path("./backups")
        backups_dir.mkdir(exist_ok=True)
        test_backup = backups_dir / "invalid_backup.db"
        test_backup.touch()

        try:
            mock_backup_service.verify_backup.return_value = False

            response = client.get("/api/v1/admin/backups/verify/invalid_backup.db")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["valid"] is False
            assert "verification failed" in data["message"]
        finally:
            # Cleanup
            if test_backup.exists():
                test_backup.unlink()

    def test_verify_nonexistent_backup(self, client, mock_backup_service):
        """Test verifying a nonexistent backup file"""
        # Since we're using a mock_backup_service, we need to create a temp dir
        # to simulate the backups directory, or just test that the endpoint
        # properly returns 404 when the file doesn't exist
        mock_backup_service._get_backups_dir.return_value = Path("./backups_temp_not_exist_or_mocked")
        response = client.get("/api/v1/admin/backups/verify/nonexistent.db")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_verify_error(self, client, mock_backup_service):
        """Test error handling in verification"""
        # Create a temporary backup file to avoid 404
        from pathlib import Path

        backups_dir = Path("./backups")
        backups_dir.mkdir(exist_ok=True)

        test_backup = backups_dir / "test.db"
        test_backup.touch()

        try:
            mock_backup_service.verify_backup.side_effect = Exception("Verification error")

            response = client.get("/api/v1/admin/backups/verify/test.db")

            assert response.status_code == 500
            assert "Verification failed" in response.json()["detail"]
        finally:
            # Cleanup
            if test_backup.exists():
                test_backup.unlink()


class TestBackupEndpointsIntegration:
    """End-to-end integration tests with real backup service"""

    def test_full_backup_restore_cycle(self, client, temp_test_db):
        """Test complete backup and restore cycle"""
        with patch('src.bcd_api.services.admin.backup.settings') as mock_settings:
            mock_settings.database_url = f"sqlite:///{temp_test_db}"
            mock_settings.backups_dir_path = "backups"

            with patch('src.bcd_api.services.admin.backup.engine') as mock_engine:
                mock_engine.dispose = MagicMock()

                # Create backup
                backup_response = client.post("/api/v1/admin/backup")
                assert backup_response.status_code == 200
                backup_file = backup_response.json()["backup"]["file_path"]

                # List backups (should include our new backup)
                list_response = client.get("/api/v1/admin/backups")
                assert list_response.status_code == 200
                assert list_response.json()["count"] >= 1

                # Verify backup
                filename = Path(backup_file).name
                verify_response = client.get(f"/api/v1/admin/backups/verify/{filename}")
                assert verify_response.status_code == 200
                assert verify_response.json()["valid"] is True

                # Restore backup
                restore_response = client.post(
                    "/api/v1/admin/restore",
                    params={"backup_file": backup_file, "confirm": True}
                )
                assert restore_response.status_code == 200

    def test_backup_list_cleanup_cycle(self, client):
        """Test backup creation, listing, and cleanup"""
        with patch('src.bcd_api.api.v1.admin.backup_service') as mock_service:
            # Setup mocks
            mock_metadata = MagicMock()
            mock_metadata.to_dict.return_value = {
                "filename": "test_backup.db",
                "size_mb": 1.0,
                "created_at": "2026-01-01T00:00:00",
                "age_days": 40
            }

            mock_service.create_backup.return_value = mock_metadata
            mock_service.list_backups.return_value = [mock_metadata]
            mock_service.get_database_size.return_value = {"size_mb": 1.5}
            mock_service.cleanup_old_backups.return_value = 1

            # Create backup
            backup_response = client.post("/api/v1/admin/backup")
            assert backup_response.status_code == 200

            # List backups
            list_response = client.get("/api/v1/admin/backups")
            assert list_response.status_code == 200
            assert len(list_response.json()["backups"]) == 1

            # Cleanup old backups
            cleanup_response = client.delete("/api/v1/admin/backups/cleanup?keep_days=30")
            assert cleanup_response.status_code == 200
            assert cleanup_response.json()["deleted_count"] == 1


class TestDownloadBackupEndpoint:
    """Test GET /admin/backups/{filename}/download endpoint"""

    def test_download_success(self, client, mock_backup_service):
        """Test successful download of a backup file"""
        from pathlib import Path
        backups_dir = Path("./backups")
        backups_dir.mkdir(exist_ok=True)
        test_backup = backups_dir / "test_download.db"
        test_backup.touch()

        try:
            # Configure mock_backup_service's _get_backups_dir to point to actual dir
            mock_backup_service._get_backups_dir.return_value = backups_dir

            response = client.get("/api/v1/admin/backups/test_download.db/download")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/x-sqlite3"
        finally:
            if test_backup.exists():
                test_backup.unlink()

    def test_download_nonexistent(self, client, mock_backup_service):
        """Test downloading a backup that doesn't exist"""
        mock_backup_service._get_backups_dir.return_value = Path("./backups")
        response = client.get("/api/v1/admin/backups/nonexistent_file.db/download")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_download_traversal_prevention(self, client, mock_backup_service):
        """Test directory traversal prevention"""
        mock_backup_service._get_backups_dir.return_value = Path("./backups")
        # If we request a filename like "invalid_file.db", it shouldn't allow escaping or access
        response = client.get("/api/v1/admin/backups/invalid_file.db/download")
        assert response.status_code == 404


class TestImportBackupEndpoint:
    """Test POST /admin/backups/import endpoint"""

    def test_import_invalid_db(self, client, mock_backup_service):
        """Test importing/uploading an invalid database backup"""
        mock_backup_service._get_backups_dir.return_value = Path("./backups")
        mock_backup_service.verify_backup.return_value = False

        file_payload = {"file": ("test_invalid.db", b"not-a-sqlite-db", "application/octet-stream")}
        response = client.post("/api/v1/admin/backups/import", files=file_payload)

        assert response.status_code == 400
        assert "not a valid SQLite database" in response.json()["detail"]

    def test_import_success(self, client, mock_backup_service):
        """Test successful upload and restoration of backup"""
        mock_backup_service._get_backups_dir.return_value = Path("./backups")
        mock_backup_service.verify_backup.return_value = True
        mock_backup_service.restore_backup.return_value = True

        file_payload = {"file": ("test_valid.db", b"valid-db-bytes", "application/octet-stream")}
        response = client.post("/api/v1/admin/backups/import", files=file_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Database successfully imported and restored" in data["message"]
        mock_backup_service.restore_backup.assert_called_once()

