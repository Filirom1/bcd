"""Catalog Usage Reports (Internal)

Handles reports about unborrowed items, highly circulated titles,
and other catalog usage patterns.
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ...models.bibliographic_record import BibliographicRecord
from ...models.circulation import CirculationTransaction
from ...models.item import Item

logger = logging.getLogger(__name__)


def _deserialize_authors(authors) -> str:
    """Helper function to deserialize authors JSON field."""
    if isinstance(authors, str):
        try:
            authors_list = json.loads(authors)
            return ", ".join(authors_list) if authors_list else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def get_never_borrowed_items(
    db: Session,
    academic_year: Optional[str] = None,
    level: Optional[str] = None,
    target_audience: Optional[str] = None,
    medium_type: Optional[str] = None,
    min_age_days: Optional[int] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get items that have never been borrowed with advanced filtering.
    """
    borrowed_items = db.query(CirculationTransaction.item_id).distinct()

    query = db.query(
        BibliographicRecord,
        Item,
    ).join(
        Item, BibliographicRecord.id == Item.bibliographic_record_id
    ).filter(
        Item.id.notin_(borrowed_items)
    )

    if academic_year:
        if "-" in academic_year:
            start_year = int(academic_year.split("-")[0])
            start_date = date(start_year, 9, 1)
            end_date = date(start_year + 1, 8, 31)

            query = query.filter(
                and_(
                    Item.acquisition_date >= start_date,
                    Item.acquisition_date <= end_date,
                )
            )

    if level:
        query = query.filter(BibliographicRecord.level.ilike(f"%{level}%"))

    if target_audience:
        query = query.filter(BibliographicRecord.target_audience == target_audience)

    if medium_type:
        query = query.filter(BibliographicRecord.medium_type == medium_type)

    if min_age_days:
        cutoff_date = date.today() - timedelta(days=min_age_days)
        query = query.filter(Item.acquisition_date <= cutoff_date)

    query = query.order_by(BibliographicRecord.title)

    total_count = query.count()

    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    results = query.all()

    never_borrowed = []
    today = date.today()

    for biblio, item in results:
        age_days = None
        if item.acquisition_date:
            age_days = (today - item.acquisition_date).days

        never_borrowed.append({
            "bibliographic_record_id": biblio.id,
            "item_id": item.item_id,
            "item_barcode": item.item_id,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "publisher": biblio.publisher,
            "level": biblio.level,
            "target_audience": biblio.target_audience,
            "medium_type": biblio.medium_type,
            "language": biblio.language,
            "publication_year": biblio.publication_year,
            "acquisition_date": item.acquisition_date,
            "age_days": age_days,
            "call_number": item.call_number,
            "shelf_location": item.shelf_location,
            "status": item.status,
            "condition": item.condition,
            "loanable": item.loanable,
        })

    return never_borrowed, total_count


def get_most_borrowed_titles(
    db: Session,
    period: str = "year",
    limit: Optional[int] = 20,
    offset: Optional[int] = None,
    medium_type: Optional[str] = None,
    target_audience: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get most borrowed titles by circulation count.
    """
    from sqlalchemy import func

    today = datetime.utcnow()
    if period == "week":
        cutoff_date = today - timedelta(days=7)
    elif period == "month":
        cutoff_date = today - timedelta(days=30)
    elif period == "year":
        cutoff_date = today - timedelta(days=365)
    else:
        cutoff_date = None

    query = db.query(
        BibliographicRecord.id,
        BibliographicRecord.title,
        BibliographicRecord.authors,
        BibliographicRecord.publisher,
        BibliographicRecord.publication_year,
        BibliographicRecord.medium_type,
        BibliographicRecord.target_audience,
        func.count(CirculationTransaction.id).label("checkout_count"),
    ).join(
        Item, BibliographicRecord.id == Item.bibliographic_record_id
    ).join(
        CirculationTransaction, Item.id == CirculationTransaction.item_id
    )

    if cutoff_date:
        query = query.filter(CirculationTransaction.checkout_date >= cutoff_date)

    if medium_type:
        query = query.filter(BibliographicRecord.medium_type == medium_type)

    if target_audience:
        query = query.filter(BibliographicRecord.target_audience == target_audience)

    query = query.group_by(
        BibliographicRecord.id,
        BibliographicRecord.title,
        BibliographicRecord.authors,
        BibliographicRecord.publisher,
        BibliographicRecord.publication_year,
        BibliographicRecord.medium_type,
        BibliographicRecord.target_audience,
    ).order_by(
        desc("checkout_count")
    )

    total_count = query.count()

    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    results = query.all()

    most_borrowed = []
    for biblio_id, title, authors, publisher, pub_year, med_type, audience_val, count in results:
        total_copies = db.query(func.count(Item.id)).filter(
            Item.bibliographic_record_id == biblio_id
        ).scalar()

        most_borrowed.append({
            "bibliographic_record_id": biblio_id,
            "title": title,
            "author": _deserialize_authors(authors),
            "publisher": publisher,
            "publication_year": pub_year,
            "medium_type": med_type,
            "target_audience": audience_val,
            "checkout_count": count,
            "total_copies": total_copies,
            "rank": len(most_borrowed) + 1,
        })

    return most_borrowed, total_count
