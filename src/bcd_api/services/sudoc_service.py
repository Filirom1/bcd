"""SUDOC SRU API Integration Service

Provides bibliographic lookup via the SUDOC (Système Universitaire de
Documentation) SRU API, as a third-level fallback after BNF and Google Books.
Specialised in French periodicals, older editions, and university collections.

Record format: Pica+ (different from UNIMARC used by BNF)
Protocol: SRU 1.1 — same as BNF but different indexes and record schema

Key SRU indexes:
    isb=<isbn>          ISBN lookup (books)
    isn=<issn>          ISSN lookup (periodicals)
    mti=<word>          Title word(s)
    aut=<word>          Author word(s)

Reference: /specs/001-school-library-system/contracts/sudoc-api.md

Usage:
    from src.bcd_api.services.sudoc_service import (
        search_by_isbn, search_by_issn, search_by_title_author
    )

    data = search_by_isbn("9782011169389")
    data = search_by_issn("1147-3371")
    data = search_by_title_author("J'aime lire", "")
"""

import logging
import re
import time
from typing import Optional

import httpx

from ...shared.constants import MediumType, TargetAudience
from ._catalog_utils import score_match

logger = logging.getLogger(__name__)

# SUDOC SRU endpoint
_SUDOC_URL = "https://www.sudoc.abes.fr/cbs/sru/"

# Rate limiting: 1 request per second
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 1.0

# ISSN pattern: 4 digits, hyphen, 3 digits + check digit (0-9 or X)
ISSN_PATTERN = re.compile(r"^\d{4}-\d{3}[\dX]$")

# Strip issue-number suffixes from periodical titles before title search
# e.g. "J'aime lire n° 228" → "J'aime lire"
_ISSUE_STRIP_RE = re.compile(
    r"\s*(?:n[°o]?\s*\d+|num[eé]ro\s*\d+|vol\.\s*\d+|fascicule\s*\d+|\d{4}/\d+).*$",
    re.IGNORECASE,
)


def configure(url: Optional[str] = None, rate_limit: int = 1) -> None:
    """Call once at startup with values from settings."""
    global _SUDOC_URL, _MIN_REQUEST_INTERVAL
    if url:
        _SUDOC_URL = url
    _MIN_REQUEST_INTERVAL = 1.0 / max(rate_limit, 1)


