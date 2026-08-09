"""Search helper for inventory query construction."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ...models.bibliographic_record import BibliographicRecord
from ...models.circulation import CirculationTransaction
from ...models.item import Item
from ...models.system_settings import SystemSettings

logger = logging.getLogger(__name__)


def escape_like_pattern(pattern: str) -> str:
    """Escape special characters in LIKE pattern to prevent wildcard injection.

    Escapes % and _ characters so they are treated as literals, not wildcards.

    Args:
        pattern: User input to use in LIKE clause

    Returns:
        Escaped pattern safe for LIKE query
    """
    if not pattern:
        return pattern
    # Escape backslash first, then % and _
    return pattern.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')


def build_item_search_query(
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
):
    """
    Constructs the base SQLAlchemy query with all filters applied.
    Returns: (query, period_loan_count_column)
    """
    # Start with base query joining bibliographic_record with all needed fields
    query = db.query(
        Item,
        BibliographicRecord.title,
        BibliographicRecord.authors,
        BibliographicRecord.level,
        BibliographicRecord.target_audience,
        BibliographicRecord.language,
        BibliographicRecord.medium_type,
        BibliographicRecord.publication_year
    ).join(BibliographicRecord)

    # Always add subquery for all-time circulation count per item
    circ_subquery = (
        db.query(
            CirculationTransaction.item_id,
            func.count().label('circ_count')
        )
        .group_by(CirculationTransaction.item_id)
        .subquery()
    )
    query = query.outerjoin(circ_subquery, circ_subquery.c.item_id == Item.id)
    query = query.add_columns(func.coalesce(circ_subquery.c.circ_count, 0).label('circulation_count'))

    # If rotation filter is active, add LEFT JOIN subquery for loan counts
    period_loan_count_column = None
    if max_borrows is not None and since_date is not None:
        # Subquery: count loans in period per item
        loan_subquery = (
            db.query(
                CirculationTransaction.item_id,
                func.count().label('period_count')
            )
            .filter(CirculationTransaction.checkout_date >= since_date)
            .group_by(CirculationTransaction.item_id)
            .subquery()
        )

        # Add LEFT JOIN to main query
        query = query.outerjoin(loan_subquery, loan_subquery.c.item_id == Item.id)
        period_loan_count_column = func.coalesce(loan_subquery.c.period_count, 0).label('period_loan_count')
        query = query.add_columns(period_loan_count_column)

        # Apply rotation filter
        query = query.filter(func.coalesce(loan_subquery.c.period_count, 0) <= max_borrows)

    # Apply text search filter (q)
    if q:
        q_safe = escape_like_pattern(q)
        query = query.filter(
            or_(
                BibliographicRecord.title.ilike(f'%{q_safe}%', escape='\\'),
                BibliographicRecord.authors.ilike(f'%{q_safe}%', escape='\\'),
                BibliographicRecord.isbn.ilike(f'%{q_safe}%', escape='\\'),
                Item.call_number.ilike(f'%{q_safe}%', escape='\\')
            )
        )

    # Apply item-level filters
    if status:
        query = query.filter(Item.status == status)
    if condition:
        query = query.filter(Item.condition == condition)
    if shelf_location == "__none__":
        query = query.filter(
            or_(Item.shelf_location.is_(None), Item.shelf_location == "")
        )
    elif shelf_location:
        shelf_safe = escape_like_pattern(shelf_location)
        query = query.filter(Item.shelf_location.ilike(f'%{shelf_safe}%', escape='\\'))

    # Apply inventory filters
    if never_inventoried:
        query = query.filter(Item.last_inventoried_at.is_(None))
    if inventoried_before:
        query = query.filter(
            or_(
                Item.last_inventoried_at.is_(None),
                Item.last_inventoried_at < inventoried_before
            )
        )

    # Apply acquisition date filter (for age in collection)
    if acquired_before:
        query = query.filter(
            and_(
                Item.acquisition_date.is_not(None),  # Only items WITH acquisition date
                Item.acquisition_date < acquired_before
            )
        )

    if acquired_after:
        query = query.filter(
            and_(
                Item.acquisition_date.is_not(None),
                Item.acquisition_date >= acquired_after
            )
        )

    # Apply record-level filters
    if medium_type == "__none__":
        query = query.filter(BibliographicRecord.medium_type.is_(None))
    elif medium_type:
        query = query.filter(BibliographicRecord.medium_type == medium_type)
    if target_audience == "__none__":
        query = query.filter(BibliographicRecord.target_audience.is_(None))
    elif target_audience:
        query = query.filter(BibliographicRecord.target_audience == target_audience)
    if level == "__none__":
        query = query.filter(BibliographicRecord.level.is_(None))
    elif level:
        level_safe = escape_like_pattern(level)
        query = query.filter(BibliographicRecord.level.ilike(f'%{level_safe}%', escape='\\'))
    if language == "__none__":
        query = query.filter(BibliographicRecord.language.is_(None))
    elif language:
        query = query.filter(BibliographicRecord.language == language)

    # Apply publication year range
    if publication_year_min is not None:
        query = query.filter(BibliographicRecord.publication_year >= publication_year_min)
    if publication_year_max is not None:
        query = query.filter(BibliographicRecord.publication_year <= publication_year_max)

    # Filter items never borrowed (last_borrowed_at IS NULL)
    if never_borrowed:
        query = query.filter(Item.last_borrowed_at.is_(None))

    return query, period_loan_count_column
