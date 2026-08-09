"""Stats Reports (Internal)

Handles aggregated library collection statistics, circulation statistics,
and individual borrower metrics.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ...models.bibliographic_record import BibliographicRecord
from ...models.borrower import Borrower
from ...models.circulation import CirculationTransaction
from ...models.item import Item

logger = logging.getLogger(__name__)


def get_collection_stats(
    db: Session,
    crew_method: str = "never_borrowed",
    min_age_years: float = 0.0,
    exclude_periodicals: bool = True,
    medium_type: Optional[str] = None,
    target_audience: Optional[str] = None,
    condition: Optional[str] = None,
    pub_year_min: Optional[int] = None,
    pub_year_max: Optional[int] = None,
    acq_year_min: Optional[int] = None,
    acq_year_max: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute aggregation stats for the collection report (breakdowns + histograms).
    """
    today = date.today()

    def _base_query(db, exclude_medium_type=False,
                    exclude_target_audience=False, exclude_condition=False,
                    exclude_pub_year=False, exclude_acq_year=False):
        """Build the base filtered query for aggregations."""
        q = db.query(Item, BibliographicRecord).join(
            BibliographicRecord, Item.bibliographic_record_id == BibliographicRecord.id
        )

        if crew_method == "never_borrowed":
            q = q.filter(Item.last_borrowed_at.is_(None))
        elif crew_method == "low_circulation":
            since = date(today.year - 2, today.month, today.day)
            loan_counts = (
                db.query(CirculationTransaction.item_id, func.count().label("cnt"))
                .filter(CirculationTransaction.checkout_date >= since)
                .group_by(CirculationTransaction.item_id)
                .subquery()
            )
            q = q.outerjoin(loan_counts, loan_counts.c.item_id == Item.id)
            q = q.filter(func.coalesce(loan_counts.c.cnt, 0) <= 2)
        elif crew_method == "damaged_old":
            q = q.filter(Item.condition == "damaged")
            if min_age_years <= 0:
                cutoff = date(today.year - 3, today.month, today.day)
                q = q.filter(Item.acquisition_date <= cutoff)
        elif crew_method == "never_inventoried":
            q = q.filter(Item.last_inventoried_at.is_(None))

        if min_age_years > 0 and crew_method != "damaged_old":
            days = int(min_age_years * 365.25)
            cutoff = today - timedelta(days=days)
            q = q.filter(Item.acquisition_date.isnot(None))
            q = q.filter(Item.acquisition_date <= cutoff)

        if exclude_periodicals:
            q = q.filter(BibliographicRecord.medium_type != "Périodique")

        if medium_type and not exclude_medium_type:
            q = q.filter(BibliographicRecord.medium_type == medium_type)
        if target_audience and not exclude_target_audience:
            q = q.filter(BibliographicRecord.target_audience == target_audience)
        if condition and not exclude_condition:
            q = q.filter(Item.condition == condition)
        if pub_year_min is not None and not exclude_pub_year:
            q = q.filter(BibliographicRecord.publication_year >= pub_year_min)
        if pub_year_max is not None and not exclude_pub_year:
            q = q.filter(BibliographicRecord.publication_year <= pub_year_max)
        if acq_year_min is not None and not exclude_acq_year:
            q = q.filter(func.strftime("%Y", Item.acquisition_date) >= str(acq_year_min))
        if acq_year_max is not None and not exclude_acq_year:
            q = q.filter(func.strftime("%Y", Item.acquisition_date) <= str(acq_year_max))

        return q

    def _breakdown(q, group_col, label_col=None):
        """Run a GROUP BY count + damaged_count on the query."""
        col = label_col or group_col
        rows = (
            q.with_entities(
                col,
                func.count(Item.id).label("count"),
                func.sum(case((Item.condition == "damaged", 1), else_=0)).label("damaged_count"),
            )
            .filter(col.isnot(None))
            .group_by(col)
            .order_by(func.count(Item.id).desc())
            .all()
        )
        return [{"value": r[0], "count": r[1], "damaged_count": r[2] or 0} for r in rows]

    medium_rows = _breakdown(_base_query(db, exclude_medium_type=True), BibliographicRecord.medium_type)
    audience_rows = _breakdown(_base_query(db, exclude_target_audience=True), BibliographicRecord.target_audience)
    condition_rows = _breakdown(_base_query(db, exclude_condition=True), Item.condition)

    pub_q = _base_query(db, exclude_pub_year=True)
    pub_rows = (
        pub_q.with_entities(
            BibliographicRecord.publication_year,
            func.count(Item.id).label("count"),
            func.sum(case((Item.condition == "damaged", 1), else_=0)).label("damaged_count"),
        )
        .filter(BibliographicRecord.publication_year.isnot(None))
        .group_by(BibliographicRecord.publication_year)
        .order_by(BibliographicRecord.publication_year)
        .all()
    )
    pub_histogram = [{"year": r[0], "count": r[1], "damaged_count": r[2] or 0} for r in pub_rows]

    acq_q = _base_query(db, exclude_acq_year=True)
    acq_rows = (
        acq_q.with_entities(
            func.strftime("%Y", Item.acquisition_date).label("acq_year"),
            func.count(Item.id).label("count"),
            func.sum(case((Item.condition == "damaged", 1), else_=0)).label("damaged_count"),
        )
        .filter(Item.acquisition_date.isnot(None))
        .group_by("acq_year")
        .order_by("acq_year")
        .all()
    )
    acq_histogram = [{"year": int(r[0]), "count": r[1], "damaged_count": r[2] or 0} for r in acq_rows]

    total = _base_query(db).count()

    return {
        "total_count": total,
        "breakdowns": {
            "medium_type": medium_rows,
            "target_audience": audience_rows,
            "condition": condition_rows,
        },
        "pub_year_histogram": pub_histogram,
        "acq_year_histogram": acq_histogram,
    }


