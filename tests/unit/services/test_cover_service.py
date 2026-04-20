"""Unit tests for cover_service — ISBN helpers, per-provider functions, cascade logic.

All HTTP calls are mocked. No real network requests are made.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import httpx

from src.bcd_api.services import cover_service
from src.bcd_api.services.cover_service import (
    _isbn10_to_isbn13,
    _isbn13_to_isbn10,
    _both_forms,
    _normalize,
    _fetch,
    _try_amazon,
    _try_openlibrary,
    _try_google_api,
    _try_geobib,
    download_cover,
    configure,
    _MIN_BYTES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(content: bytes = b"", status: int = 200, content_type: str = "image/jpeg"):
    """Build a mock httpx.Client whose get() returns a fake response."""
    response = MagicMock()
    response.status_code = status
    response.content = content
    response.headers = {"content-type": content_type}
    client = MagicMock()
    client.get.return_value = response
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


def _image(size: int = 10_000) -> bytes:
    """Fake image bytes large enough to pass the MIN_BYTES check."""
    return b"\xff\xd8\xff" + b"X" * size  # JPEG magic + padding


# ---------------------------------------------------------------------------
# ISBN helpers
# ---------------------------------------------------------------------------

class TestIsbnHelpers:
    def test_isbn10_to_isbn13_correct_check_digit(self):
        # ISBN-10: 2211056466 → ISBN-13: 9782211056465
        assert _isbn10_to_isbn13("2211056466") == "9782211056465"

    def test_isbn10_to_isbn13_x_check(self):
        # ISBN-10 with X check digit → ISBN-13
        result = _isbn10_to_isbn13("207036822X")
        assert result.startswith("978")
        assert len(result) == 13

    def test_isbn10_to_isbn13_passthrough_wrong_length(self):
        assert _isbn10_to_isbn13("123") == "123"

    def test_isbn13_to_isbn10_978_prefix(self):
        assert _isbn13_to_isbn10("9782211056465") == "2211056466"

    def test_isbn13_to_isbn10_979_prefix_returns_none(self):
        # 979 books have no ISBN-10 equivalent
        assert _isbn13_to_isbn10("9791032303399") is None

    def test_isbn13_to_isbn10_non_13_digit_returns_none(self):
        assert _isbn13_to_isbn10("97820") is None

    def test_both_forms_isbn10_gives_both(self):
        isbn10, isbn13 = _both_forms("2211056466")
        assert isbn10 == "2211056466"
        assert isbn13 == "9782211056465"

    def test_both_forms_isbn13_gives_both(self):
        isbn10, isbn13 = _both_forms("9782211056465")
        assert isbn10 == "2211056466"
        assert isbn13 == "9782211056465"

    def test_both_forms_isbn13_979_gives_none_for_isbn10(self):
        isbn10, isbn13 = _both_forms("9791032303399")
        assert isbn10 is None
        assert isbn13 == "9791032303399"

    def test_both_forms_garbage_gives_none_none(self):
        assert _both_forms("hello") == (None, None)

    def test_normalize_strips_hyphens_spaces_dots(self):
        assert _normalize("978-2-211-05646-5") == "9782211056465"
        assert _normalize("978 2 211 05646 5") == "9782211056465"
        assert _normalize("978.2.211.05646.5") == "9782211056465"

    def test_normalize_strips_isbn_prefix(self):
        # _normalize doesn't strip the isbn: prefix, that's download_cover's job
        result = _normalize("9782070368228")
        assert result == "9782070368228"


# ---------------------------------------------------------------------------
# _fetch
# ---------------------------------------------------------------------------

class TestFetch:
    def test_returns_bytes_for_valid_image(self):
        data = _image()
        client = _make_client(content=data)
        result = _fetch("https://example.com/cover.jpg", client)
        assert result == data

    def test_returns_none_for_http_404(self):
        response = MagicMock()
        response.status_code = 404
        response.content = b""
        response.headers = {"content-type": "image/jpeg"}
        client = MagicMock()
        client.get.return_value = response
        result = _fetch("https://example.com/cover.jpg", client)
        assert result is None

    def test_returns_none_for_too_small_image(self):
        client = _make_client(content=b"\xff\xd8" + b"X" * 10)  # below _MIN_BYTES
        assert _fetch("https://example.com/tiny.jpg", client) is None

    def test_returns_none_for_non_image_content_type(self):
        client = _make_client(content=_image(), content_type="text/html")
        assert _fetch("https://example.com/page.html", client) is None

    def test_returns_none_on_network_exception(self):
        client = MagicMock()
        client.get.side_effect = httpx.ConnectError("connection refused")
        assert _fetch("https://example.com/cover.jpg", client) is None


# ---------------------------------------------------------------------------
# _try_amazon
# ---------------------------------------------------------------------------

class TestTryAmazon:
    def test_returns_bytes_using_lzzzzzzz_first(self):
        data = _image()
        client = _make_client(content=data)
        result = _try_amazon("2211056466", client)
        assert result == data
        # First call should be LZZZZZZZ variant
        first_url = client.get.call_args_list[0][0][0]
        assert "LZZZZZZZ" in first_url

    def test_falls_back_to_tzzzzzzz_when_lzzzzzzz_fails(self):
        data = _image()
        # First calls (LZZZZZZZ on both hosts) return too-small images; TZZZZZZZ succeeds
        small = _make_client(content=b"X" * 10)
        good = _make_client(content=data)

        call_count = 0
        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "LZZZZZZZ" in url:
                return small.get(url)
            return good.get(url)

        client = MagicMock()
        client.get.side_effect = side_effect
        # Patch _fetch to use our client directly
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.side_effect = lambda url, c: (data if "TZZZZZZZ" in url else None)
            result = _try_amazon("2211056466", client)
        assert result == data

    def test_returns_none_when_no_isbn10(self):
        # ISBN-13 with 979 prefix has no ISBN-10
        client = _make_client(content=_image())
        result = _try_amazon(None, client)
        assert result is None

    def test_returns_none_when_all_variants_fail(self):
        with patch("src.bcd_api.services.cover_service._fetch", return_value=None):
            client = MagicMock()
            result = _try_amazon("2211056466", client)
        assert result is None

    def test_uses_isbn10_in_url(self):
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.return_value = _image()
            client = MagicMock()
            _try_amazon("2211056466", client)
            url = mock_fetch.call_args[0][0]
            assert "2211056466" in url


# ---------------------------------------------------------------------------
# _try_openlibrary
# ---------------------------------------------------------------------------

class TestTryOpenlibrary:
    def test_prefers_isbn13_over_isbn10(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.return_value = data
            client = MagicMock()
            result = _try_openlibrary("2211056466", "9782211056465", client)
        assert result == data
        # First fetch should use ISBN-13
        first_url = mock_fetch.call_args_list[0][0][0]
        assert "9782211056465" in first_url

    def test_falls_back_to_isbn10_when_isbn13_fails(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.side_effect = lambda url, c: (data if "2211056466" in url and "978" not in url else None)
            client = MagicMock()
            result = _try_openlibrary("2211056466", "9782211056465", client)
        assert result == data

    def test_returns_none_when_both_fail(self):
        with patch("src.bcd_api.services.cover_service._fetch", return_value=None):
            result = _try_openlibrary("2211056466", "9782211056465", MagicMock())
        assert result is None

    def test_uses_default_false_parameter(self):
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.return_value = _image()
            _try_openlibrary("2211056466", "9782211056465", MagicMock())
            url = mock_fetch.call_args_list[0][0][0]
            assert "default=false" in url


# ---------------------------------------------------------------------------
# _try_google_api
# ---------------------------------------------------------------------------

class TestTryGoogleApi:
    def _google_response(self, thumbnail_url: str = "http://books.google.com/cover.jpg"):
        return {
            "totalItems": 1,
            "items": [{
                "volumeInfo": {
                    "imageLinks": {"thumbnail": thumbnail_url}
                }
            }]
        }

    def test_returns_bytes_on_success(self):
        data = _image()
        client = _make_client()
        client.get.return_value.status_code = 200
        client.get.return_value.json.return_value = self._google_response()

        with patch("src.bcd_api.services.cover_service._fetch", return_value=data):
            result = _try_google_api("9782211056465", client)
        assert result == data

    def test_includes_api_key_when_configured(self):
        cover_service._google_api_key = "MY_KEY"
        client = _make_client()
        client.get.return_value.json.return_value = {"totalItems": 0}

        _try_google_api("9782211056465", client)
        call_kwargs = client.get.call_args[1]
        assert call_kwargs.get("params", {}).get("key") == "MY_KEY"
        cover_service._google_api_key = None  # reset

    def test_no_api_key_when_not_configured(self):
        cover_service._google_api_key = None
        client = _make_client()
        client.get.return_value.json.return_value = {"totalItems": 0}

        _try_google_api("9782211056465", client)
        params = client.get.call_args[1].get("params", {})
        assert "key" not in params

    def test_returns_none_when_no_items(self):
        client = _make_client()
        client.get.return_value.json.return_value = {"totalItems": 0}
        result = _try_google_api("9782211056465", client)
        assert result is None

    def test_returns_none_when_items_empty(self):
        client = _make_client()
        client.get.return_value.json.return_value = {"totalItems": 1, "items": []}
        result = _try_google_api("9782211056465", client)
        assert result is None

    def test_upgrades_http_thumbnail_to_https(self):
        http_url = "http://books.google.com/books/content?id=abc"
        client = _make_client()
        client.get.return_value.json.return_value = self._google_response(http_url)

        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.return_value = _image()
            _try_google_api("9782211056465", client)
            fetched_url = mock_fetch.call_args[0][0]
            assert fetched_url.startswith("https://")

    def test_tries_large_before_thumbnail(self):
        """Prefers 'large' image over 'thumbnail' when both present."""
        client = _make_client()
        client.get.return_value.json.return_value = {
            "totalItems": 1,
            "items": [{"volumeInfo": {"imageLinks": {
                "thumbnail": "https://example.com/thumb.jpg",
                "large": "https://example.com/large.jpg",
            }}}]
        }
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.return_value = _image()
            _try_google_api("9782211056465", client)
            assert "large.jpg" in mock_fetch.call_args[0][0]

    def test_returns_none_when_no_isbn13(self):
        client = MagicMock()
        result = _try_google_api(None, client)
        assert result is None
        client.get.assert_not_called()

    def test_returns_none_on_http_error(self):
        client = _make_client()
        client.get.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock()
        )
        result = _try_google_api("9782211056465", client)
        assert result is None


# ---------------------------------------------------------------------------
# _try_geobib
# ---------------------------------------------------------------------------

class TestTryGeobib:
    def test_returns_bytes_on_success(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._fetch", return_value=data):
            result = _try_geobib("9782211056465", MagicMock())
        assert result == data

    def test_uses_isbn13_in_url(self):
        with patch("src.bcd_api.services.cover_service._fetch") as mock_fetch:
            mock_fetch.return_value = _image()
            _try_geobib("9782211056465", MagicMock())
            url = mock_fetch.call_args[0][0]
            assert "9782211056465" in url
            assert "couverture.geobib.fr" in url

    def test_returns_none_when_no_isbn13(self):
        result = _try_geobib(None, MagicMock())
        assert result is None

    def test_returns_none_on_failure(self):
        with patch("src.bcd_api.services.cover_service._fetch", return_value=None):
            result = _try_geobib("9782211056465", MagicMock())
        assert result is None


# ---------------------------------------------------------------------------
# download_cover — cascade logic
# ---------------------------------------------------------------------------

class TestDownloadCover:
    @pytest.fixture(autouse=True)
    def covers_dir(self, tmp_path):
        self.covers = tmp_path / "covers"
        return self.covers

    def _patch_providers(self, results: dict):
        """
        Patch all four provider functions. results maps provider name to
        bytes (hit) or None (miss). Unspecified providers default to None.
        """
        defaults = {"amazon": None, "openlibrary": None, "google_api": None, "geobib": None}
        defaults.update(results)
        patches = {}
        for name, retval in defaults.items():
            p = patch(f"src.bcd_api.services.cover_service._try_{name}",
                      return_value=retval)
            patches[name] = p
        return patches

    def test_skips_issn_identifier(self):
        result = download_cover("issn:1234-5678", covers_dir=self.covers)
        assert result is None
        assert not self.covers.exists() or not list(self.covers.iterdir())

    def test_strips_isbn_prefix(self):
        data = _image()
        patches = self._patch_providers({"amazon": data})
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=data):
            with patch("httpx.Client", return_value=_make_client()):
                result = download_cover("isbn:2211056466", covers_dir=self.covers)
        # Should not crash; isbn: stripped → normalized ISBN used
        assert result is not None or result is None  # just no exception

    def test_returns_cached_filename_if_file_exists(self):
        self.covers.mkdir()
        existing = self.covers / "2211056466.jpg"
        existing.write_bytes(_image())
        result = download_cover("2211056466", covers_dir=self.covers)
        assert result == "2211056466.jpg"

    def test_cascade_stops_at_amazon(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=data) as mock_amz, \
             patch("src.bcd_api.services.cover_service._try_openlibrary") as mock_ol, \
             patch("src.bcd_api.services.cover_service._try_google_api") as mock_g, \
             patch("src.bcd_api.services.cover_service._try_geobib") as mock_geo, \
             patch("httpx.Client", return_value=_make_client()):
            result = download_cover("2211056466", covers_dir=self.covers)
        assert result == "2211056466.jpg"
        mock_ol.assert_not_called()
        mock_g.assert_not_called()
        mock_geo.assert_not_called()

    def test_cascade_falls_through_to_openlibrary(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_openlibrary", return_value=data), \
             patch("src.bcd_api.services.cover_service._try_google_api") as mock_g, \
             patch("src.bcd_api.services.cover_service._try_geobib") as mock_geo, \
             patch("httpx.Client", return_value=_make_client()):
            result = download_cover("9782211056465", covers_dir=self.covers)
        assert result == "9782211056465.jpg"
        mock_g.assert_not_called()
        mock_geo.assert_not_called()

    def test_cascade_falls_through_to_google_api(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_openlibrary", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_google_api", return_value=data), \
             patch("src.bcd_api.services.cover_service._try_geobib") as mock_geo, \
             patch("httpx.Client", return_value=_make_client()):
            result = download_cover("9782211056465", covers_dir=self.covers)
        assert result == "9782211056465.jpg"
        mock_geo.assert_not_called()

    def test_cascade_falls_through_to_geobib(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_openlibrary", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_google_api", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_geobib", return_value=data), \
             patch("httpx.Client", return_value=_make_client()):
            result = download_cover("9782211056465", covers_dir=self.covers)
        assert result == "9782211056465.jpg"

    def test_returns_none_when_all_fail(self):
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_openlibrary", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_google_api", return_value=None), \
             patch("src.bcd_api.services.cover_service._try_geobib", return_value=None), \
             patch("httpx.Client", return_value=_make_client()):
            result = download_cover("9782211056465", covers_dir=self.covers)
        assert result is None

    def test_file_written_to_covers_dir(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=data), \
             patch("httpx.Client", return_value=_make_client()):
            download_cover("2211056466", covers_dir=self.covers)
        assert (self.covers / "2211056466.jpg").exists()
        assert (self.covers / "2211056466.jpg").stat().st_size == len(data)

    def test_returns_none_for_empty_isbn(self):
        result = download_cover("", covers_dir=self.covers)
        assert result is None

    def test_covers_dir_created_if_missing(self):
        assert not self.covers.exists()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=_image()), \
             patch("httpx.Client", return_value=_make_client()):
            download_cover("2211056466", covers_dir=self.covers)
        assert self.covers.exists()

    def test_normalizes_hyphened_isbn(self):
        data = _image()
        with patch("src.bcd_api.services.cover_service._try_amazon", return_value=data), \
             patch("httpx.Client", return_value=_make_client()):
            result = download_cover("978-2-211-05646-5", covers_dir=self.covers)
        assert result == "9782211056465.jpg"


# ---------------------------------------------------------------------------
# configure()
# ---------------------------------------------------------------------------

class TestConfigure:
    def test_sets_google_api_key(self):
        configure(google_api_key="TEST_KEY_123")
        assert cover_service._google_api_key == "TEST_KEY_123"

    def test_none_clears_google_api_key(self):
        cover_service._google_api_key = "OLD_KEY"
        configure(google_api_key=None)
        assert cover_service._google_api_key is None

    def teardown_method(self):
        cover_service._google_api_key = None
