"""Loan Reports (Internal)

Handles reports about currently active or overdue loans, holds, and reservations.
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...models.bibliographic_record import BiblographicRecord
from ...models.borrower import Borrower
from ...models.circulation import CirculationTransaction
from ...models.class_model import Class
from ...models.hold import Hold
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


def get_overdue_items(
    db: Session,
    class_name: Optional[str] = None,
    academic_year: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all currently overdue items.
    """
    today = datetime.utcnow().date()

    query = db.query(
        CirculationTransaction,
        Borrower,
        Item,
        BiblographicRecord,
        Class,
    ).join(
        Borrower, CirculationTransaction.borrower_id == Borrower.id
    ).join(
        Item, CirculationTransaction.item_id == Item.id
    ).join(
        BiblographicRecord, Item.bibliographic_record_id == BiblographicRecord.id
    ).outerjoin(
        Class, Borrower.class_id == Class.id
    ).filter(
        and_(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < today,
        )
    )

    if class_name:
        query = query.filter(Class.name == class_name)

    query = query.order_by(CirculationTransaction.due_date)

    results = query.all()

    overdue_items = []
    for circ, borrower, item, biblio, class_obj in results:
        days_overdue = (today - circ.due_date).days

        overdue_items.append({
            "circulation_id": circ.id,
            "borrower_id": borrower.borrower_id,
            "borrower_name": borrower.full_name,
            "class_name": class_obj.name if class_obj else None,
            "item_id": item.item_id,
            "record_id": biblio.id,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "checkout_date": circ.checkout_date.date(),
            "due_date": circ.due_date,
            "days_overdue": days_overdue,
        })

    return overdue_items


def get_overdue_summary_by_class(
    db: Session,
    academic_year: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get summary of overdue items grouped by class.
    """
    from sqlalchemy import func

    today = datetime.utcnow().date()

    query = db.query(
        Class.name,
        func.count(CirculationTransaction.id).label("overdue_count"),
    ).join(
        Borrower, Class.id == Borrower.class_id
    ).join(
        CirculationTransaction, Borrower.id == CirculationTransaction.borrower_id
    ).filter(
        and_(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < today,
        )
    ).group_by(Class.name)

    query = query.order_by(Class.name)

    results = query.all()

    return [
        {"class_name": class_name, "overdue_count": count}
        for class_name, count in results
    ]


def get_holds_report(
    db: Session,
    status: Optional[str] = None,
    class_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get holds/reservations report with filtering by status and class.
    """
    query = db.query(Hold, Borrower, BiblographicRecord, Class).join(
        Borrower, Hold.borrower_id == Borrower.id
    ).join(
        BiblographicRecord, Hold.bibliographic_record_id == BiblographicRecord.id
    ).outerjoin(
        Class, Borrower.class_id == Class.id
    )

    if status:
        query = query.filter(Hold.status == status)
    else:
        query = query.filter(Hold.status.in_(["waiting", "ready", "expired"]))

    if class_name:
        query = query.filter(Class.name == class_name)

    results = query.order_by(Hold.status, Hold.queue_position).all()

    today = date.today()
    holds_list = []
    for hold, borrower, biblio, class_obj in results:
        hold_dict = {
            "hold_id": hold.id,
            "borrower_id": borrower.borrower_id,
            "borrower_name": borrower.full_name,
            "class_name": class_obj.name if class_obj else None,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "status": hold.status,
            "hold_date": hold.hold_date,
            "queue_position": hold.queue_position,
        }

        if hold.status == "ready":
            hold_dict["available_date"] = hold.available_date
            hold_dict["expiration_date"] = hold.expiration_date
            if hold.expiration_date:
                days_until_expiration = (hold.expiration_date - today).days
                hold_dict["days_until_expiration"] = days_until_expiration

        holds_list.append(hold_dict)

    return holds_list


def get_active_loans(
    db: Session,
    class_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all active loans (items currently checked out).
    """
    query = db.query(CirculationTransaction, Borrower, Item, BiblographicRecord, Class).join(
        Borrower, CirculationTransaction.borrower_id == Borrower.id
    ).join(
        Item, CirculationTransaction.item_id == Item.id
    ).join(
        BiblographicRecord, CirculationTransaction.bibliographic_record_id == BiblographicRecord.id
    ).outerjoin(
        Class, Borrower.class_id == Class.id
    ).filter(
        CirculationTransaction.return_date.is_(None)
    )

    if class_name:
        query = query.filter(Class.name == class_name)

    results = query.order_by(CirculationTransaction.due_date).all()

    today = date.today()
    loans_list = []
    for circ, borrower, item, biblio, class_obj in results:
        days_until_due = (circ.due_date - today).days
        is_overdue = circ.due_date < today

        loans_list.append({
            "circulation_id": circ.id,
            "borrower_id": borrower.borrower_id,
            "borrower_name": borrower.full_name,
            "class_name": class_obj.name if class_obj else None,
            "item_id": item.item_id,
            "bibliographic_record_id": biblio.id,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "checkout_date": circ.checkout_date,
            "due_date": circ.due_date,
            "days_until_due": days_until_due,
            "is_overdue": is_overdue,
            "renewal_count": circ.renewal_count,
        })

    return loans_list
