"""Unit tests for BNF SRU API service."""

from unittest.mock import Mock, patch

import httpx
import pytest

from src.bcd_api.services.bnf_service import (
    _has_illustrations,
    _normalize_isbn,
    _parse_author_name,
    _parse_binding_type,
    _parse_page_count,
    parse_unimarc_xml,
    search_by_isbn,
)


class TestHelperFunctions:
    """Test utility/helper functions."""

    def test_normalize_isbn(self):
        """Test ISBN normalization."""
        assert _normalize_isbn("978-2-8006-8734-6") == "9782800687346"
        assert _normalize_isbn("2-8006-8734-7") == "2800687347"
        assert _normalize_isbn("978 2 8006 8734 6") == "9782800687346"
        assert _normalize_isbn("9782800687346") == "9782800687346"

    def test_parse_page_count(self):
        """Test page count extraction."""
        assert _parse_page_count("83 p.") == 83
        assert _parse_page_count("128 p. ; 21 cm") == 128
        assert _parse_page_count("1 vol. (352 p.)") == 352
        assert _parse_page_count("invalid") is None

    def test_parse_binding_type(self):
        """Test binding type parsing."""
        assert _parse_binding_type("rel.") == "hardcover"
        assert _parse_binding_type("relié") == "hardcover"
        assert _parse_binding_type("cart.") == "hardcover"
        assert _parse_binding_type("br.") == "paperback"
        assert _parse_binding_type("broché") == "paperback"
        assert _parse_binding_type("unknown") is None

    def test_has_illustrations(self):
        """Test illustration detection."""
        assert _has_illustrations("ill. en coul.") is True
        assert _has_illustrations("couv. ill.") is True
        assert _has_illustrations("Illustré par") is True
        assert _has_illustrations("texte seulement") is False
        assert _has_illustrations("sans images") is False

    def test_parse_author_name(self):
        """Test author name parsing."""
        assert _parse_author_name("Petit", "Dominique") == "Petit, Dominique"
        assert _parse_author_name("Rowling", None) == "Rowling"
        assert _parse_author_name(None, "J.K.") == "J.K."
        assert _parse_author_name(None, None) is None


