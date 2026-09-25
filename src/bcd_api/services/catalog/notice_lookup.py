"""Cataloging notice discovery and external-source routing.

The cataloging screen deliberately separates two operations:

* ``search_local_notices`` is a database-only lookup and is always safe to call
  first; and
* ``lookup_notice_source`` calls exactly one configured external source after
  the local lookup found no suitable notice.

Keeping the source call explicit makes the workflow easy to skip, test, and
understand.  It also prevents a free-form barcode from entering an ISBN
cascade.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from sqlalchemy import and_, case, exists, func, or_
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import ValidationError
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.system_settings import SystemSettings
from src.bcd_api.utils.catalog_input import (
    CatalogInput,
    classify_catalog_input,
    strip_periodical_issue_suffix,
)
from src.shared.constants import MediumType

from .._catalog_utils import normalize as normalize_catalog_text
from ._serialization import decode_list
from ._validation import item_id_search_values
from .projections import availability_by_record

logger = logging.getLogger(__name__)

EXTERNAL_SOURCES = ("bnf", "google_books", "sudoc")
_SOURCE_DEFAULTS = {
    "bnf": {"enabled": True, "timeout": 4},
    "google_books": {"enabled": True, "timeout": 4},
    "sudoc": {"enabled": True, "timeout": 5},
}

# SQLite does not provide a portable accent-insensitive collation.  Normalize
# the small set of French diacritics in SQL, and normalize separators so that
# searches such as "sorciere"/"Sorcière" and "j magazine"/"J-Magazine"
# address the same notice on both SQLite and PostgreSQL.
_ACCENT_REPLACEMENTS = (
    ("à", "a"), ("À", "a"), ("â", "a"), ("Â", "a"), ("ä", "a"), ("Ä", "a"),
    ("ç", "c"), ("Ç", "c"),
    ("é", "e"), ("É", "e"), ("è", "e"), ("È", "e"), ("ê", "e"), ("Ê", "e"),
    ("ë", "e"), ("Ë", "e"),
    ("î", "i"), ("Î", "i"), ("ï", "i"), ("Ï", "i"),
    ("ô", "o"), ("Ô", "o"), ("ö", "o"), ("Ö", "o"),
    ("ù", "u"), ("Ù", "u"), ("û", "u"), ("Û", "u"), ("ü", "u"), ("Ü", "u"),
    ("œ", "oe"), ("Œ", "oe"), ("æ", "ae"), ("Æ", "ae"),
)
_SEARCH_SEPARATORS = (" ", "-", "–", "—", "'", "’", ".", ",", ":", ";", "/", "_", "(", ")")


def _normalize_search_text(value: str) -> str:
    """Normalize user text using the catalog's shared search normalization."""
    # ``normalize_catalog_text`` already handles case, accents, punctuation,
    # and whitespace.  Removing the remaining spaces makes separators
    # interchangeable: "j magazine" and "J-Magazine" both become
    # ``jmagazine``.
    return normalize_catalog_text(value or "").replace(" ", "")


def _normalized_column(column):
    """Build a portable SQL expression matching ``_normalize_search_text``."""
    expression = column
    for source, target in _ACCENT_REPLACEMENTS:
        expression = func.replace(expression, source, target)
    expression = func.lower(expression)
    for separator in _SEARCH_SEPARATORS:
        expression = func.replace(expression, separator, "")
    return expression


def _text_search_expressions(raw_query: str) -> dict[str, Any]:
    """Build one normalized set of SQL expressions for local notice search."""
    raw = raw_query.strip()
    raw_normalized = _normalize_search_text(raw)
    title_normalized = _normalize_search_text(strip_periodical_issue_suffix(raw))
    title_expression = _normalized_column(BibliographicRecord.title)
    search_expressions = {
        "exact_title": title_expression == raw_normalized,
        "exact_title_without_issue": title_expression == title_normalized,
        "title_contains": title_expression.like(f"%{raw_normalized}%"),
        "author_contains": _normalized_column(BibliographicRecord.authors).like(
            f"%{raw_normalized}%"
        ),
        "subtitle_contains": _normalized_column(BibliographicRecord.subtitle).like(
            f"%{raw_normalized}%"
        ),
        "publisher_contains": _normalized_column(BibliographicRecord.publisher).like(
            f"%{raw_normalized}%"
        ),
        "collection_contains": _normalized_column(BibliographicRecord.collection).like(
            f"%{raw_normalized}%"
        ),
    }
    return search_expressions


