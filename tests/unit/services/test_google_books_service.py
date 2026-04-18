"""Unit tests for Google Books API service."""

import pytest
from unittest.mock import patch, Mock
import httpx

from src.bcd_api.services.google_books_service import (
    search_by_isbn,
    search_by_title_author,
    _parse_year,
    _extract_isbn,
    _parse_volume,
    configure,
)
from src.bcd_api.services._catalog_utils import normalize as _normalize, token_overlap as _token_overlap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_volume():
    """Minimal Google Books volume dict."""
    return {
        "kind": "books#volume",
        "id": "abc123",
        "volumeInfo": {
            "title": "Stuart Little",
            "subtitle": "Une souris dans la ville",
            "authors": ["E.B. White"],
            "publisher": "Ecole des loisirs",
            "publishedDate": "2000",
            "description": "<b>M. et Mme Little</b> attendaient un enfant.",
            "industryIdentifiers": [
                {"type": "ISBN_10", "identifier": "2211056466"},
                {"type": "ISBN_13", "identifier": "9782211056465"},
            ],
            "pageCount": 173,
            "categories": ["Juvenile Fiction"],
            "language": "fr",
            "imageLinks": {
                "thumbnail": "https://books.google.com/books/content?id=abc123&zoom=1",
            },
        },
    }


@pytest.fixture
def api_response_one(sample_volume):
    """Google Books API response with one result."""
    return {"totalItems": 1, "items": [sample_volume]}


@pytest.fixture
def api_response_empty():
    """Google Books API response with no results."""
    return {"totalItems": 0}


def _mock_client(json_data):
    """Return a mock httpx.Client that returns json_data."""
    mock_response = Mock()
    mock_response.json.return_value = json_data
    mock_client = Mock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    return mock_client


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_normalize_strips_accents(self):
        assert _normalize("Élémentaire") == "elementaire"

    def test_normalize_strips_punctuation(self):
        assert _normalize("L'Île mystérieuse !") == "l ile mysterieuse"

    def test_normalize_lowercases(self):
        assert _normalize("STUART LITTLE") == "stuart little"

    def test_token_overlap_perfect(self):
        assert _token_overlap("Stuart Little", "Stuart Little") == 1.0

    def test_token_overlap_partial(self):
        # "ville" is in a but not in b → partial overlap
        score = _token_overlap("Stuart Little ville", "Stuart Little")
        assert 0.0 < score < 1.0

    def test_token_overlap_no_match(self):
        assert _token_overlap("Harry Potter", "Stuart Little") == 0.0

    def test_token_overlap_stopwords_only(self):
        # "le" is a stopword — should return 0.5 (uncertain)
        assert _token_overlap("le", "la les") == 0.5

    def test_parse_year_full_date(self):
        assert _parse_year("2003-05-12") == 2003

    def test_parse_year_year_only(self):
        assert _parse_year("2003") == 2003

    def test_parse_year_none(self):
        assert _parse_year(None) is None

    def test_parse_year_invalid(self):
        assert _parse_year("unknown") is None

    def test_extract_isbn_prefers_isbn13(self):
        ids = [
            {"type": "ISBN_10", "identifier": "2211056466"},
            {"type": "ISBN_13", "identifier": "9782211056465"},
        ]
        assert _extract_isbn(ids) == "9782211056465"

    def test_extract_isbn_fallback_isbn10(self):
        ids = [{"type": "ISBN_10", "identifier": "2211056466"}]
        assert _extract_isbn(ids) == "2211056466"

    def test_extract_isbn_empty(self):
        assert _extract_isbn([]) is None


# ---------------------------------------------------------------------------
# Volume parsing
# ---------------------------------------------------------------------------

class TestParseVolume:
    def test_parse_basic_fields(self, sample_volume):
        result = _parse_volume(sample_volume)
        assert result["title"] == "Stuart Little"
        assert result["subtitle"] == "Une souris dans la ville"
        assert result["publisher"] == "Ecole des loisirs"
        assert result["publication_year"] == 2000
        assert result["page_count"] == 173
        assert result["language"] == "fr"
        assert result["isbn"] == "9782211056465"

    def test_parse_author_name_normalised(self, sample_volume):
        result = _parse_volume(sample_volume)
        # "E.B. White" → "White, E.B."
        assert result["authors"] == ["White, E.B."]

    def test_parse_description_strips_html(self, sample_volume):
        result = _parse_volume(sample_volume)
        assert "<b>" not in result["description"]
        assert "M. et Mme Little" in result["description"]

    def test_parse_thumbnail(self, sample_volume):
        result = _parse_volume(sample_volume)
        assert result["cover_url"].startswith("https://books.google.com")

    def test_parse_categories_as_keywords(self, sample_volume):
        result = _parse_volume(sample_volume)
        assert result["keywords"] == ["Juvenile Fiction"]

    def test_parse_medium_type_default(self, sample_volume):
        result = _parse_volume(sample_volume)
        assert result["medium_type"] == "Livre"

    def test_parse_missing_optional_fields(self):
        minimal = {"volumeInfo": {"title": "Minimal Book"}}
        result = _parse_volume(minimal)
        assert result["title"] == "Minimal Book"
        assert "subtitle" not in result
        assert "authors" not in result
        assert "isbn" not in result