class TestParseUnimarcXML:
    """Test UNIMARC XML parsing."""

    @pytest.fixture
    def sample_unimarc_xml(self):
        """Sample UNIMARC XML response from BNF."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>1</srw:numberOfRecords>
  <srw:records>
    <srw:record>
      <srw:recordData>
        <mxc:record xmlns:mxc="info:lc/xmlns/marcxchange-v2">
          <mxc:datafield tag="010" ind1=" " ind2=" ">
            <mxc:subfield code="a">2-8006-8734-7</mxc:subfield>
            <mxc:subfield code="b">rel.</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="101" ind1="0" ind2=" ">
            <mxc:subfield code="a">fre</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="102" ind1=" " ind2=" ">
            <mxc:subfield code="a">BE</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="200" ind1="1" ind2=" ">
            <mxc:subfield code="a">L'équipe des mascrottes</mxc:subfield>
            <mxc:subfield code="f">une histoire de Dominique Petit</mxc:subfield>
            <mxc:subfield code="g">ill. par Marina Rouzé</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="210" ind1=" " ind2=" ">
            <mxc:subfield code="c">Hemma</mxc:subfield>
            <mxc:subfield code="d">2004</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="215" ind1=" " ind2=" ">
            <mxc:subfield code="a">83 p.</mxc:subfield>
            <mxc:subfield code="c">ill. en coul.</mxc:subfield>
            <mxc:subfield code="d">18 cm</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="225" ind1="|" ind2=" ">
            <mxc:subfield code="a">La mini C</mxc:subfield>
            <mxc:subfield code="v">24</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="330" ind1=" " ind2=" ">
            <mxc:subfield code="a">Pour pouvoir exploiter sa dernière découverte...</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="700" ind1=" " ind2="|">
            <mxc:subfield code="a">Petit</mxc:subfield>
            <mxc:subfield code="b">Dominique</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="702" ind1=" " ind2="|">
            <mxc:subfield code="a">Rouzé</mxc:subfield>
            <mxc:subfield code="b">Marina</mxc:subfield>
          </mxc:datafield>
        </mxc:record>
      </srw:recordData>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>""".encode('utf-8')

    def test_parse_unimarc_success(self, sample_unimarc_xml):
        """Test successful parsing of UNIMARC XML."""
        result = parse_unimarc_xml(sample_unimarc_xml)

        assert result is not None
        assert result["isbn"] == "2800687347"
        assert result["title"] == "L'équipe des mascrottes"
        assert result["publisher"] == "Hemma"
        assert result["publication_year"] == 2004
        assert result["language"] == "fr"
        assert result["country_code"] == "BE"
        assert result["binding_type"] == "hardcover"
        assert result["page_count"] == 83
        assert result["has_illustrations"] is True
        assert result["dimensions"] == "18 cm"
        assert result["collection"] == "La mini C"
        assert result["series_number"] == "24"
        assert result["description"] == "Pour pouvoir exploiter sa dernière découverte..."
        assert result["authors"] == ["Petit, Dominique"]
        assert result["illustrators"] == ["Rouzé, Marina"]
        assert result["medium_type"] == "Livre"
        assert result["target_audience"] == "child"

    def test_parse_unimarc_no_records(self):
        """Test parsing when no records found."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>0</srw:numberOfRecords>
</srw:searchRetrieveResponse>""".encode('utf-8')

        result = parse_unimarc_xml(xml)
        assert result is None

    def test_parse_unimarc_invalid_xml(self):
        """Test parsing invalid XML."""
        invalid_xml = b"<invalid>xml"
        result = parse_unimarc_xml(invalid_xml)
        assert result is None


class TestSearchByISBN:
    """Test ISBN search functionality."""

    @patch("httpx.Client")
    def test_search_by_isbn_success(self, mock_client_class):
        """Test successful ISBN search."""
        # Mock response
        mock_response = Mock()
        mock_response.content = """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>1</srw:numberOfRecords>
  <srw:records>
    <srw:record>
      <srw:recordData>
        <mxc:record xmlns:mxc="info:lc/xmlns/marcxchange-v2">
          <mxc:datafield tag="200" ind1="1" ind2=" ">
            <mxc:subfield code="a">Test Book</mxc:subfield>
          </mxc:datafield>
        </mxc:record>
      </srw:recordData>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>""".encode('utf-8')

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = search_by_isbn("978-2-8006-8734-6")

        assert result is not None
        assert result["title"] == "Test Book"
        mock_client.get.assert_called_once()

    @patch("src.bcd_api.services.bnf_service._rate_limit")
    @patch("httpx.Client")
    def test_search_by_isbn_not_found(self, mock_client_class, mock_rate_limit):
        """Test ISBN not found."""
        mock_response = Mock()
        mock_response.content = """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>0</srw:numberOfRecords>
</srw:searchRetrieveResponse>""".encode('utf-8')

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = search_by_isbn("978-9999-9999-9-9")
        assert result is None

    @patch("src.bcd_api.services.bnf_service._rate_limit")
    @patch("httpx.Client")
    def test_search_by_isbn_timeout(self, mock_client_class, mock_rate_limit):
        """Test timeout handling."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        with pytest.raises(httpx.TimeoutException):
            search_by_isbn("978-2-8006-8734-6")

    @patch("src.bcd_api.services.bnf_service._rate_limit")
    @patch("httpx.Client")
    def test_search_by_isbn_http_error(self, mock_client_class, mock_rate_limit):
        """Test HTTP error handling."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        )
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            search_by_isbn("978-2-8006-8734-6")

    def test_search_by_isbn_invalid_isbn(self):
        """Test invalid ISBN handling."""
        result = search_by_isbn("")
        assert result is None