def _identifier_search_expressions(classified: CatalogInput) -> tuple[Any, Any]:
    """Build exact identifier expressions shared by filtering and ranking."""
    exact_identifier = (
        BibliographicRecord.isbn == classified.normalized_identifier
        if classified.normalized_identifier
        else False
    )
    # Older imported catalogues may contain an unprefixed identifier.  It is
    # still an exact local match, but is never passed to an external provider.
    bare_identifier = (
        func.lower(BibliographicRecord.isbn) == func.lower(classified.identifier_value)
        if classified.identifier_value
        else False
    )
    return exact_identifier, bare_identifier


def _settings_value(db: Session, source: str, field: str) -> Any:
    """Read a source setting, falling back to the application default."""
    row = db.query(SystemSettings).first()
    key = f"{source}_{field}"
    if row is not None and hasattr(row, key):
        value = getattr(row, key)
        if value is not None:
            return value
    return _SOURCE_DEFAULTS[source][field]


def source_configuration(db: Session) -> list[dict[str, Any]]:
    """Return the small, fixed source configuration used by the UI."""
    return [
        {
            "source": source,
            "enabled": bool(_settings_value(db, source, "enabled")),
            "timeout": int(_settings_value(db, source, "timeout")),
        }
        for source in EXTERNAL_SOURCES
    ]


def _local_match_expressions(
    raw_query: str,
    classified: CatalogInput,
    exact_item_barcode: Any = False,
) -> tuple[list[Any], Any]:
    """Build the shared filter and ranking expressions for local search."""
    text = _text_search_expressions(raw_query)
    exact_title = text["exact_title"]
    exact_title_without_issue = text["exact_title_without_issue"]
    title_contains = text["title_contains"]
    author_contains = text["author_contains"]
    subtitle_contains = text["subtitle_contains"]
    publisher_contains = text["publisher_contains"]
    collection_contains = text["collection_contains"]
    exact_identifier, bare_identifier = _identifier_search_expressions(classified)

    matches = [
        exact_identifier,
        bare_identifier,
        exact_title,
        exact_title_without_issue,
        title_contains,
        author_contains,
        subtitle_contains,
        publisher_contains,
        collection_contains,
        exact_item_barcode,
    ]

    # Prefer an exact periodical title to issue-like notices with the same
    # words.  The expression is intentionally independent of a hard-coded
    # medium vocabulary: the identifier is the authoritative periodical hint.
    preferred_periodical_title = and_(
        BibliographicRecord.isbn.ilike("issn:%"),
        exact_title_without_issue,
    )

    rank = case(
        (exact_item_barcode, 0),
        (exact_identifier, 1),
        (bare_identifier, 2),
        (preferred_periodical_title, 3),
        (exact_title, 4),
        (exact_title_without_issue, 5),
        (author_contains, 6),
        (title_contains, 7),
        (subtitle_contains, 8),
        (publisher_contains, 9),
        (collection_contains, 10),
        else_=11,
    )
    return matches, rank


def _record_identifier(record: BibliographicRecord) -> dict[str, Optional[str]]:
    value = record.isbn_value
    identifier_type = record.identifier_type
    return {
        "identifier_type": identifier_type,
        "identifier": value,
        "isbn": value if identifier_type == "isbn" else None,
        "issn": value if identifier_type == "issn" else None,
    }


def _issue_sort_key(value: str) -> tuple[int, Any]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, value.casefold())