def _rate_limit() -> None:
    """Enforce minimum interval between API calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _pica_title(raw: str) -> str:
    """Strip the Pica+ sort indicator (@) from a title field.

    SUDOC stores titles as e.g. "L' @imagerie du corps" → "L'imagerie du corps"
    or "Les @P'tites princesses" → "Les P'tites princesses".
    The @ marks the sort start position.
    """
    if "@" not in raw:
        return raw.strip()

    idx = raw.index("@")
    prefix = raw[:idx].rstrip()  # Remove trailing whitespace from prefix
    rest = raw[idx + 1:].lstrip()  # Remove leading whitespace from rest

    # Add space between prefix and rest if prefix doesn't end with punctuation
    if prefix and not prefix[-1] in ("'", "-", " "):
        return f"{prefix} {rest}"
    return prefix + rest


def _parse_year(date_str: Optional[str]) -> Optional[int]:
    """Extract 4-digit year from a Pica+ date field."""
    if not date_str:
        return None
    m = re.search(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def _parse_pica_record(record_xml: str) -> Optional[dict]:
    """Parse a single Pica+ record from SUDOC SRU XML response.

    Pica+ field names use the format NNN@X where NNN is the field tag and
    X is the subfield code. In the SRU XML response they appear as
    <datafield tag="NNN@">...<subfield code="X">value</subfield>.

    Handles both namespaced (old test mocks) and non-namespaced (real API) XML.
    """
    try:
        from lxml import etree

        root = etree.fromstring(record_xml.encode() if isinstance(record_xml, str) else record_xml)

        # Handle both namespaced and non-namespaced XML
        ns_uri = root.nsmap.get(None)  # Default namespace
        ns_prefix = f"{{{ns_uri}}}" if ns_uri else ""

        def _sub(tag: str, code: str) -> Optional[str]:
            # Try with namespace first (for test mocks), then without (for real API)
            elem = root.find(f'.//{ns_prefix}datafield[@tag="{tag}"]/{ns_prefix}subfield[@code="{code}"]')
            if elem is None and ns_prefix:
                # Try without namespace (real SUDOC API)
                elem = root.find(f'.//datafield[@tag="{tag}"]/subfield[@code="{code}"]')
            return elem.text if elem is not None else None

        data: dict = {
            "medium_type": MediumType.LIVRE.value,
            "target_audience": TargetAudience.CHILD.value,
        }

        # Title (021A$a) — strip @ sort indicator
        raw_title = _sub("021A", "a")
        if raw_title:
            data["title"] = _pica_title(raw_title)
        else:
            return None  # no title → discard

        # Subtitle (021A$d)
        raw_sub = _sub("021A", "d")
        if raw_sub:
            data["subtitle"] = _pica_title(raw_sub)

        # Authors (028A$8 is the full display name; also check 028B, 028C)
        authors = []
        for tag in ("028A", "028B", "028C"):
            name = _sub(tag, "8")
            if name:
                authors.append(name)
        if authors:
            data["authors"] = authors

        # Publisher (033A$n)
        publisher = _sub("033A", "n")
        if publisher:
            data["publisher"] = publisher

        # Publication year (011@$a)
        year = _parse_year(_sub("011@", "a"))
        if year:
            data["publication_year"] = year

        # Language (010@$a — ISO 639-2 code, e.g. "fre")
        lang = _sub("010@", "a")
        if lang:
            # Normalise 3-letter ISO to 2-letter for consistency with Google/BNF
            _iso3_to_2 = {"fre": "fr", "eng": "en", "ger": "de", "spa": "es",
                          "ita": "it", "por": "pt", "ara": "ar", "chi": "zh"}
            data["language"] = _iso3_to_2.get(lang, lang)

        # ISBN (004A$A or $B — both are stored without hyphens in SUDOC)
        isbn = _sub("004A", "A") or _sub("004A", "a") or _sub("004A", "B") or _sub("004A", "b")
        if isbn:
            data["isbn"] = isbn.replace("-", "").replace(" ", "")

        # ISSN (005A$0 or 005A$e as fallback)
        issn = _sub("005A", "0") or _sub("005A", "e")
        if issn:
            data["issn"] = issn

        # Series / collection (036C$a)
        series = _sub("036C", "a")
        if series:
            data["collection"] = _pica_title(series)

        return data

    except Exception:
        logger.exception("Error parsing Pica+ record")
        return None


def _parse_sudoc_response(xml_content: bytes) -> list[dict]:
    """Parse SUDOC SRU response and return list of parsed records."""
    try:
        from lxml import etree

        ns = {
            "srw": "http://www.loc.gov/zing/srw/",
        }
        root = etree.fromstring(xml_content)

        num_elem = root.find(".//srw:numberOfRecords", ns)
        if num_elem is None or int(num_elem.text or 0) == 0:
            return []

        records = []
        for record_data in root.findall(".//srw:record", ns):
            # SUDOC returns plain <record> without namespace (not <pica:record>)
            record_data_elem = record_data.find("srw:recordData", ns)
            if record_data_elem is None:
                continue

            # Find the <record> element (may have namespace in test mocks, no namespace in real API)
            record_content = None
            for child in record_data_elem:
                # Match both "record" and "{namespace}record"
                tag = child.tag
                if tag == "record" or tag.endswith("}record"):
                    record_content = child
                    break

            if record_content is None:
                continue

            record_bytes = etree.tostring(record_content)
            parsed = _parse_pica_record(record_bytes)
            if parsed:
                records.append(parsed)

        return records

    except Exception:
        logger.exception("Error parsing SUDOC SRU response")
        return []


def _get(params: dict, timeout: int) -> Optional[bytes]:
    """Execute a single GET request, return response bytes or None."""
    _rate_limit()
    try:
        with httpx.Client() as client:
            response = client.get(_SUDOC_URL, params=params, timeout=timeout)
            response.raise_for_status()
            return response.content
    except httpx.TimeoutException:
        logger.error("SUDOC API timeout")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"SUDOC API HTTP error: {e.response.status_code}")
        raise
    except httpx.HTTPError as e:
        logger.error(f"SUDOC API error: {e}")
        raise


def search_by_isbn(isbn: str, timeout: int = 10) -> Optional[dict]:
    """
    Look up a book by ISBN in SUDOC.

    Args:
        isbn: ISBN-10 or ISBN-13 (hyphens allowed)
        timeout: Request timeout in seconds

    Returns:
        Bibliographic dict (same format as bnf_service output) or None
    """
    normalized = isbn.replace("-", "").replace(" ", "").strip()
    if not normalized:
        logger.warning(f"Invalid ISBN: {isbn}")
        return None

    logger.info(f"Searching SUDOC for ISBN: {normalized}")
    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "query": f"isb={normalized}",
        "recordSchema": "pica",
        "maximumRecords": "1",
    }
    content = _get(params, timeout)
    if not content:
        return None

    records = _parse_sudoc_response(content)
    if not records:
        logger.info(f"ISBN {normalized} not found in SUDOC")
        return None

    result = records[0]
    result["_source"] = "sudoc"
    return result


def search_by_issn(issn: str, timeout: int = 10) -> Optional[dict]:
    """
    Look up a periodical by ISSN in SUDOC.

    Args:
        issn: ISSN in the format NNNN-NNNX
        timeout: Request timeout in seconds

    Returns:
        Bibliographic dict or None
    """
    normalized = issn.strip()
    if not ISSN_PATTERN.match(normalized):
        logger.warning(f"Invalid ISSN: {issn}")
        return None

    logger.info(f"Searching SUDOC for ISSN: {normalized}")
    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "query": f"isn={normalized}",
        "recordSchema": "pica",
        "maximumRecords": "1",
    }
    content = _get(params, timeout)
    if not content:
        return None

    records = _parse_sudoc_response(content)
    if not records:
        logger.info(f"ISSN {normalized} not found in SUDOC")
        return None

    result = records[0]
    result["_source"] = "sudoc"
    return result


def search_by_title_author(title: str, author_lastname: str = "",
                           timeout: int = 10) -> Optional[dict]:
    """
    Search SUDOC by title words and optional author last name.

    Strips issue-number suffixes before searching (useful for periodicals
    like "J'aime lire n° 228" → "J'aime lire").

    Scores results by title/author similarity and returns the best match
    above the confidence threshold.

    Args:
        title: Book or periodical title (French, accents preserved)
        author_lastname: Author last name (optional)
        timeout: Request timeout in seconds

    Returns:
        Bibliographic dict or None if no confident match found
    """
    if not title:
        return None

    # Strip issue number before searching
    clean_title = _ISSUE_STRIP_RE.sub("", title).strip()
    if not clean_title:
        return None

    # Build SRU query: one mti= clause per word, plus optional aut=
    from ._catalog_utils import normalize as _normalize
    title_words = [w for w in _normalize(clean_title).split() if len(w) > 1]
    if not title_words:
        return None

    query_parts = [f"mti={w}" for w in title_words[:4]]  # cap at 4 words
    if author_lastname:
        aut_words = _normalize(author_lastname).split()
        if aut_words:
            query_parts.append(f"aut={aut_words[0]}")

    query = " and ".join(query_parts)

    logger.info(f"Searching SUDOC: '{title}' / '{author_lastname}' → query={query!r}")
    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "query": query,
        "recordSchema": "pica",
        "maximumRecords": "5",
    }
    content = _get(params, timeout)
    if not content:
        return None

    records = _parse_sudoc_response(content)
    if not records:
        logger.info(f"No SUDOC results for '{title}'")
        return None

    # Score each result
    best_score = 0.0
    best_record = None
    for rec in records:
        found_title = rec.get("title", "")
        found_authors = " ".join(rec.get("authors", []))
        sc = score_match(clean_title, author_lastname, found_title, found_authors)
        if sc > best_score:
            best_score = sc
            best_record = rec

    if best_record is None or best_score < 0.45:
        logger.info(f"No confident SUDOC match for '{title}' (best score: {best_score:.2f})")
        return None

    best_record["_confidence"] = "high" if best_score >= 0.75 else "low"
    best_record["_score"] = round(best_score, 3)
    best_record["_source"] = "sudoc"
    logger.info(f"SUDOC match for '{title}': score={best_score:.2f}")
    return best_record
