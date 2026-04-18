"""
API-layer tests for GET /api/v1/catalog/items/available-ids endpoint.

Tests the HTTP layer only: query-parameter validation, response shape, and
HTTP status codes.  The service behavour (contiguous vs scatter algorithm) is
fully covered by TestGetAvailableItemIDs in
tests/integration/services/test_catalog_service.py.

The service is mocked here to keep tests fast, deterministic, and free of
database-isolation issues.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.bcd_api.main import app

# ---------------------------------------------------------------------------
# Shared mock response factory
# ---------------------------------------------------------------------------

def _mock_ids(ids, contiguous=True):
    """Build a realistic service return value from a list of ID strings."""
    return {
        "ids": ids,
        "start_id": ids[0],
        "end_id": ids[-1],
        "count": len(ids),
        "id_format": "numeric",
        "contiguous": contiguous,
    }


SERVICE_PATH = "src.bcd_api.api.v1.catalog.catalog_service.get_available_item_ids"


@pytest.fixture
def client():
    """Plain TestClient — no DB override needed (service is mocked)."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------

class TestAvailableIdsResponseStructure:
    """Verify the shape of a successful response."""

    def test_response_has_all_required_fields(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["1", "2", "3"])):
            response = client.get("/api/v1/catalog/items/available-ids?count=3")

        assert response.status_code == 200
        body = response.json()
        for field in ("ids", "start_id", "end_id", "count", "id_format", "contiguous"):
            assert field in body, f"Missing field: {field}"

    def test_ids_is_a_list_of_strings(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["1", "2", "3", "4", "5"])):
            response = client.get("/api/v1/catalog/items/available-ids?count=5")

        body = response.json()
        assert isinstance(body["ids"], list)
        assert all(isinstance(i, str) for i in body["ids"])

    def test_count_field_matches_ids_length(self, client):
        ids = [str(i) for i in range(1, 8)]
        with patch(SERVICE_PATH, return_value=_mock_ids(ids)):
            response = client.get("/api/v1/catalog/items/available-ids?count=7")

        body = response.json()
        assert body["count"] == len(body["ids"]) == 7


# ---------------------------------------------------------------------------
# Default behaviour
# ---------------------------------------------------------------------------

class TestAvailableIdsDefaults:
    """Default parameter handling."""

    def test_default_count_30_is_passed_to_service(self, client):
        """When count is omitted the service receives 30."""
        with patch(SERVICE_PATH, return_value=_mock_ids([str(i) for i in range(1, 31)])) as mock:
            response = client.get("/api/v1/catalog/items/available-ids")

        assert response.status_code == 200
        _args, kwargs = mock.call_args
        assert kwargs.get("count", _args[1] if len(_args) > 1 else None) == 30

    def test_default_contiguous_true_is_passed_to_service(self, client):
        """contiguous defaults to True."""
        with patch(SERVICE_PATH, return_value=_mock_ids(["1", "2", "3"])) as mock:
            response = client.get("/api/v1/catalog/items/available-ids?count=3")

        assert response.status_code == 200
        _args, kwargs = mock.call_args
        assert kwargs.get("contiguous", _args[3] if len(_args) > 3 else True) is True

    def test_response_contiguous_field_reflects_true(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["1", "2", "3"], contiguous=True)):
            response = client.get("/api/v1/catalog/items/available-ids?count=3")

        assert response.json()["contiguous"] is True

    def test_response_id_format_is_numeric(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["1"])):
            response = client.get("/api/v1/catalog/items/available-ids?count=1")

        assert response.json()["id_format"] == "numeric"


# ---------------------------------------------------------------------------
# count validation (FastAPI enforces ge=1, le=1000 — no service call needed)
# ---------------------------------------------------------------------------

class TestAvailableIdsCountValidation:
    """count must satisfy 1 ≤ count ≤ 1000."""

    def test_count_zero_returns_422(self, client):
        assert client.get("/api/v1/catalog/items/available-ids?count=0").status_code == 422

    def test_count_negative_returns_422(self, client):
        assert client.get("/api/v1/catalog/items/available-ids?count=-1").status_code == 422

    def test_count_above_1000_returns_422(self, client):
        assert client.get("/api/v1/catalog/items/available-ids?count=1001").status_code == 422

    def test_count_1_is_accepted(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["42"])):
            response = client.get("/api/v1/catalog/items/available-ids?count=1")
        assert response.status_code == 200

    def test_count_1000_is_accepted(self, client):
        ids = [str(i) for i in range(1, 1001)]
        with patch(SERVICE_PATH, return_value=_mock_ids(ids)):
            response = client.get("/api/v1/catalog/items/available-ids?count=1000")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# start_from parameter
# ---------------------------------------------------------------------------

class TestAvailableIdsStartFrom:
    """start_from handling."""

    def test_start_from_forwarded_to_service(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["500", "501", "502"])) as mock:
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=3&start_from=500"
            )

        assert response.status_code == 200
        _args, kwargs = mock.call_args
        start = kwargs.get("start_from", _args[2] if len(_args) > 2 else None)
        assert start == "500"

    def test_start_from_reflected_in_response(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["500", "501", "502"])):
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=3&start_from=500"
            )

        body = response.json()
        assert body["start_id"] == "500"
        assert body["ids"][0] == "500"

    def test_start_from_non_numeric_returns_400(self, client):
        """Service raises ValueError for non-numeric start_from; endpoint maps to 400."""
        with patch(SERVICE_PATH, side_effect=ValueError("Invalid start_from value")):
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=5&start_from=ABCDE"
            )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# contiguous parameter
# ---------------------------------------------------------------------------

class TestAvailableIdsContiguous:
    """contiguous query-parameter forwarding and response."""

    def test_contiguous_false_forwarded_to_service(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["3", "6", "7"], contiguous=False)) as mock:
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=3&contiguous=false"
            )

        assert response.status_code == 200
        _args, kwargs = mock.call_args
        cont = kwargs.get("contiguous", _args[3] if len(_args) > 3 else None)
        assert cont is False

    def test_contiguous_false_reflected_in_response(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["3", "6", "7"], contiguous=False)):
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=3&contiguous=false"
            )

        assert response.json()["contiguous"] is False

    def test_contiguous_true_forwarded_to_service(self, client):
        with patch(SERVICE_PATH, return_value=_mock_ids(["6", "7", "8"], contiguous=True)) as mock:
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=3&contiguous=true"
            )

        _args, kwargs = mock.call_args
        cont = kwargs.get("contiguous", _args[3] if len(_args) > 3 else None)
        assert cont is True

    def test_contiguous_response_ids_match_service_output(self, client):
        """The endpoint passes through whatever the service returns unchanged."""
        expected = ["3", "6", "7"]
        with patch(SERVICE_PATH, return_value=_mock_ids(expected, contiguous=False)):
            response = client.get(
                "/api/v1/catalog/items/available-ids?count=3&contiguous=false"
            )

        assert response.json()["ids"] == expected