def _add_notice_selection_fields(
    db: Session,
    records: list[BibliographicRecord],
) -> list[dict[str, Any]]:
    """Enrich records with compact selection information in one item query."""
    if not records:
        return []

    summaries = availability_by_record(db, records, include_items=False)
    summaries_by_id = {summary["id"]: summary for summary in summaries}
    record_ids = [record.id for record in records]
    periodical_record_ids = {
        record.id
        for record in records
        if (record.isbn or "").lower().startswith("issn:")
    }
    items = (
        db.query(Item)
        .filter(Item.bibliographic_record_id.in_(record_ids))
        .order_by(Item.bibliographic_record_id, Item.id)
        .all()
    )
    issues_by_record: dict[int, list[str]] = {record_id: [] for record_id in record_ids}
    for item in items:
        # Periodical issue numbers are stored in the existing call_number
        # column and are shown with an explicit issue-number label in the UI.
        issue = (
            item.call_number
            if item.bibliographic_record_id in periodical_record_ids
            else None
        )
        if issue and issue not in issues_by_record[item.bibliographic_record_id]:
            issues_by_record[item.bibliographic_record_id].append(str(issue))

    result: list[dict[str, Any]] = []
    for record in records:
        summary = dict(summaries_by_id.get(record.id, {}))
        summary.update(_record_identifier(record))
        summary["notice_id"] = record.id
        summary["copies"] = summary.get("total_items", 0)
        summary["issues_present"] = sorted(
            issues_by_record.get(record.id, []), key=_issue_sort_key
        )
        summary["authors"] = decode_list(record.authors)
        # Keep the fields needed by the review form even though this is a
        # compact result rather than the full bibliographic response.
        summary["subtitle"] = record.subtitle
        summary["dewey_number"] = record.dewey_number
        summary["collection"] = record.collection
        summary["illustrators"] = decode_list(record.illustrators)
        result.append(summary)
    return result


