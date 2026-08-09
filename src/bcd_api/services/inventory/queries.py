"""Query services for inventory, including search and orphan record discovery."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...models.bibliographic_record import BibliographicRecord
from ...models.circulation import CirculationTransaction
from ...models.item import Item
from ...models.system_settings import SystemSettings
from ._search import build_item_search_query
from ._serialization import parse_authors

logger = logging.getLogger(__name__)


def search_items(
    db: Session,
    q: Optional[str] = None,
    status: Optional[str] = None,
    condition: Optional[str] = None,
    shelf_location: Optional[str] = None,
    never_inventoried: Optional[bool] = None,
    inventoried_before: Optional[date] = None,
    acquired_before: Optional[date] = None,
    acquired_after: Optional[date] = None,
    medium_type: Optional[str] = None,
    target_audience: Optional[str] = None,
    level: Optional[str] = None,
    language: Optional[str] = None,
    publication_year_min: Optional[int] = None,
    publication_year_max: Optional[int] = None,
    max_borrows: Optional[int] = None,
    since_date: Optional[date] = None,
    never_borrowed: Optional[bool] = None,
    no_limit: bool = False
) -> dict:
    """
    Search items matching inventory criteria (rotation, last inventoried, condition, etc.).
    """
    query, period_loan_count_column = build_item_search_query(
        db, q=q, status=status, condition=condition, shelf_location=shelf_location,
        never_inventoried=never_inventoried, inventoried_before=inventoried_before,
        acquired_before=acquired_before, acquired_after=acquired_after,
        medium_type=medium_type, target_audience=target_audience, level=level,
        language=language, publication_year_min=publication_year_min,
        publication_year_max=publication_year_max, max_borrows=max_borrows,
        since_date=since_date, never_borrowed=never_borrowed
    )

    # Get total count before limit
    total_count = query.count()

    # Apply limit (read from settings) unless no_limit is True
    capped = False
    if not no_limit:
        settings = db.query(SystemSettings).first()
        result_limit = settings.inventory_search_result_limit if settings else 200
        if total_count > result_limit:
            capped = True
        query = query.limit(result_limit)

    # Execute query
    results = query.all()

    # Build response items
    items = []
    for result in results:
        item = result[0]  # Item object
        title = result[1]  # title from BibliographicRecord
        authors = result[2]  # authors JSON string from BibliographicRecord
        level = result[3]  # level from BibliographicRecord
        target_audience = result[4]  # target_audience from BibliographicRecord
        language = result[5]  # language from BibliographicRecord
        medium_type = result[6]  # medium_type from BibliographicRecord
        publication_year = result[7]  # publication_year from BibliographicRecord
        circulation_count = result[8]  # all-time loan count (always present)

        # Parse authors list
        authors_list = parse_authors(authors) if authors else None

        # Calculate age in days if acquisition_date exists
        age_days = None
        if item.acquisition_date:
            today = datetime.now(timezone.utc).date()
            age_days = (today - item.acquisition_date).days

        item_dict = {
            # Item fields
            "item_id": item.item_id,
            "bibliographic_record_id": item.bibliographic_record_id,
            "status": item.status,
            "condition": item.condition,
            "loanable": item.loanable,
            "shelf_location": item.shelf_location,
            "acquisition_date": item.acquisition_date,
            "last_borrowed_at": item.last_borrowed_at,
            "last_inventoried_at": item.last_inventoried_at,
            # Record fields (for display in working table)
            "title": title,
            "authors": authors_list,
            "call_number": item.call_number,
            "level": level,
            "target_audience": target_audience,
            "language": language,
            "medium_type": medium_type,
            "publication_year": publication_year,
            # Calculated fields
            "age_days": age_days,
            "circulation_count": circulation_count,
        }

        # Add period_loan_count if rotation filter was active
        if period_loan_count_column is not None and len(result) > 9:
            item_dict["period_loan_count"] = result[9]  # period_loan_count from subquery

        items.append(item_dict)

    # Compute archive cutoff date
    archive_cutoff = db.query(func.min(CirculationTransaction.checkout_date)).scalar()

    logger.info(f"Search found {total_count} items, returning {len(items)} (capped={capped})")

    return {
        "items": items,
        "total_count": total_count,
        "displayed_count": len(items),
        "capped": capped,
        "archive_cutoff_date": archive_cutoff
    }


def get_orphan_records(db: Session) -> dict:
    """
    Get bibliographic records with no remaining items using real relationship existence checks.

    Args:
        db: Database session

    Returns:
        dict with:
            - count (int): Number of orphan records
            - records (list): Orphan record details (id, title, isbn)
    """
    # Use real NOT EXISTS query
    orphans = db.query(BibliographicRecord).filter(
        ~db.query(Item).filter(Item.bibliographic_record_id == BibliographicRecord.id).exists()
    ).all()

    records = [
        {
            "id": record.id,
            "title": record.title,
            "isbn": record.isbn
        }
        for record in orphans
    ]

    logger.info(f"Found {len(records)} orphan records")

    return {
        "count": len(records),
        "records": records
    }