def get_circulation_statistics(
    db: Session,
    period: str = "year",
) -> Dict[str, Any]:
    """
    Get overall circulation statistics.
    """
    from sqlalchemy import and_

    today = datetime.utcnow()
    if period == "month":
        cutoff_date = today - timedelta(days=30)
        period_label = "Last 30 days"
    elif period == "year":
        cutoff_date = today - timedelta(days=365)
        period_label = "Last year"
    else:
        cutoff_date = None
        period_label = "All time"

    base_query = db.query(CirculationTransaction)
    if cutoff_date:
        base_query = base_query.filter(CirculationTransaction.checkout_date >= cutoff_date)

    total_checkouts = base_query.count()

    items_on_loan = db.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.is_(None)
    ).count()

    overdue_count = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < datetime.utcnow().date(),
        )
    ).count()

    active_borrowers = db.query(
        func.count(func.distinct(CirculationTransaction.borrower_id))
    ).filter(
        CirculationTransaction.return_date.is_(None)
    ).scalar()

    avg_loans_per_day = None
    if cutoff_date:
        days = (today - cutoff_date).days
        if days > 0:
            avg_loans_per_day = round(total_checkouts / days, 2)

    renewals_count = base_query.filter(CirculationTransaction.renewal_count > 0).count()

    late_returns = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.return_date.isnot(None),
            CirculationTransaction.return_date > CirculationTransaction.due_date,
        )
    )
    if cutoff_date:
        late_returns = late_returns.filter(CirculationTransaction.checkout_date >= cutoff_date)
    late_returns_count = late_returns.count()

    returned_items = db.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.isnot(None)
    )
    if cutoff_date:
        returned_items = returned_items.filter(CirculationTransaction.checkout_date >= cutoff_date)
    returned_count = returned_items.count()

    late_return_rate = (
        round((late_returns_count / returned_count) * 100, 1) if returned_count > 0 else 0
    )

    return {
        "period": period_label,
        "total_checkouts": total_checkouts,
        "items_on_loan": items_on_loan,
        "overdue_items": overdue_count,
        "active_borrowers": active_borrowers,
        "average_loans_per_day": avg_loans_per_day,
        "renewals": renewals_count,
        "late_returns": late_returns_count,
        "late_return_rate": late_return_rate,
        "returned_items": returned_count,
    }


def get_borrower_statistics(
    db: Session,
    borrower_id: int,
) -> Dict[str, Any]:
    """
    Get statistics for a specific borrower.
    """
    from sqlalchemy import and_

    total_checkouts = db.query(CirculationTransaction).filter(
        CirculationTransaction.borrower_id == borrower_id
    ).count()

    current_loans = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.is_(None),
        )
    ).count()

    overdue = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < datetime.utcnow().date(),
        )
    ).count()

    total_renewals = db.query(
        func.sum(CirculationTransaction.renewal_count)
    ).filter(
        CirculationTransaction.borrower_id == borrower_id
    ).scalar() or 0

    late_returns = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.isnot(None),
            CirculationTransaction.return_date > CirculationTransaction.due_date,
        )
    ).count()

    returned = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.isnot(None),
        )
    ).count()

    late_return_rate = round((late_returns / returned) * 100, 1) if returned > 0 else 0

    return {
        "total_checkouts": total_checkouts,
        "current_loans": current_loans,
        "overdue_items": overdue,
        "total_renewals": int(total_renewals),
        "late_returns": late_returns,
        "late_return_rate": late_return_rate,
    }
