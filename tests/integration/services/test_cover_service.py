"""Integration tests for cover_service — full cascade with mocked HTTP.

Tests verify the end-to-end flow: ISBN input → provider cascade → file on disk.
No real HTTP requests are made; httpx is patched at the client level.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.bcd_api.services import cover_service
from src.bcd_api.services.cover_service import configure, download_cover

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_config():
    """Ensure cover_service global state is clean between tests."""
    original_key = cover_service._google_api_key
    yield
    cover_service._google_api_key = original_key


@pytest.fixture
def covers_dir(tmp_path):
    return tmp_path / "covers"


def _image(size: int = 12_000) -> bytes:
    """Fake JPEG bytes that pass the MIN_BYTES guard."""
    return b"\xff\xd8\xff\xe0" + b"A" * size


def _mock_httpx_client(responses: dict[str, bytes | None]):
    """
    Build a mock httpx.Client. responses maps URL substrings to bytes (hit)
    or None (miss / error). Unmatched URLs return None.
    """
    def get_side_effect(url, **kwargs):
        for key, data in responses.items():
            if key in url:
                r = MagicMock()
                r.status_code = 200 if data else 404
                r.content = data or b""
                r.headers = {"content-type": "image/jpeg" if data else "text/plain"}
                return r
        # Default: 404
        r = MagicMock()
        r.status_code = 404
        r.content = b""
        r.headers = {"content-type": "text/plain"}
        return r

    client = MagicMock()
    client.get.side_effect = get_side_effect
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# Full cascade — happy paths
# ---------------------------------------------------------------------------

class TestCascadeHappyPaths:
    def test_amazon_found_first_no_other_providers_called(self, covers_dir):
        """When Amazon returns a cover, Open Library is never contacted."""
        data = _image()
        client = _mock_httpx_client({"ssl-images-amazon.com": data})

        with patch("httpx.Client", return_value=client):
            result = download_cover("2211056466", covers_dir=covers_dir)

        assert result == "9782211056465.jpg"
        assert (covers_dir / "9782211056465.jpg").read_bytes() == data
        # Open Library URL should never have been requested
        openlibrary_calls = [
            c for c in client.get.call_args_list
            if "openlibrary" in str(c)
        ]
        assert openlibrary_calls == []

    def test_openlibrary_used_when_amazon_misses(self, covers_dir):
        data = _image()
        client = _mock_httpx_client({
            "ssl-images-amazon.com": None,
            "m.media-amazon.com": None,
            "openlibrary.org": data,
        })
        with patch("httpx.Client", return_value=client):
            result = download_cover("9782211056465", covers_dir=covers_dir)

        assert result == "9782211056465.jpg"
        assert (covers_dir / "9782211056465.jpg").read_bytes() == data

    def test_google_api_used_when_amazon_and_ol_miss(self, covers_dir):
        data = _image()
        google_api_response = {
            "totalItems": 1,
            "items": [{"volumeInfo": {"imageLinks": {
                "thumbnail": "https://books.google.com/books/thumb.jpg"
            }}}]
        }
        client = _mock_httpx_client({
            "ssl-images-amazon.com": None,
            "m.media-amazon.com": None,
            "openlibrary.org": None,
            "books/thumb.jpg": data,
        })
        client.get.side_effect = None  # override side_effect for JSON responses

        def get_side_effect(url, **kwargs):
            if "googleapis.com" in url:
                r = MagicMock()
                r.status_code = 200
                r.json.return_value = google_api_response
                r.content = b""
                r.headers = {"content-type": "application/json"}
                return r
            if "thumb.jpg" in url:
                r = MagicMock()
                r.status_code = 200
                r.content = data
                r.headers = {"content-type": "image/jpeg"}
                return r
            r = MagicMock()
            r.status_code = 404
            r.content = b""
            r.headers = {"content-type": "text/plain"}
            return r

        client.get.side_effect = get_side_effect

        with patch("httpx.Client", return_value=client):
            result = download_cover("9782211056465", covers_dir=covers_dir)

        assert result == "9782211056465.jpg"

    def test_geobib_used_as_last_resort(self, covers_dir):
        data = _image()
        client = _mock_httpx_client({
            "ssl-images-amazon.com": None,
            "m.media-amazon.com": None,
            "openlibrary.org": None,
            "googleapis.com": None,
            "geobib.fr": data,
        })
        # Override for geobib since it checks content-type
        def get_side_effect(url, **kwargs):
            if "geobib.fr" in url:
                r = MagicMock()
                r.status_code = 200
                r.content = data
                r.headers = {"content-type": "image/jpeg"}
                return r
            r = MagicMock()
            r.status_code = 404
            r.content = b""
            r.headers = {"content-type": "text/plain"}
            return r
        client.get.side_effect = get_side_effect

        with patch("httpx.Client", return_value=client):
            result = download_cover("9782211056465", covers_dir=covers_dir)

        assert result == "9782211056465.jpg"
        assert (covers_dir / "9782211056465.jpg").stat().st_size > 0

    def test_returns_none_when_all_providers_fail(self, covers_dir):
        client = _mock_httpx_client({})  # all 404
        with patch("httpx.Client", return_value=client):
            result = download_cover("9782211056465", covers_dir=covers_dir)
        assert result is None
        assert not covers_dir.exists() or not list(covers_dir.iterdir())


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_returns_cached_filename_without_http_call(self, covers_dir):
        covers_dir.mkdir()
        existing = covers_dir / "9782211056465.jpg"
        existing.write_bytes(_image())

        client = MagicMock()
        with patch("httpx.Client", return_value=client):
            result = download_cover("9782211056465", covers_dir=covers_dir)

        assert result == "9782211056465.jpg"
        client.__enter__.assert_not_called()  # httpx.Client never entered

    def test_second_call_returns_same_filename(self, covers_dir):
        data = _image()
        client = _mock_httpx_client({"ssl-images-amazon.com": data})

        with patch("httpx.Client", return_value=client):
            r1 = download_cover("2211056466", covers_dir=covers_dir)
            r2 = download_cover("2211056466", covers_dir=covers_dir)

        assert r1 == r2 == "9782211056465.jpg"


# ---------------------------------------------------------------------------
# ISBN normalisation
# ---------------------------------------------------------------------------

class TestIsbnNormalisation:
    def test_isbn10_and_isbn13_both_resolve(self, covers_dir):
        """ISBN-10 and its ISBN-13 equivalent should find the same cover."""
        data = _image()
        client = _mock_httpx_client({"ssl-images-amazon.com": data})

        with patch("httpx.Client", return_value=client):
            r10 = download_cover("2211056466", covers_dir=covers_dir)
        assert r10 == "9782211056465.jpg"
        assert (covers_dir / "9782211056465.jpg").exists()

    def test_hyphened_isbn13_normalised(self, covers_dir):
        data = _image()
        client = _mock_httpx_client({"ssl-images-amazon.com": data})
        with patch("httpx.Client", return_value=client):
            result = download_cover("978-2-211-05646-5", covers_dir=covers_dir)
        assert result == "9782211056465.jpg"

    def test_isbn_prefix_stripped(self, covers_dir):
        data = _image()
        client = _mock_httpx_client({"ssl-images-amazon.com": data})
        with patch("httpx.Client", return_value=client):
            result = download_cover("isbn:2211056466", covers_dir=covers_dir)
        assert result == "9782211056465.jpg"

    def test_issn_skipped_immediately(self, covers_dir):
        client = MagicMock()
        with patch("httpx.Client", return_value=client):
            result = download_cover("issn:0295-7736", covers_dir=covers_dir)
        assert result is None
        client.__enter__.assert_not_called()


# ---------------------------------------------------------------------------
# Amazon — LZZZZZZZ preferred over TZZZZZZZ
# ---------------------------------------------------------------------------

class TestAmazonSizePreference:
    def test_lzzzzzzz_used_before_tzzzzzzz(self, covers_dir):
        data = _image()
        url_order = []

        def get_side_effect(url, **kwargs):
            url_order.append(url)
            r = MagicMock()
            r.status_code = 200
            r.content = data
            r.headers = {"content-type": "image/jpeg"}
            return r

        client = MagicMock()
        client.get.side_effect = get_side_effect
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        with patch("httpx.Client", return_value=client):
            download_cover("2211056466", covers_dir=covers_dir)

        amazon_urls = [u for u in url_order if "amazon" in u]
        assert amazon_urls, "No Amazon URLs requested"
        assert "LZZZZZZZ" in amazon_urls[0], f"First Amazon URL should be LZZZZZZZ, got {amazon_urls[0]}"


# ---------------------------------------------------------------------------
# Open Library — ISBN-13 preferred
# ---------------------------------------------------------------------------

class TestOpenLibraryIsbnPreference:
    def test_isbn13_tried_before_isbn10(self, covers_dir):
        data = _image()
        url_order = []

        def get_side_effect(url, **kwargs):
            url_order.append(url)
            r = MagicMock()
            # Amazon misses, OL hits
            if "amazon" in url or "media-amazon" in url:
                r.status_code = 404
                r.content = b""
                r.headers = {"content-type": "text/plain"}
            else:
                r.status_code = 200
                r.content = data
                r.headers = {"content-type": "image/jpeg"}
            return r

        client = MagicMock()
        client.get.side_effect = get_side_effect
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        with patch("httpx.Client", return_value=client):
            download_cover("2211056466", covers_dir=covers_dir)

        ol_urls = [u for u in url_order if "openlibrary" in u]
        assert ol_urls, "No Open Library URLs requested"
        assert "9782211056465" in ol_urls[0], "ISBN-13 should be tried first at Open Library"


# ---------------------------------------------------------------------------
# configure() affects google_api provider
# ---------------------------------------------------------------------------

class TestConfigureIntegration:
    def test_api_key_passed_to_google_provider(self, covers_dir):
        configure(google_api_key="SECRET_KEY")
        params_used = {}

        def get_side_effect(url, **kwargs):
            params_used.update(kwargs.get("params", {}))
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = {"totalItems": 0}
            r.content = b""
            r.headers = {"content-type": "application/json"}
            return r

        client = MagicMock()
        client.get.side_effect = get_side_effect
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        with patch("httpx.Client", return_value=client):
            # Amazon and OL miss → hits Google API
            with patch("src.bcd_api.services.cover_service._try_amazon", return_value=None), \
                 patch("src.bcd_api.services.cover_service._try_openlibrary", return_value=None):
                download_cover("9782211056465", covers_dir=covers_dir)

        assert params_used.get("key") == "SECRET_KEY"


# ---------------------------------------------------------------------------
# Integration with catalog_service._download_cover
# ---------------------------------------------------------------------------

class TestCatalogServiceIntegration:
    """Verify that catalog_service._download_cover delegates to cover_service."""

    def test_download_cover_delegates_to_cover_service(self, covers_dir):
        from src.bcd_api.services.catalog_service import _download_cover

        with patch("src.bcd_api.services.cover_service.download_cover") as mock_dl:
            mock_dl.return_value = "2211056466.jpg"
            result = _download_cover("2211056466")

        mock_dl.assert_called_once()
        assert result == "2211056466.jpg"

    def test_issn_skipped_by_cover_service(self):
        from src.bcd_api.services.catalog_service import _download_cover
        # The issn: guard lives inside cover_service.download_cover.
        # catalog_service._download_cover delegates unconditionally and
        # returns whatever cover_service returns (None for ISSNs).
        with patch("src.bcd_api.services.cover_service.download_cover",
                   return_value=None) as mock_dl:
            result = _download_cover("issn:0295-7736")
        assert result is None
        mock_dl.assert_called_once()

    def test_none_isbn_returns_none(self):
        from src.bcd_api.services.catalog_service import _download_cover
        result = _download_cover(None)
        assert result is None
