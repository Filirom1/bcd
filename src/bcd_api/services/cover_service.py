"""Cover Image Service

Downloads book cover images from multiple providers in cascade:

  1. Amazon         -- direct URL (ISBN-10 = ASIN, best for French books)
  2. Open Library   -- covers.openlibrary.org (prefers ISBN-13)
  3. Google Books   -- googleapis.com/books (requires GOOGLE_BOOKS_API_KEY in .env)
  4. geobib         -- couverture.geobib.fr (BNF proxy, ISBN-13)

Returns the cached filename (e.g. '9782070368228.jpg') on success, None on failure.
Idempotent: if the file already exists in data/covers/, returns immediately.
"""

import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Minimum image size — anything smaller is a placeholder / 1×1 pixel
_MIN_BYTES = 3_000

# Amazon: prefer LZZZZZZZ (~326×500 px) over TZZZZZZZ (~70×110 px)
_AMAZON_SUFFIXES = ["LZZZZZZZ", "TZZZZZZZ"]
_AMAZON_HOSTS = [
    "images-na.ssl-images-amazon.com",
    "m.media-amazon.com",
]

_HEADERS = {
    "User-Agent": "BCD/1.0 (school library catalog; contact: bcd@ecole.fr)",
}

# Optional Google Books API key — configured via settings
_google_api_key: Optional[str] = None


def configure(google_api_key: Optional[str] = None) -> None:
    """Call once at startup with values from settings."""
    global _google_api_key
    _google_api_key = google_api_key or None


# ---------------------------------------------------------------------------
# ISBN helpers
# ---------------------------------------------------------------------------

def _isbn10_to_isbn13(isbn10: str) -> str:
    if len(isbn10) != 10:
        return isbn10
    base = "978" + isbn10[:9]
    total = sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(base))
    check = (10 - (total % 10)) % 10
    return base + str(check)


def _isbn13_to_isbn10(isbn13: str) -> Optional[str]:
    if len(isbn13) != 13 or not isbn13.startswith("978"):
        return None
    base = isbn13[3:12]
    total = sum((10 - i) * int(d) for i, d in enumerate(base))
    check = (11 - (total % 11)) % 11
    return base + ("X" if check == 10 else str(check))


def _normalize(isbn: str) -> str:
    return isbn.strip().replace("-", "").replace(".", "").replace(" ", "")


def _both_forms(isbn: str) -> tuple[Optional[str], Optional[str]]:
    """Return (isbn10, isbn13) for any normalized ISBN."""
    if len(isbn) == 10:
        return isbn, _isbn10_to_isbn13(isbn)
    if len(isbn) == 13:
        return _isbn13_to_isbn10(isbn), isbn
    return None, None


# ---------------------------------------------------------------------------
# Generic image fetch via httpx
# ---------------------------------------------------------------------------

def _fetch(url: str, client: httpx.Client) -> Optional[bytes]:
    try:
        r = client.get(url, timeout=10, follow_redirects=True)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            if "image" in ct and len(r.content) >= _MIN_BYTES:
                return r.content
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Per-provider functions
# ---------------------------------------------------------------------------

def _try_amazon(isbn10: Optional[str], client: httpx.Client) -> Optional[bytes]:
    if not isbn10:
        return None
    for suffix in _AMAZON_SUFFIXES:
        for host in _AMAZON_HOSTS:
            url = f"https://{host}/images/P/{isbn10}.01.{suffix}.jpg"
            data = _fetch(url, client)
            if data:
                return data
    return None


def _try_openlibrary(isbn10: Optional[str], isbn13: Optional[str],
                     client: httpx.Client) -> Optional[bytes]:
    for isbn in filter(None, [isbn13, isbn10]):
        url = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"
        data = _fetch(url, client)
        if data:
            return data
    return None


def _try_google_api(isbn13: Optional[str], client: httpx.Client) -> Optional[bytes]:
    if not isbn13:
        return None
    params: dict = {"q": f"isbn:{isbn13}", "maxResults": "1"}
    if _google_api_key:
        params["key"] = _google_api_key
    try:
        r = client.get("https://www.googleapis.com/books/v1/volumes",
                        params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("items"):
            return None
        links = data["items"][0].get("volumeInfo", {}).get("imageLinks", {})
        for size in ["large", "medium", "small", "thumbnail", "smallThumbnail"]:
            if size in links:
                thumb = links[size].replace("http://", "https://")
                return _fetch(thumb, client)
    except Exception:
        pass
    return None


def _try_geobib(isbn13: Optional[str], client: httpx.Client) -> Optional[bytes]:
    if not isbn13:
        return None
    url = f"https://couverture.geobib.fr/api/v1/{isbn13}/medium"
    return _fetch(url, client)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_cover(isbn: str, covers_dir: Path = Path("data/covers")) -> Optional[str]:
    """
    Download a book cover image, trying multiple providers in cascade.

    Args:
        isbn: ISBN-10 or ISBN-13 (hyphens allowed; ``isbn:`` / ``issn:`` prefixes stripped).
        covers_dir: Directory where cover images are stored.

    Returns:
        Filename (e.g. '9782070368228.jpg') on success, None if no cover found.
        Idempotent: returns the cached filename if the file already exists.
    """
    if not isbn:
        return None

    # Strip prefixes
    if isbn.lower().startswith("issn:"):
        return None  # periodicals have no covers
    if isbn.lower().startswith("isbn:"):
        isbn = isbn[5:]

    normalized = _normalize(isbn)
    if not normalized:
        return None

    covers_dir.mkdir(parents=True, exist_ok=True)
    dest = covers_dir / f"{normalized}.jpg"
    if dest.exists():
        return dest.name

    isbn10, isbn13 = _both_forms(normalized)

    providers = [
        ("amazon",      lambda c: _try_amazon(isbn10, c)),
        ("openlibrary", lambda c: _try_openlibrary(isbn10, isbn13, c)),
        ("google_api",  lambda c: _try_google_api(isbn13, c)),
        ("geobib",      lambda c: _try_geobib(isbn13, c)),
    ]

    with httpx.Client(headers=_HEADERS) as client:
        for name, fn in providers:
            try:
                data = fn(client)
                if data:
                    dest.write_bytes(data)
                    logger.info(f"Cover downloaded for ISBN {normalized} via {name}")
                    return dest.name
            except Exception:
                logger.debug(f"Cover provider {name} failed for {normalized}", exc_info=True)

    logger.info(f"No cover found for ISBN {normalized}")
    return None
