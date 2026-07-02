"""
Integration Tests for Admin Cover Endpoints

Tests the background cover downloading endpoints with FastAPI TestClient.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.bcd_api.main import app
from src.bcd_api.api.v1.admin import _download_status, _download_lock


@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_status():
    """Reset the global download status before and after each test."""
    with _download_lock:
        _download_status["running"] = False
        _download_status["processed"] = 0
        _download_status["total"] = 0
        _download_status["found"] = 0
        _download_status["last_processed_isbn"] = None
    yield
    with _download_lock:
        _download_status["running"] = False
        _download_status["processed"] = 0
        _download_status["total"] = 0
        _download_status["found"] = 0
        _download_status["last_processed_isbn"] = None


class TestAdminCoverEndpoints:
    """Test Suite for Cover Administration endpoints"""

    def test_get_status_initial(self, client):
        """Test getting initial (not running) download status."""
        response = client.get("/api/v1/admin/covers/download-missing/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert data["processed"] == 0
        assert data["total"] == 0
        assert data["found"] == 0
        assert data["last_processed_isbn"] is None

    def test_start_download_success(self, client):
        """Test starting the background download task successfully."""
        with patch("src.bcd_api.api.v1.admin._download_missing_covers_task") as mock_task:
            response = client.post("/api/v1/admin/covers/download-missing")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            
            # Status should be set to running
            with _download_lock:
                assert _download_status["running"] is True

            # Try to start it again while running
            response2 = client.post("/api/v1/admin/covers/download-missing")
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["status"] == "already_running"

    def test_cancel_download(self, client):
        """Test cancelling a running download task."""
        # When not running
        response = client.post("/api/v1/admin/covers/download-missing/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "not_running"

        # Set it to running
        with _download_lock:
            _download_status["running"] = True

        # Cancel it
        response2 = client.post("/api/v1/admin/covers/download-missing/cancel")
        assert response2.status_code == 200
        assert response2.json()["status"] == "cancelling"
        
        with _download_lock:
            assert _download_status["running"] is False
