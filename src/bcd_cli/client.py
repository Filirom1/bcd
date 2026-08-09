"""
API Client - HTTP client wrapper for BCD API

Handles communication with the FastAPI backend.
"""

import os
from typing import Any, Dict, List, Optional

import httpx


class BCDAPIClient:
    """HTTP client for BCD API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        timeout: int = 30,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL of the API server
            timeout: Request timeout in seconds
            auth_username: Username for HTTP Digest Auth (optional)
            auth_password: Password for HTTP Digest Auth (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Read auth credentials from environment if not provided
        if auth_username is None:
            auth_username = os.environ.get("BCD_AUTH_USERNAME", "")
        if auth_password is None:
            auth_password = os.environ.get("BCD_AUTH_PASSWORD", "")

        # Configure authentication if credentials provided
        auth = None
        if auth_username and auth_password:
            auth = httpx.DigestAuth(username=auth_username, password=auth_password)

        self.client = httpx.Client(timeout=timeout, auth=auth)

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON payload for POST/PUT
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.client.request(
                method=method, url=url, json=json_data, params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to BCD API at {self.base_url}\n"
                "  • Is the API server running? Try: bcd\n"
                "  • Check API URL in config"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to {endpoint} timed out after {self.timeout}s"
            )
        except httpx.HTTPStatusError as e:
            # Extract error details from response
            try:
                error_detail = e.response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise Exception(f"API Error ({e.response.status_code}): {error_detail}")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> httpx.Response:
        """
        Make GET request to API endpoint.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            httpx.Response object
        """
        url = f"{self.base_url}{endpoint}"
        return self.client.get(url, params=params)

    def post(self, endpoint: str, json: Optional[Dict] = None, files: Optional[Dict] = None) -> httpx.Response:
        """
        Make POST request to API endpoint.

        Args:
            endpoint: API endpoint path
            json: JSON payload
            files: Files to upload

        Returns:
            httpx.Response object
        """
        url = f"{self.base_url}{endpoint}"
        return self.client.post(url, json=json, files=files)

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    # Circulation endpoints

    def checkout(
        self, borrower_id: str, item_ids: List[str], checked_out_by: str = "cli"
    ) -> Dict[str, Any]:
        """
        Checkout items to a borrower.

        Args:
            borrower_id: Borrower ID
            item_ids: List of item IDs to checkout
            checked_out_by: Who performed the checkout

        Returns:
            Checkout response with transaction details
        """
        payload = {
            "borrower_id": borrower_id,
            "item_ids": item_ids,
            "checked_out_by": checked_out_by,
        }
        return self._request("POST", "/api/v1/circulation/checkout", json_data=payload)

    def return_items(
        self, item_ids: List[str], returned_by: str = "cli"
    ) -> Dict[str, Any]:
        """
        Return items.

        Args:
            item_ids: List of item IDs to return
            returned_by: Who processed the return

        Returns:
            Return response with details
        """
        payload = {"item_ids": item_ids, "returned_by": returned_by}
        return self._request("POST", "/api/v1/circulation/return", json_data=payload)

    def renew_items(
        self, borrower_id: str, item_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Renew items for a borrower.

        Args:
            borrower_id: Borrower ID
            item_ids: Optional list of specific items to renew (None = all eligible)

        Returns:
            Renewal response
        """
        payload = {"borrower_id": borrower_id}
        if item_ids is not None:
            payload["item_ids"] = item_ids
        return self._request("POST", "/api/v1/circulation/renew", json_data=payload)

    def get_borrower_current_loans(self, borrower_id: str) -> Dict[str, Any]:
        """
        Get borrower information with their current loans.

        Args:
            borrower_id: Borrower ID

        Returns:
            Borrower detailed data including current loans
        """
        return self._request(
            "GET", f"/api/v1/borrowers/{borrower_id}?detail=true"
        )

    def get_item_history(self, item_id: str) -> Dict[str, Any]:
        """
        Get circulation history for an item.

        Args:
            item_id: Item ID

        Returns:
            Item history data
        """
        return self._request("GET", f"/api/v1/circulation/item/{item_id}/history")

    def get_borrower_history(self, borrower_id: str) -> Dict[str, Any]:
        """
        Get circulation history for a borrower.

        Args:
            borrower_id: Borrower ID

        Returns:
            Borrower history data
        """
        return self._request(
            "GET", f"/api/v1/circulation/borrower/{borrower_id}/history"
        )

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance
_client: Optional[BCDAPIClient] = None


def get_client(
    base_url: str = "http://localhost:8888",
    auth_username: Optional[str] = None,
    auth_password: Optional[str] = None,
) -> BCDAPIClient:
    """
    Get or create API client singleton.

    Args:
        base_url: API base URL
        auth_username: Username for HTTP Digest Auth (optional)
        auth_password: Password for HTTP Digest Auth (optional)

    Returns:
        BCDAPIClient instance
    """
    global _client
    if _client is None:
        _client = BCDAPIClient(
            base_url=base_url,
            auth_username=auth_username,
            auth_password=auth_password,
        )
    return _client
