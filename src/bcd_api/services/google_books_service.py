"""Google Books API Integration Service

Provides bibliographic lookup via the Google Books API v1, as a complement
and fallback to the BNF SRU API. Returns data in the same format as
bnf_service.parse_unimarc_xml() for transparent interoperability.

Reference: /specs/001-school-library-system/contracts/google-books-api.md

Usage:
    from src.bcd_api.services.google_books_service import search_by_isbn, search_by_title_author

    data = search_by_isbn("9782211056465")
    data = search_by_title_author("Stuart Little", "White")
"""

import logging
import re
import time
from typing import Optional

import httpx

from ...shared.constants import MediumType, TargetAudience
from ._catalog_utils import token_overlap as _token_overlap

logger = logging.getLogger(__name__)

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

# Rate limiting: 1 request per second (same pattern as bnf_service)
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 1.0

# Optional API key — set via GOOGLE_BOOKS_API_KEY in .env
# Without a key: ~1 000 req/day. With a key: no practical limit for normal use.
_api_key: Optional[str] = None


def configure(api_key: Optional[str] = None, rate_limit: int = 1) -> None:
    """Call once at startup with values from settings."""
    global _api_key, _MIN_REQUEST_INTERVAL
    _api_key = api_key or None
    _MIN_REQUEST_INTERVAL = 1.0 / max(rate_limit, 1)


def _rate_limit() -> None:
    """Enforce minimum interval between API calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _parse_year(date_str: Optional[str]) -> Optional[int]:
    """Extract 4-digit year from publishedDate ('2003', '2003-05', '2003-05-12')."""
    if not date_str:
        return None
    m = re.search(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def _extract_isbn(identifiers: list) -> Optional[str]:
    """Prefer ISBN-13, fall back to ISBN-10."""
    if not identifiers:
        return None
    by_type = {entry.get("type"): entry.get("identifier") for entry in identifiers}
    return by_type.get("ISBN_13") or by_type.get("ISBN_10")


def _parse_volume(volume: dict) -> dict:
    """Convert a Google Books volumeInfo dict to BCD bibliographic format."""
    info = volume.get("volumeInfo", {})

    authors_raw = info.get("authors", [])
    # Google returns "Firstname Lastname" — normalise to "Lastname, Firstname"
    authors = []
    for a in authors_raw:
        parts = a.rsplit(" ", 1)
        if len(parts) == 2:
            authors.append(f"{parts[1]}, {parts[0]}")
        else:
            authors.append(a)

    year = _parse_year(info.get("publishedDate"))

    result: dict = {
        "title": info.get("title", ""),
        "medium_type": MediumType.LIVRE.value,
        "target_audience": TargetAudience.CHILD.value,
        "language": info.get("language", ""),
    }

    if info.get("subtitle"):
        result["subtitle"] = info["subtitle"]
    if authors:
        result["authors"] = authors
    if info.get("publisher"):
        result["publisher"] = info["publisher"]
    if year:
        result["publication_year"] = year
    if info.get("description"):
        result["description"] = re.sub(r"<[^>]+>", "", info["description"])  # strip HTML
    if info.get("pageCount"):
        result["page_count"] = info["pageCount"]
    if info.get("categories"):
        result["keywords"] = info["categories"]

    isbn = _extract_isbn(info.get("industryIdentifiers", []))
    if isbn:
        result["isbn"] = isbn.replace("-", "")

    thumbnail = info.get("imageLinks", {}).get("thumbnail")
    if thumbnail:
        result["cover_url"] = thumbnail

    return result


def _get(params: dict, timeout: int) -> Optional[dict]:
    """Execute a single GET request, return parsed JSON or None."""
    if _api_key:
        params["key"] = _api_key

    _rate_limit()
    try:
        with httpx.Client() as client:
            response = client.get(GOOGLE_BOOKS_URL, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error("Google Books API timeout")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Google Books API HTTP error: {e.response.status_code}")
        raise
    except httpx.HTTPError as e:
        logger.error(f"Google Books API error: {e}")
        raise


def search_by_isbn(isbn: str, timeout: int = 10) -> Optional[dict]:
    """
    Look up a book by ISBN in Google Books.

    No language restriction applied — the ISBN uniquely identifies the edition.

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

    logger.info(f"Searching Google Books for ISBN: {normalized}")
    data = _get({"q": f"isbn:{normalized}", "maxResults": 1}, timeout)
    if not data or data.get("totalItems", 0) == 0:
        logger.info(f"ISBN {normalized} not found in Google Books")
        return None

    items = data.get("items", [])
    if not items:
        return None

    return _parse_volume(items[0])


def search_by_title_author(title: str, author_lastname: str,
                           timeout: int = 10) -> Optional[dict]:
    """
    Search Google Books by title and author lastname.

    Uses langRestrict=fr because the catalog contains French books.
    Scores results by title/author similarity and returns the best match
    above the confidence threshold.

    Args:
        title: Book title (French, accents preserved)
        author_lastname: Author last name only
        timeout: Request timeout in seconds

    Returns:
        Bibliographic dict or None if no confident match found
    """
    if not title:
        return None

    clean_title = re.sub(r'["\']', " ", title).strip()
    clean_author = re.sub(r'["\']', " ", author_lastname).strip()

    query = f"intitle:{clean_title}"
    if clean_author:
        query += f" inauthor:{clean_author}"

    logger.info(f"Searching Google Books: '{title}' / '{author_lastname}'")

    params = {
        "q": query,
        "maxResults": 5,
        "langRestrict": "fr",
    }
    data = _get(params, timeout)
    if not data or data.get("totalItems", 0) == 0:
        logger.info(f"No Google Books results for '{title}' / '{author_lastname}'")
        return None

    items = data.get("items", [])
    if not items:
        return None

    # Score each result by title + author similarity
    best_score = 0.0
    best_item = None
    for item in items:
        info = item.get("volumeInfo", {})
        bnf_title = info.get("title", "")
        bnf_authors = " ".join(info.get("authors", []))

        title_score = _token_overlap(title, bnf_title)
        author_score = _token_overlap(author_lastname, bnf_authors) if author_lastname else 0.5

        # Perfect title match → weight title more heavily
        score = (title_score * 0.85 + author_score * 0.15
                 if title_score >= 1.0
                 else title_score * 0.65 + author_score * 0.35)

        if score > best_score:
            best_score = score
            best_item = item

    if best_item is None or best_score < 0.45:
        logger.info(f"No confident Google Books match for '{title}' (best score: {best_score:.2f})")
        return None

    result = _parse_volume(best_item)
    result["_confidence"] = "high" if best_score >= 0.75 else "low"
    result["_score"] = round(best_score, 3)
    logger.info(f"Google Books match for '{title}': score={best_score:.2f}")
    return result