def search_local_notices(
    db: Session,
    query: str,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, CatalogInput]:
    """Search only the local catalog and return compact notice choices.

    No external service is imported or called from this function.  Exact
    identifier and item-barcode matches are ranked before title/author text;
    an issue suffix is also searched without its suffix.
    """
    classified = classify_catalog_input(query)
    raw = classified.raw
    if not raw:
        return [], 0, classified

    # Search the raw barcode exactly.  The stored item ID does not include the
    # display prefix, so accept both forms configured in the singleton settings.
    settings_row = db.query(SystemSettings).first()
    prefix = getattr(settings_row, "item_barcode_prefix", ".") if settings_row else "."
    barcode_values = item_id_search_values(raw, prefix)
    exact_item_barcode = exists().where(
        and_(
            Item.bibliographic_record_id == BibliographicRecord.id,
            Item.item_id.in_(barcode_values),
        )
    )
    matches, rank = _local_match_expressions(raw, classified, exact_item_barcode)

    query_builder = db.query(BibliographicRecord).filter(or_(*matches))
    total = query_builder.count()
    records = (
        query_builder.order_by(rank, BibliographicRecord.title, BibliographicRecord.id)
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return _add_notice_selection_fields(db, records), total, classified


def _normalised_external_data(
    data: Optional[dict[str, Any]], classified: CatalogInput, source: str
) -> Optional[dict[str, Any]]:
    if not data:
        return None
    result = dict(data)
    if classified.normalized_identifier:
        result["isbn"] = classified.normalized_identifier
    if classified.identifier_type == "issn":
        result.pop("issn", None)
        result["medium_type"] = MediumType.PERIODIQUE.value
    result["_source"] = source
    return result


def _call_source(
    source: str,
    classified: CatalogInput,
    timeout: int,
) -> Optional[dict[str, Any]]:
    if source == "bnf":
        from ..external.bnf import search_by_isbn
        return search_by_isbn(classified.identifier_value or "", timeout=timeout)
    if source == "google_books":
        from ..external.google_books import search_by_isbn
        return search_by_isbn(classified.identifier_value or "", timeout=timeout)
    if source == "sudoc":
        from ..external.sudoc import search_by_issn
        return search_by_issn(classified.identifier_value or "", timeout=timeout)
    raise ValidationError(f"Unknown external catalog source: {source}")


def lookup_notice_source(
    db: Session,
    query: str,
    source: str,
) -> dict[str, Any]:
    """Perform one source lookup after rechecking the local catalog.

    The local recheck is intentional: callers can safely use this endpoint as
    the second step without accidentally causing an external request when a
    matching notice was added or already existed locally.
    """
    source = source.strip().lower()
    if source not in EXTERNAL_SOURCES:
        raise ValidationError(f"Unknown external catalog source: {source}")

    local_items, local_total, classified = search_local_notices(db, query, limit=20)
    if local_total:
        return {
            "status": "local",
            "source": "local",
            "items": local_items,
            "total": local_total,
            "input_type": classified.kind,
            "normalized_identifier": classified.normalized_identifier,
        }

    if source not in classified.external_sources:
        raise ValidationError(
            f"External source {source} is not applicable to {classified.kind} input"
        )

    if not bool(_settings_value(db, source, "enabled")):
        return {
            "status": "disabled",
            "source": source,
            "items": [],
            "total": 0,
            "input_type": classified.kind,
            "normalized_identifier": classified.normalized_identifier,
        }

    timeout = int(_settings_value(db, source, "timeout"))
    started = time.perf_counter()
    try:
        data = _call_source(source, classified, timeout)
    except Exception as exc:  # providers are optional and must not block manual entry
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        logger.warning("External catalog source %s failed: %s", source, exc)
        return {
            "status": "error",
            "source": source,
            "items": [],
            "total": 0,
            "input_type": classified.kind,
            "normalized_identifier": classified.normalized_identifier,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    normalised = _normalised_external_data(data, classified, source)
    return {
        "status": "found" if normalised else "not_found",
        "source": source,
        "data": normalised,
        "items": [normalised] if normalised else [],
        "total": 1 if normalised else 0,
        "input_type": classified.kind,
        "normalized_identifier": classified.normalized_identifier,
        "elapsed_ms": elapsed_ms,
    }


def lookup_identifier_cascade(db: Session, query: str) -> Optional[dict[str, Any]]:
    """Run the fixed ISBN or ISSN route for legacy/API callers.

    This is still sequential and has no title-search cascade.  In particular,
    SUDOC is never attempted for an ISBN.
    """
    local_items, local_total, classified = search_local_notices(db, query, limit=1)
    if local_total:
        return local_items[0]
    for source in classified.external_sources:
        result = lookup_notice_source(db, query, source)
        if result.get("status") == "found":
            return result["data"]
    return None


def test_external_source(
    db: Session,
    source: str,
    query: Optional[str] = None,
) -> dict[str, Any]:
    """Make one explicit test request for the Settings screen."""
    source = source.strip().lower()
    samples = {"bnf": "9782070612758", "google_books": "9782070612758", "sudoc": "1163-7706"}
    value = (query or samples.get(source, "")).strip()
    if source not in EXTERNAL_SOURCES:
        raise ValidationError(f"Unknown external catalog source: {source}")
    classified = classify_catalog_input(value)
    if source not in classified.external_sources:
        raise ValidationError(f"Invalid test identifier for source {source}: {value}")
    if not bool(_settings_value(db, source, "enabled")):
        return {"source": source, "status": "disabled", "ok": False}

    started = time.perf_counter()
    try:
        data = _call_source(source, classified, int(_settings_value(db, source, "timeout")))
        status = "reachable" if data else "not_found"
        return {
            "source": source,
            "status": status,
            "ok": True,
            "found": bool(data),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        return {
            "source": source,
            "status": "error",
            "ok": False,
            "error": str(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
