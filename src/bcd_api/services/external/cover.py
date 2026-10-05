"""Cover Image Service

Downloads book cover images from multiple providers in cascade:

  1. Configured ISBN URL pattern (optional, configured in .env)
  2. Amazon         -- direct URL (ISBN-10 = ASIN, best for French books)
  3. Open Library   -- covers.openlibrary.org (prefers ISBN-13)
  4. Google Books   -- googleapis.com/books (requires GOOGLE_BOOKS_API_KEY in .env)
  5. geobib         -- couverture.geobib.fr (BNF proxy, ISBN-13)

Returns the cached filename (e.g. '9782070368228.jpg') on success, None on failure.
Idempotent: if the file already exists in data/covers/, returns immediately.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

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


def _get_covers_dir() -> Path:
    """Return the covers directory, configurable from settings/env."""
    from src.bcd_api.core.config import settings

    if settings.covers_dir_path:
        return Path(settings.covers_dir_path)
    return Path("data/covers")


def migrate_covers_to_isbn13(
    covers_dir: Optional[Path] = None, db: Optional[Session] = None
) -> None:
    """Rename any ISBN-10 cover files to their ISBN-13 equivalent.

    Runs only once: a sentinel file ``covers_dir/.isbn13`` is written after
    a successful migration so subsequent startups skip the disk scan entirely.
    Updates cover_image in the DB when a session is provided.
    """
    if covers_dir is None:
        covers_dir = _get_covers_dir()

    if not covers_dir.exists():
        return

    sentinel = covers_dir / ".isbn13"
    if sentinel.exists():
        return

    renamed = 0
    for path in sorted(covers_dir.glob("*.jpg")):
        stem = path.stem
        if len(stem) != 10 or not stem[:9].isdigit():
            continue
        isbn13 = _isbn10_to_isbn13(stem)
        dest = covers_dir / f"{isbn13}.jpg"
        if dest.exists():
            continue
        try:
            path.rename(dest)
            renamed += 1
            if db is not None:
                from sqlalchemy import text

                db.execute(
                    text(
                        "UPDATE bibliographic_record SET cover_image = :new WHERE cover_image = :old"
                    ),
                    {"new": dest.name, "old": path.name},
                )
        except Exception:
            logger.debug(f"Could not rename cover {path.name} -> {dest.name}", exc_info=True)

    if db is not None:
        db.commit()
    sentinel.write_text("")
    if renamed:
        logger.info(f"Migrated {renamed} cover file(s) from ISBN-10 to ISBN-13 filenames")


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


def _try_openlibrary(
    isbn10: Optional[str], isbn13: Optional[str], client: httpx.Client
) -> Optional[bytes]:
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
        r = client.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=10)
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


def _expand_isbn_url_pattern(pattern: str, isbn13: str) -> str:
    """Expand whole-ISBN and arbitrary Python-style index/slice fields.

    Examples include ``{isbn[-1]}``, ``{isbn[-2:]}``, and
    ``{isbn[3:7]}``. Indexes and slice bounds can select any number of digits.
    """
    field_pattern = re.compile(r"\{isbn(?:\[([^\]]+)\])?\}")

    def replace_field(match: re.Match) -> str:
        expression = match.group(1)
        if expression is None:
            return isbn13

        if ":" not in expression:
            if not re.fullmatch(r"[+-]?\d+", expression):
                raise ValueError(f"Invalid ISBN index: {expression}")
            return isbn13[int(expression)]

        parts = expression.split(":")
        if len(parts) > 3 or any(part and not re.fullmatch(r"[+-]?\d+", part) for part in parts):
            raise ValueError(f"Invalid ISBN slice: {expression}")
        bounds = [int(part) if part else None for part in parts]
        return isbn13[slice(*bounds)]

    url = field_pattern.sub(replace_field, pattern)
    if "{" in url or "}" in url:
        raise ValueError("Unsupported field in cover image URL pattern")
    return url


def _try_configured_url(isbn13: Optional[str], client: httpx.Client) -> Optional[bytes]:
    """Try an optional URL template configured through ``.env``.

    Templates support ``{isbn}`` and arbitrary Python-style ISBN indexes and
    slices, such as ``{isbn[-1]}`` or ``{isbn[-2:]}``. Only numeric ISBN-13
    values are used.
    """
    if not isbn13 or len(isbn13) != 13 or not isbn13.isdigit():
        return None

    from src.bcd_api.core.config import settings

    pattern = settings.cover_image_url_pattern.strip()
    if not pattern:
        return None

    try:
        url = _expand_isbn_url_pattern(pattern, isbn13)
    except (IndexError, ValueError) as exc:
        logger.warning("Invalid cover image URL pattern: %s", exc)
        return None

    if not url.startswith(("http://", "https://")):
        logger.warning("Cover image URL pattern must produce an HTTP(S) URL")
        return None

    return _fetch(url, client)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_cached_cover(isbn: str, covers_dir: Optional[Path] = None) -> Optional[str]:
    """Return the canonical cover filename if it already exists on disk, else None.

    Uses the same ISBN normalisation and ISBN-13 canonical naming as
    ``download_cover`` so the two functions always agree on filenames.
    Does **not** attempt any network download.
    """
    if covers_dir is None:
        covers_dir = _get_covers_dir()

    if not isbn:
        return None
    isbn = isbn.strip()
    if isbn.lower().startswith("issn:"):
        return None
    if isbn.lower().startswith("isbn:"):
        isbn = isbn[5:]
    normalized = _normalize(isbn)
    if not normalized:
        return None
    _, isbn13 = _both_forms(normalized)
    canonical = isbn13 if isbn13 else normalized
    dest = covers_dir / f"{canonical}.jpg"
    return dest.name if dest.exists() else None


def download_cover(isbn: str, covers_dir: Optional[Path] = None) -> Optional[str]:
    """
    Download a book cover image, trying multiple providers in cascade.

    Args:
        isbn: ISBN-10 or ISBN-13 (hyphens allowed; ``isbn:`` / ``issn:`` prefixes stripped).
        covers_dir: Directory where cover images are stored.

    Returns:
        Filename (e.g. '9782070368228.jpg') on success, None if no cover found.
        Idempotent: returns the cached filename if the file already exists.
    """
    if covers_dir is None:
        covers_dir = _get_covers_dir()

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

    isbn10, isbn13 = _both_forms(normalized)
    # Always store under ISBN-13 when possible; fall back to normalized form
    canonical = isbn13 if isbn13 else normalized
    dest = covers_dir / f"{canonical}.jpg"
    if dest.exists():
        return dest.name

    providers = [
        ("configured_url", lambda c: _try_configured_url(isbn13, c)),
        ("amazon", lambda c: _try_amazon(isbn10, c)),
        ("openlibrary", lambda c: _try_openlibrary(isbn10, isbn13, c)),
        ("google_api", lambda c: _try_google_api(isbn13, c)),
        ("geobib", lambda c: _try_geobib(isbn13, c)),
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
