"""BNF SRU API Integration Service

This module provides integration with the BNF (Bibliothèque nationale de France)
SRU API for ISBN-based bibliographic record lookup using UNIMARC format.

Reference: /specs/001-school-library-system/contracts/bnf-sru-api.md
"""

import logging
import re
import time
from typing import Optional

from ....shared.constants import MediumType, TargetAudience
from ....shared.validators import clean_call_number

logger = logging.getLogger(__name__)

# BNF SRU API endpoint (overridable via configure())
_BNF_URL = "https://catalogue.bnf.fr/api/SRU"

# Rate limiting: 1 request per second
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 1.0


def configure(url: str | None = None, rate_limit: int = 1) -> None:
    """Configure BNF service — call once at startup with values from settings.

    Args:
        url: Override the BNF SRU endpoint (useful for testing).
        rate_limit: Maximum requests per second (default: 1).
    """
    global _BNF_URL, _MIN_REQUEST_INTERVAL
    if url:
        _BNF_URL = url
    _MIN_REQUEST_INTERVAL = 1.0 / max(rate_limit, 1)


def _rate_limit() -> None:
    """Enforce minimum interval between API calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _normalize_isbn(isbn: str) -> str:
    """
    Normalize ISBN by removing hyphens and spaces.

    Args:
        isbn: ISBN-10 or ISBN-13 (may include hyphens)

    Returns:
        Normalized ISBN (digits only)
    """
    return isbn.replace("-", "").replace(" ", "").strip()


def _extract_text(element, xpath: str, namespaces: dict) -> Optional[str]:
    """Extract text from XML element using XPath."""
    result = element.find(xpath, namespaces)
    return result.text if result is not None else None


def _extract_all_text(element, xpath: str, namespaces: dict) -> list[str]:
    """Extract all text values from XML elements using XPath."""
    results = element.findall(xpath, namespaces)
    return [r.text for r in results if r.text]


def _parse_author_name(surname: Optional[str], forename: Optional[str]) -> Optional[str]:
    """Parse author name from surname and forename."""
    if surname and forename:
        return f"{surname}, {forename}"
    elif surname:
        return surname
    elif forename:
        return forename
    return None


def _parse_author_statement(statement: str) -> Optional[str]:
    """Extract author name from statement like 'une histoire de Dominique Petit'."""
    patterns = [
        r"(?:une histoire (?:de|par))\s+(.+?)(?:\s*;|$)",
        r"(?:écrit (?:par))\s+(.+?)(?:\s*;|$)",
        r"(?:par)\s+(.+?)(?:\s*;|$)",
        r"(?:de)\s+(.+?)(?:\s*;|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, statement, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    if len(statement) < 50:
        return statement.strip()

    return None


def _parse_page_count(extent: str) -> Optional[int]:
    """Extract page count from extent field like '83 p.' or '1 vol. (352 p.)'."""
    patterns = [
        r"(\d+)\s*p\.",
        r"\((\d+)\s*p\.\)",
    ]

    for pattern in patterns:
        match = re.search(pattern, extent)
        if match:
            return int(match.group(1))

    return None


def _parse_binding_type(binding_code: str) -> Optional[str]:
    """Parse binding type from 010$b code."""
    binding_map = {
        "rel.": "hardcover",
        "relié": "hardcover",
        "cart.": "hardcover",
        "cartonné": "hardcover",
        "br.": "paperback",
        "broché": "paperback",
    }
    return binding_map.get(binding_code.lower().strip())


def _has_illustrations(illustration_field: str) -> bool:
    """Check if book has illustrations based on 215$c field."""
    return "ill" in illustration_field.lower()


def parse_unimarc_xml(xml_content: bytes) -> Optional[dict]:
    """
    Parse UNIMARC XML response from BNF SRU API.

    Args:
        xml_content: XML response bytes

    Returns:
        Dictionary with bibliographic data or None if parsing failed

    Reference: /specs/001-school-library-system/contracts/bnf-sru-api.md
    """
    try:
        from lxml import etree  # lazy — only loaded on first ISBN lookup

        root = etree.fromstring(xml_content)

        # Define namespaces
        ns = {"srw": "http://www.loc.gov/zing/srw/", "mxc": "info:lc/xmlns/marcxchange-v2"}

        # Check number of records
        num_records_elem = root.find(".//srw:numberOfRecords", ns)
        if num_records_elem is None:
            logger.error("No numberOfRecords element in BNF response")
            return None

        num_records = int(num_records_elem.text)
        if num_records == 0:
            logger.info("ISBN not found in BNF catalog (0 records)")
            return None

        # Get first record
        marc_record = root.find(".//mxc:record", ns)
        if marc_record is None:
            logger.error("No UNIMARC record found in response")
            return None

        # Extract bibliographic data
        data = {}

        # ISBN (010$a)
        isbn_elem = marc_record.find('.//mxc:datafield[@tag="010"]/mxc:subfield[@code="a"]', ns)
        if isbn_elem is not None:
            data["isbn"] = _normalize_isbn(isbn_elem.text)

        # Binding type (010$b)
        binding_elem = marc_record.find('.//mxc:datafield[@tag="010"]/mxc:subfield[@code="b"]', ns)
        if binding_elem is not None:
            data["binding_type"] = _parse_binding_type(binding_elem.text)

        # Language (101$a) — normalize ISO 639-2 (3-letter) to ISO 639-1 (2-letter)
        _iso3_to_2 = {
            "fre": "fr",
            "eng": "en",
            "ger": "de",
            "spa": "es",
            "ita": "it",
            "por": "pt",
            "ara": "ar",
            "chi": "zh",
            "rus": "ru",
            "dut": "nl",
            "pol": "pl",
        }
        lang_elem = marc_record.find('.//mxc:datafield[@tag="101"]/mxc:subfield[@code="a"]', ns)
        if lang_elem is not None:
            lang = lang_elem.text
            data["language"] = _iso3_to_2.get(lang, lang)

        # Country (102$a)
        country_elem = marc_record.find('.//mxc:datafield[@tag="102"]/mxc:subfield[@code="a"]', ns)
        if country_elem is not None:
            data["country_code"] = country_elem.text

        # Title and subtitle (200$a, 200$e)
        title_elem = marc_record.find('.//mxc:datafield[@tag="200"]/mxc:subfield[@code="a"]', ns)
        if title_elem is not None:
            data["title"] = title_elem.text

        subtitle_elem = marc_record.find('.//mxc:datafield[@tag="200"]/mxc:subfield[@code="e"]', ns)
        if subtitle_elem is not None:
            data["subtitle"] = subtitle_elem.text

        # Author statement (200$f)
        author_stmt_elem = marc_record.find(
            './/mxc:datafield[@tag="200"]/mxc:subfield[@code="f"]', ns
        )
        author_from_stmt = None
        if author_stmt_elem is not None:
            author_from_stmt = _parse_author_statement(author_stmt_elem.text)

        # Illustrator statement (200$g)
        illus_stmt_elem = marc_record.find(
            './/mxc:datafield[@tag="200"]/mxc:subfield[@code="g"]', ns
        )
        illus_from_stmt = None
        if illus_stmt_elem is not None:
            illus_text = illus_stmt_elem.text
            if "ill" in illus_text.lower():
                match = re.search(
                    r"(?:ill\.|illustré)\s*(?:par)?\s*(.+)", illus_text, re.IGNORECASE
                )
                if match:
                    illus_from_stmt = match.group(1).strip()

        # Publisher and year (210$c, 210$d)
        publisher_elem = marc_record.find(
            './/mxc:datafield[@tag="210"]/mxc:subfield[@code="c"]', ns
        )
        if publisher_elem is not None:
            data["publisher"] = publisher_elem.text

        year_elem = marc_record.find('.//mxc:datafield[@tag="210"]/mxc:subfield[@code="d"]', ns)
        if year_elem is not None:
            year_text = year_elem.text
            match = re.search(r"(\d{4})", year_text)
            if match:
                data["publication_year"] = int(match.group(1))

        # Physical description (215$a, 215$c, 215$d)
        extent_elem = marc_record.find('.//mxc:datafield[@tag="215"]/mxc:subfield[@code="a"]', ns)
        if extent_elem is not None:
            extent_text = extent_elem.text
            data["page_count"] = _parse_page_count(extent_text)

            physical_parts = [extent_text]

            # Illustrations (215$c)
            illus_elem = marc_record.find(
                './/mxc:datafield[@tag="215"]/mxc:subfield[@code="c"]', ns
            )
            if illus_elem is not None:
                illus_text = illus_elem.text
                data["has_illustrations"] = _has_illustrations(illus_text)
                physical_parts.append(illus_text)
            else:
                data["has_illustrations"] = False

            # Dimensions (215$d)
            dim_elem = marc_record.find('.//mxc:datafield[@tag="215"]/mxc:subfield[@code="d"]', ns)
            if dim_elem is not None:
                dim_text = dim_elem.text
                data["dimensions"] = dim_text
                physical_parts.append(dim_text)

            data["physical_size"] = ", ".join(physical_parts)

        # Series (225$a, 225$v)
        series_elem = marc_record.find('.//mxc:datafield[@tag="225"]/mxc:subfield[@code="a"]', ns)
        if series_elem is not None:
            data["collection"] = series_elem.text

        series_num_elem = marc_record.find(
            './/mxc:datafield[@tag="225"]/mxc:subfield[@code="v"]', ns
        )
        if series_num_elem is not None:
            data["series_number"] = series_num_elem.text

        # Summary (330$a)
        summary_elem = marc_record.find('.//mxc:datafield[@tag="330"]/mxc:subfield[@code="a"]', ns)
        if summary_elem is not None:
            data["description"] = summary_elem.text

        # Subject headings / keywords (606$a)
        keywords = _extract_all_text(
            marc_record, './/mxc:datafield[@tag="606"]/mxc:subfield[@code="a"]', ns
        )
        if keywords:
            data["keywords"] = keywords

        # Dewey classification number (676$a)
        dewey_elem = marc_record.find('.//mxc:datafield[@tag="676"]/mxc:subfield[@code="a"]', ns)
        if dewey_elem is not None and dewey_elem.text:
            data["dewey_number"] = clean_call_number(dewey_elem.text.strip())

        # Authors (700$a, 700$b, 701$a, 701$b)
        authors = []

        # Primary author (700)
        surname_700 = _extract_text(
            marc_record, './/mxc:datafield[@tag="700"]/mxc:subfield[@code="a"]', ns
        )
        forename_700 = _extract_text(
            marc_record, './/mxc:datafield[@tag="700"]/mxc:subfield[@code="b"]', ns
        )
        author_700 = _parse_author_name(surname_700, forename_700)
        if author_700:
            authors.append(author_700)

        # Additional authors (701)
        for datafield in marc_record.findall('.//mxc:datafield[@tag="701"]', ns):
            surname = _extract_text(datafield, './/mxc:subfield[@code="a"]', ns)
            forename = _extract_text(datafield, './/mxc:subfield[@code="b"]', ns)
            author = _parse_author_name(surname, forename)
            if author:
                authors.append(author)

        # Fallback to author from statement if no authors found
        if not authors and author_from_stmt:
            authors.append(author_from_stmt)

        if authors:
            data["authors"] = authors

        # Illustrators (702$a, 702$b)
        illustrators = []
        for datafield in marc_record.findall('.//mxc:datafield[@tag="702"]', ns):
            surname = _extract_text(datafield, './/mxc:subfield[@code="a"]', ns)
            forename = _extract_text(datafield, './/mxc:subfield[@code="b"]', ns)
            illustrator = _parse_author_name(surname, forename)
            if illustrator:
                illustrators.append(illustrator)

        # Fallback to illustrator from statement
        if not illustrators and illus_from_stmt:
            illustrators.append(illus_from_stmt)

        if illustrators:
            data["illustrators"] = illustrators

        # Default medium type (not in BNF data)
        data["medium_type"] = MediumType.LIVRE.value

        # Target audience (default for primary school books)
        data["target_audience"] = TargetAudience.CHILD.value

        logger.info(f"Successfully parsed BNF data for ISBN {data.get('isbn')}")
        return data

    except Exception as e:
        logger.exception(f"Error parsing UNIMARC XML: {e}")
        return None


def search_by_isbn(isbn: str, timeout: int = 10) -> Optional[dict]:
    """
    Search BNF catalog by ISBN and return bibliographic data.

    Args:
        isbn: ISBN-10 or ISBN-13 (with or without hyphens)
        timeout: Request timeout in seconds

    Returns:
        Dictionary with bibliographic metadata or None if not found

    Raises:
        httpx.HTTPError: If network error occurs (caller should handle)

    Example:
        >>> data = search_by_isbn("978-2-8006-8734-6")
        >>> print(data['title'])
        "L'équipe des mascrottes"

    Reference: /specs/001-school-library-system/contracts/bnf-sru-api.md
    """
    import httpx  # lazy — only loaded on first ISBN lookup

    isbn_normalized = _normalize_isbn(isbn)

    if not isbn_normalized:
        logger.warning(f"Invalid ISBN: {isbn}")
        return None

    # Build query
    query = f'bib.isbn all "{isbn_normalized}"'

    # Build request parameters
    params = {
        "version": "1.2",
        "operation": "searchRetrieve",
        "query": query,
        "recordSchema": "unimarcxchange",
        "maximumRecords": "1",
    }

    try:
        # Rate limiting
        _rate_limit()

        # Make request
        logger.info(f"Searching BNF for ISBN: {isbn_normalized}")

        with httpx.Client() as client:
            response = client.get(_BNF_URL, params=params, timeout=timeout)
            response.raise_for_status()

        # Parse response
        return parse_unimarc_xml(response.content)

    except httpx.TimeoutException:
        logger.error(f"BNF API timeout for ISBN {isbn_normalized}")
        raise

    except httpx.HTTPStatusError as e:
        logger.error(f"BNF API HTTP error: {e.response.status_code}")
        raise

    except httpx.HTTPError as e:
        logger.error(f"BNF API error: {e}")
        raise