# ---------------------------------------------------------------------------
# search_by_isbn
# ---------------------------------------------------------------------------

class TestSearchByISBN:
    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_found(self, mock_client_class, mock_rate_limit, api_response_one):
        mock_client_class.return_value = _mock_client(api_response_one)
        result = search_by_isbn("978-2-211-05646-5")
        assert result is not None
        assert result["title"] == "Stuart Little"
        # Verify correct query param
        call_kwargs = mock_client_class.return_value.get.call_args
        assert "isbn:9782211056465" in call_kwargs[1]["params"]["q"]

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_not_found(self, mock_client_class, mock_rate_limit, api_response_empty):
        mock_client_class.return_value = _mock_client(api_response_empty)
        result = search_by_isbn("9999999999999")
        assert result is None

    def test_empty_isbn_returns_none(self):
        result = search_by_isbn("")
        assert result is None

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_timeout_raises(self, mock_client_class, mock_rate_limit):
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        with pytest.raises(httpx.TimeoutException):
            search_by_isbn("9782211056465")

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_api_key_included_when_configured(self, mock_client_class, mock_rate_limit,
                                               api_response_one):
        configure(api_key="TEST_KEY_123")
        try:
            mock_client_class.return_value = _mock_client(api_response_one)
            search_by_isbn("9782211056465")
            call_kwargs = mock_client_class.return_value.get.call_args
            assert call_kwargs[1]["params"].get("key") == "TEST_KEY_123"
        finally:
            configure(api_key=None)

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_no_api_key_works(self, mock_client_class, mock_rate_limit, api_response_one):
        configure(api_key=None)
        mock_client_class.return_value = _mock_client(api_response_one)
        result = search_by_isbn("9782211056465")
        assert result is not None
        call_kwargs = mock_client_class.return_value.get.call_args
        assert "key" not in call_kwargs[1]["params"]


# ---------------------------------------------------------------------------
# search_by_title_author
# ---------------------------------------------------------------------------

class TestSearchByTitleAuthor:
    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_french_language_restriction(self, mock_client_class, mock_rate_limit,
                                          api_response_empty):
        mock_client_class.return_value = _mock_client(api_response_empty)
        search_by_title_author("Stuart Little", "White")
        call_kwargs = mock_client_class.return_value.get.call_args
        assert call_kwargs[1]["params"].get("langRestrict") == "fr"

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_found_high_confidence(self, mock_client_class, mock_rate_limit,
                                    api_response_one):
        mock_client_class.return_value = _mock_client(api_response_one)
        result = search_by_title_author("Stuart Little", "White")
        assert result is not None
        assert result["title"] == "Stuart Little"
        assert result["_confidence"] == "high"

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_no_results_returns_none(self, mock_client_class, mock_rate_limit,
                                      api_response_empty):
        mock_client_class.return_value = _mock_client(api_response_empty)
        result = search_by_title_author("Livre inexistant", "Auteur inconnu")
        assert result is None

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_low_score_returns_none(self, mock_client_class, mock_rate_limit):
        # Mismatch: searching for "Les Misérables" but API returns "Stuart Little"
        bad_response = {
            "totalItems": 1,
            "items": [{
                "volumeInfo": {
                    "title": "Stuart Little",
                    "authors": ["E.B. White"],
                    "language": "fr",
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9782211056465"}],
                }
            }]
        }
        mock_client_class.return_value = _mock_client(bad_response)
        result = search_by_title_author("Les Misérables", "Hugo")
        assert result is None

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_query_uses_intitle_inauthor(self, mock_client_class, mock_rate_limit,
                                          api_response_empty):
        mock_client_class.return_value = _mock_client(api_response_empty)
        search_by_title_author("Stuart Little", "White")
        call_kwargs = mock_client_class.return_value.get.call_args
        q = call_kwargs[1]["params"]["q"]
        assert "intitle:" in q
        assert "inauthor:" in q

    @patch("src.bcd_api.services.google_books_service._rate_limit")
    @patch("httpx.Client")
    def test_empty_title_returns_none(self, mock_client_class, mock_rate_limit):
        result = search_by_title_author("", "White")
        assert result is None
        mock_client_class.return_value.get.assert_not_called()
