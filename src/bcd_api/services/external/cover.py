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
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import ValidationError

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

_COVER_SOURCE_DEFAULTS: dict[str, bool | int | str | None] = {
    "cover_custom_url_enabled": True,
    "cover_custom_url_timeout": 2,
    "cover_image_url_pattern": None,
    "cover_amazon_enabled": True,
    "cover_amazon_timeout": 2,
    "cover_openlibrary_enabled": True,
    "cover_openlibrary_timeout": 2,
    "cover_google_books_enabled": True,
    "cover_google_books_timeout": 2,
    "cover_geobib_enabled": True,
    "cover_geobib_timeout": 2,
}


def configure(google_api_key: Optional[str] = None) -> None:
    """Call once at startup with values from settings."""
    global _google_api_key
    _google_api_key = google_api_key or None


def snapshot_cover_source_settings(settings: object | None) -> dict[str, bool | int | str | None]:
    """Copy the cover provider options before the database session is closed."""
    options = {
        key: getattr(settings, key, default) if settings is not None else default
        for key, default in _COVER_SOURCE_DEFAULTS.items()
    }
    if options["cover_image_url_pattern"] is None:
        from src.bcd_api.core.config import settings as app_settings

        options["cover_image_url_pattern"] = app_settings.cover_image_url_pattern
    return options


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


def _fetch(url: str, client: httpx.Client, timeout: int = 2) -> Optional[bytes]:
    try:
        r = client.get(url, timeout=timeout, follow_redirects=True)
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


def _try_amazon(isbn10: Optional[str], client: httpx.Client, timeout: int = 2) -> Optional[bytes]:
    if not isbn10:
        return None
    for suffix in _AMAZON_SUFFIXES:
        for host in _AMAZON_HOSTS:
            url = f"https://{host}/images/P/{isbn10}.01.{suffix}.jpg"
            data = _fetch(url, client, timeout)
            if data:
                return data
    return None


def _try_openlibrary(
    isbn10: Optional[str], isbn13: Optional[str], client: httpx.Client, timeout: int = 2
) -> Optional[bytes]:
    for isbn in filter(None, [isbn13, isbn10]):
        url = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"
        data = _fetch(url, client, timeout)
        if data:
            return data
    return None


