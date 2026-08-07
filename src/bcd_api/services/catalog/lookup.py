"""Lookup module for ISBN/ISSN catalog search and external metadata integration."""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from src.bcd_api.core.config import settings
from src.bcd_api.core.exceptions import ConflictError
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.shared.constants import MediumType
from ._validation import normalize_identifier

logger = logging.getLogger(__name__)


def _download_cover(isbn: str) -> Optional[str]:
    """Download cover image from external providers in cascade."""
    from ..external.cover import download_cover as cover_download_cover
    return cover_download_cover(isbn, covers_dir=None)


def lookup_isbn(db: Session, isbn: str) -> Optional[Dict[str, Any]]:
    """
    Lookup ISBN/ISSN in local database, then fallback to external APIs in cascade:
    SUDOC (for ISSN), BNF -> Google Books -> SUDOC (for ISBN).
    """
    normalized_isbn = normalize_identifier(isbn)

    # Check local database first
    existing_record = db.query(BibliographicRecord).filter(
        BibliographicRecord.isbn == normalized_isbn
    ).first()

    if existing_record:
        error = ConflictError(f"ISBN/ISSN {normalized_isbn} already exists in database")
        error.context = {
            "record_id": existing_record.id,
            "title": existing_record.title,
            "isbn": normalized_isbn,
            "medium_type": existing_record.medium_type,
        }
        raise error

    data = None
    source = None
    is_issn = normalized_isbn.startswith("issn:")
    bare_identifier = normalized_isbn.split(":", 1)[1]

    # Import external APIs directly
    from ..external.bnf import search_by_isbn as bnf_search_by_isbn
    from ..external.google_books import search_by_isbn as google_search_by_isbn
    from ..external.sudoc import search_by_issn as sudoc_search_by_issn, search_by_isbn as sudoc_search_by_isbn

    # SUDOC ISSN check
    if is_issn and settings.sudoc_enabled:
        logger.info(f"ISSN detected - querying SUDOC directly for {bare_identifier}")
        try:
            data = sudoc_search_by_issn(bare_identifier)
            if data:
                data.pop("issn", None)
                data["isbn"] = normalized_isbn
                data["medium_type"] = MediumType.PERIODIQUE.value
                source = "sudoc"
            else:
                logger.info(f"ISSN {bare_identifier} not found in SUDOC")
        except Exception:
            logger.warning(f"SUDOC unavailable for ISSN {bare_identifier}", exc_info=True)

    # ISBN checks cascade
    if data is None and not is_issn:
        if settings.bnf_enabled:
            logger.info(f"Looking up ISBN {bare_identifier} in BNF catalog")
            try:
                data = bnf_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "bnf"
                else:
                    logger.info(f"ISBN {bare_identifier} not found in BNF catalog")
            except Exception:
                logger.warning(f"BNF unavailable for ISBN {bare_identifier}", exc_info=True)

        if data is None and settings.google_books_enabled:
            logger.info(f"Trying Google Books for ISBN {bare_identifier}")
            try:
                data = google_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "google_books"
            except Exception:
                logger.warning(f"Google Books unavailable for ISBN {bare_identifier}", exc_info=True)

        if data is None and settings.sudoc_enabled:
            logger.info(f"Trying SUDOC for ISBN {bare_identifier}")
            try:
                data = sudoc_search_by_isbn(bare_identifier)
                if data is not None:
                    source = "sudoc"
            except Exception:
                logger.warning(f"SUDOC unavailable for ISBN {bare_identifier}", exc_info=True)

        if data is not None:
            data["isbn"] = normalized_isbn

    if data is None:
        logger.info(f"ISBN/ISSN {normalized_isbn} not found in any catalog")
        return None

    data["_source"] = source

    # Synchronously download cover image if found
    cover_file = _download_cover(normalized_isbn)
    if cover_file:
        data["cover_image"] = cover_file

    logger.info(f"Successfully found bibliographic data for {normalized_isbn} (source: {source})")
    return data
