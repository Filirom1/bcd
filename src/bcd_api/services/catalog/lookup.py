"""Notice lookup façade for cataloging and legacy catalog API callers."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from .notice_lookup import (
    EXTERNAL_SOURCES,
    classify_catalog_input,
    lookup_identifier_cascade,
    lookup_notice_source,
    search_local_notices,
    source_configuration,
    test_external_source,
)


def _download_cover(identifier: str) -> Optional[str]:
    """Download a cover through the cover service when available."""
    from ..external.cover import download_cover as cover_download_cover

    return cover_download_cover(identifier, covers_dir=None)


def lookup_isbn(db: Session, isbn: str) -> Optional[dict[str, Any]]:
    """Run the fixed local → BnF → Google Books / SUDOC route.

    The public name is retained for API callers, but the implementation now
    follows the Find-a-notice design: arbitrary text and unsupported barcodes
    never call an external service, and SUDOC is never an ISBN fallback.
    """
    return lookup_identifier_cascade(db, isbn)


__all__ = [
    "EXTERNAL_SOURCES",
    "classify_catalog_input",
    "lookup_isbn",
    "lookup_notice_source",
    "search_local_notices",
    "source_configuration",
    "test_external_source",
    "_download_cover",
]