def _try_google_api(
    isbn13: Optional[str], client: httpx.Client, timeout: int = 2
) -> Optional[bytes]:
    if not isbn13:
        return None
    params: dict = {"q": f"isbn:{isbn13}", "maxResults": "1"}
    if _google_api_key:
        params["key"] = _google_api_key
    try:
        r = client.get(
            "https://www.googleapis.com/books/v1/volumes", params=params, timeout=timeout
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("items"):
            return None
        links = data["items"][0].get("volumeInfo", {}).get("imageLinks", {})
        for size in ["large", "medium", "small", "thumbnail", "smallThumbnail"]:
            if size in links:
                thumb = links[size].replace("http://", "https://")
                return _fetch(thumb, client, timeout)
    except Exception:
        pass
    return None


def _try_geobib(isbn13: Optional[str], client: httpx.Client, timeout: int = 2) -> Optional[bytes]:
    if not isbn13:
        return None
    url = f"https://couverture.geobib.fr/api/v1/{isbn13}/medium"
    return _fetch(url, client, timeout)


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


def _try_configured_url(
    isbn13: Optional[str],
    client: httpx.Client,
    timeout: int = 2,
    pattern: Optional[str] = None,
) -> Optional[bytes]:
    """Try an optional URL template configured through ``.env``.

    Templates support ``{isbn}`` and arbitrary Python-style ISBN indexes and
    slices, such as ``{isbn[-1]}`` or ``{isbn[-2:]}``. Only numeric ISBN-13
    values are used.
    """
    if not isbn13 or len(isbn13) != 13 or not isbn13.isdigit():
        return None

    if pattern is None:
        from src.bcd_api.core.config import settings

        pattern = settings.cover_image_url_pattern
    pattern = pattern.strip()
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

    return _fetch(url, client, timeout)


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


def download_cover(
    isbn: str,
    covers_dir: Optional[Path] = None,
    source_settings: Optional[Mapping[str, bool | int | str | None]] = None,
) -> Optional[str]:
    """
    Download a book cover image, trying multiple providers in cascade.

    Args:
        isbn: ISBN-10 or ISBN-13 (hyphens allowed; ``isbn:`` / ``issn:`` prefixes stripped).
        covers_dir: Directory where cover images are stored.
        source_settings: Per-provider switches and timeouts from system settings.

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

    options = {**_COVER_SOURCE_DEFAULTS, **(source_settings or {})}
    if options["cover_image_url_pattern"] is None:
        from src.bcd_api.core.config import settings

        options["cover_image_url_pattern"] = settings.cover_image_url_pattern
    providers = [
        (
            "configured_url",
            "cover_custom_url",
            lambda c, timeout: _try_configured_url(
                isbn13, c, timeout, str(options["cover_image_url_pattern"] or "")
            ),
        ),
        ("amazon", "cover_amazon", lambda c, timeout: _try_amazon(isbn10, c, timeout)),
        (
            "openlibrary",
            "cover_openlibrary",
            lambda c, timeout: _try_openlibrary(isbn10, isbn13, c, timeout),
        ),
        (
            "google_api",
            "cover_google_books",
            lambda c, timeout: _try_google_api(isbn13, c, timeout),
        ),
        ("geobib", "cover_geobib", lambda c, timeout: _try_geobib(isbn13, c, timeout)),
    ]

    with httpx.Client(headers=_HEADERS) as client:
        for name, key, fn in providers:
            if not options[f"{key}_enabled"]:
                continue
            try:
                data = fn(client, int(options[f"{key}_timeout"]))
                if data:
                    dest.write_bytes(data)
                    logger.info(f"Cover downloaded for ISBN {normalized} via {name}")
                    return dest.name
            except Exception:
                logger.debug(f"Cover provider {name} failed for {normalized}", exc_info=True)

    logger.info(f"No cover found for ISBN {normalized}")
    return None


def test_cover_source(
    source: str, source_settings: Optional[Mapping[str, bool | int | str | None]] = None
) -> dict[str, object]:
    """Test one enabled cover provider with a sample ISBN without storing its image."""
    source = source.strip().lower()
    options = {**_COVER_SOURCE_DEFAULTS, **(source_settings or {})}
    if options["cover_image_url_pattern"] is None:
        from src.bcd_api.core.config import settings

        options["cover_image_url_pattern"] = settings.cover_image_url_pattern
    isbn10, isbn13 = _both_forms("9782070612758")
    providers = {
        "custom_url": (
            "cover_custom_url_enabled",
            "cover_custom_url_timeout",
            lambda client, timeout: _try_configured_url(
                isbn13, client, timeout, str(options["cover_image_url_pattern"] or "")
            ),
        ),
        "amazon": (
            "cover_amazon_enabled",
            "cover_amazon_timeout",
            lambda client, timeout: _try_amazon(isbn10, client, timeout),
        ),
        "openlibrary": (
            "cover_openlibrary_enabled",
            "cover_openlibrary_timeout",
            lambda client, timeout: _try_openlibrary(isbn10, isbn13, client, timeout),
        ),
        "google_books": (
            "cover_google_books_enabled",
            "cover_google_books_timeout",
            lambda client, timeout: _try_google_api(isbn13, client, timeout),
        ),
        "geobib": (
            "cover_geobib_enabled",
            "cover_geobib_timeout",
            lambda client, timeout: _try_geobib(isbn13, client, timeout),
        ),
    }
    if source not in providers:
        raise ValidationError(f"Unknown cover source: {source}")

    enabled_key, timeout_key, provider = providers[source]
    if not options[enabled_key]:
        return {"source": source, "status": "disabled", "ok": False}

    started = time.perf_counter()
    try:
        with httpx.Client(headers=_HEADERS) as client:
            data = provider(client, int(options[timeout_key]))
        return {
            "source": source,
            "status": "reachable" if data else "not_found",
            "ok": True,
            "found": bool(data),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        logger.warning("Cover source test for '%s' failed: %s", source, exc)
        return {
            "source": source,
            "status": "error",
            "ok": False,
            "error": str(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
