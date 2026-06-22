"""Unit tests for SUDOC SRU API service."""

from unittest.mock import Mock, patch

import httpx
import pytest

from src.bcd_api.services.sudoc_service import (
    ISSN_PATTERN,
    _parse_pica_record,
    _parse_year,
    _pica_title,
    configure,
    search_by_isbn,
    search_by_issn,
    search_by_title_author,
)

# ---------------------------------------------------------------------------
# Minimal Pica+ XML helpers
# ---------------------------------------------------------------------------

def _pica_xml(fields: list[tuple[str, str, str]]) -> bytes:
    """Build a minimal picaXML record for testing.

    Args:
        fields: list of (tag, code, value) tuples
    """
    ns = 'xmlns="info:srw/schema/5/picaXML-v1.0"'
    parts = [f'<record {ns}>']
    for tag, code, value in fields:
        parts.append(
            f'  <datafield tag="{tag}">'
            f'<subfield code="{code}">{value}</subfield>'
            f'</datafield>'
        )
    parts.append('</record>')
    return "\n".join(parts).encode()


def _sru_response(records_xml: list[bytes], total: int | None = None) -> bytes:
    """Wrap Pica+ records in a minimal SRU searchRetrieveResponse."""
    count = total if total is not None else len(records_xml)
    pica_ns = "info:srw/schema/5/picaXML-v1.0"
    body_parts = []
    for rec in records_xml:
        body_parts.append(
            '<srw:record>'
            '<srw:recordData>'
            + rec.decode()
            + '</srw:recordData>'
            '</srw:record>'
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/"
                             xmlns:pica="{pica_ns}">
  <srw:numberOfRecords>{count}</srw:numberOfRecords>
  <srw:records>
    {"".join(body_parts)}
  </srw:records>
</srw:searchRetrieveResponse>""".encode()


def _empty_sru_response() -> bytes:
    """SRU response with zero results."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>0</srw:numberOfRecords>
  <srw:records/>
</srw:searchRetrieveResponse>"""


SAMPLE_RECORD = _pica_xml([
    ("021A", "a", "L' @imagerie du corps"),
    ("028A", "8", "Beaumont, Emilie"),
    ("033A", "n", "Fleurus"),
    ("011@", "a", "2005"),
    ("010@", "a", "fre"),
    ("004A", "A", "9782215065340"),
])


def _mock_client(content: bytes):
    """Return a mock httpx.Client that returns the given bytes."""
    mock_response = Mock()
    mock_response.content = content
    mock_client = Mock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    return mock_client


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_pica_title_strips_at_prefix(self):
        assert _pica_title("L' @imagerie du corps") == "L'imagerie du corps"

    def test_pica_title_no_at(self):
        assert _pica_title("Stuart Little") == "Stuart Little"

    def test_pica_title_at_at_start(self):
        assert _pica_title("@Le petit prince") == "Le petit prince"

    def test_parse_year_extracts_4_digits(self):
        assert _parse_year("2005") == 2005

    def test_parse_year_handles_text(self):
        assert _parse_year("DL 2005") == 2005

    def test_parse_year_none(self):
        assert _parse_year(None) is None

    def test_parse_year_no_year(self):
        assert _parse_year("unknown") is None

    def test_issn_pattern_valid(self):
        assert ISSN_PATTERN.match("1147-3371") is not None

    def test_issn_pattern_x_check(self):
        assert ISSN_PATTERN.match("0000-000X") is not None

    def test_issn_pattern_invalid_no_hyphen(self):
        assert ISSN_PATTERN.match("11473371") is None

    def test_issn_pattern_isbn_rejected(self):
        assert ISSN_PATTERN.match("9782215065340") is None


# ---------------------------------------------------------------------------
# Pica+ record parsing
# ---------------------------------------------------------------------------

class TestParsePicaRecord:
    def test_parse_basic_fields(self):
        result = _parse_pica_record(SAMPLE_RECORD)
        assert result is not None
        assert result["title"] == "L'imagerie du corps"
        assert result["authors"] == ["Beaumont, Emilie"]
        assert result["publisher"] == "Fleurus"
        assert result["publication_year"] == 2005
        assert result["language"] == "fr"
        assert result["isbn"] == "9782215065340"

    def test_parse_medium_type_default(self):
        result = _parse_pica_record(SAMPLE_RECORD)
        assert result["medium_type"] == "Livre"

    def test_parse_no_title_returns_none(self):
        rec = _pica_xml([("033A", "n", "Fleurus")])
        result = _parse_pica_record(rec)
        assert result is None

    def test_parse_iso3_language_normalised(self):
        rec = _pica_xml([
            ("021A", "a", "Stuart Little"),
            ("010@", "a", "eng"),
        ])
        result = _parse_pica_record(rec)
        assert result["language"] == "en"

    def test_parse_issn_field(self):
        rec = _pica_xml([
            ("021A", "a", "J'aime lire"),
            ("005A", "0", "1147-3371"),
        ])
        result = _parse_pica_record(rec)
        assert result["issn"] == "1147-3371"

    def test_parse_series(self):
        rec = _pica_xml([
            ("021A", "a", "Les petits débrouillards"),
            ("036C", "a", "@Bibliothèque verte"),
        ])
        result = _parse_pica_record(rec)
        assert result["collection"] == "Bibliothèque verte"


# ---------------------------------------------------------------------------
# search_by_isbn
# ---------------------------------------------------------------------------

class TestSearchByISBN:
    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_found(self, mock_client_class, mock_rate_limit):
        content = _sru_response([SAMPLE_RECORD])
        mock_client_class.return_value = _mock_client(content)
        result = search_by_isbn("978-2-215-06534-0")
        assert result is not None
        assert result["title"] == "L'imagerie du corps"
        assert result["_source"] == "sudoc"

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_not_found(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        result = search_by_isbn("9999999999999")
        assert result is None

    def test_empty_isbn_returns_none(self):
        result = search_by_isbn("")
        assert result is None

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_query_uses_isb_index(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        search_by_isbn("9782215065340")
        call_kwargs = mock_client_class.return_value.get.call_args
        assert "isb=9782215065340" in call_kwargs[1]["params"]["query"]

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_timeout_raises(self, mock_client_class, mock_rate_limit):
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        with pytest.raises(httpx.TimeoutException):
            search_by_isbn("9782215065340")


# ---------------------------------------------------------------------------
# search_by_issn
# ---------------------------------------------------------------------------

class TestSearchByISSN:
    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_found(self, mock_client_class, mock_rate_limit):
        rec = _pica_xml([
            ("021A", "a", "J'aime lire"),
            ("005A", "0", "1147-3371"),
            ("010@", "a", "fre"),
        ])
        content = _sru_response([rec])
        mock_client_class.return_value = _mock_client(content)
        result = search_by_issn("1147-3371")
        assert result is not None
        assert result["title"] == "J'aime lire"
        assert result["_source"] == "sudoc"

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_not_found(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        result = search_by_issn("0000-0000")
        assert result is None

    def test_invalid_issn_returns_none(self):
        result = search_by_issn("not-an-issn")
        assert result is None

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_query_uses_isn_index(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        search_by_issn("1147-3371")
        call_kwargs = mock_client_class.return_value.get.call_args
        assert "isn=1147-3371" in call_kwargs[1]["params"]["query"]


# ---------------------------------------------------------------------------
# search_by_title_author
# ---------------------------------------------------------------------------

class TestSearchByTitleAuthor:
    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_found_confident(self, mock_client_class, mock_rate_limit):
        rec = _pica_xml([
            ("021A", "a", "L' @imagerie du corps"),
            ("028A", "8", "Beaumont, Emilie"),
            ("010@", "a", "fre"),
        ])
        content = _sru_response([rec])
        mock_client_class.return_value = _mock_client(content)
        result = search_by_title_author("L'imagerie du corps", "Beaumont")
        assert result is not None
        assert "_confidence" in result
        assert result["_source"] == "sudoc"

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_strips_issue_number(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        search_by_title_author("J'aime lire n° 228", "")
        call_kwargs = mock_client_class.return_value.get.call_args
        query = call_kwargs[1]["params"]["query"]
        # "n° 228" should be stripped — query should contain "jaime" and "lire"
        assert "228" not in query

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_low_score_returns_none(self, mock_client_class, mock_rate_limit):
        # Query "Les Misérables" but SUDOC returns "Stuart Little"
        rec = _pica_xml([
            ("021A", "a", "Stuart Little"),
            ("028A", "8", "White, E.B."),
        ])
        content = _sru_response([rec])
        mock_client_class.return_value = _mock_client(content)
        result = search_by_title_author("Les Misérables", "Hugo")
        assert result is None

    def test_empty_title_returns_none(self):
        result = search_by_title_author("", "White")
        assert result is None

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_no_results_returns_none(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        result = search_by_title_author("Livre introuvable", "Inconnu")
        assert result is None

    @patch("src.bcd_api.services.sudoc_service._rate_limit")
    @patch("httpx.Client")
    def test_query_uses_mti_index(self, mock_client_class, mock_rate_limit):
        mock_client_class.return_value = _mock_client(_empty_sru_response())
        search_by_title_author("Stuart Little", "White")
        call_kwargs = mock_client_class.return_value.get.call_args
        query = call_kwargs[1]["params"]["query"]
        assert "mti=" in query
        assert "aut=" in query


# ---------------------------------------------------------------------------
# configure()
# ---------------------------------------------------------------------------

class TestConfigure:
    def test_configure_url(self):
        from src.bcd_api.services import sudoc_service
        configure(url="http://mock-sudoc.example.com/sru/")
        assert sudoc_service._SUDOC_URL == "http://mock-sudoc.example.com/sru/"
        # Restore default
        configure(url="https://www.sudoc.abes.fr/cbs/sru/")

    def test_configure_rate_limit(self):
        from src.bcd_api.services import sudoc_service
        configure(rate_limit=2)
        assert sudoc_service._MIN_REQUEST_INTERVAL == pytest.approx(0.5)
        configure(rate_limit=1)
