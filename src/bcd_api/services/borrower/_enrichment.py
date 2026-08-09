"""Private batch enrichment helpers for the borrower domain."""

from datetime import date
from typing import Dict, List, NamedTuple, Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.bcd_api.models import Class
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.services.circulation.query_filters import active_loan_predicate, overdue_loan_predicate
from src.bcd_api.services.circulation.policy import CirculationPolicy
from src.bcd_api.models.borrower import Borrower


class Counts(NamedTuple):
    current_loans_count: int
    overdue_count: int


class ClassDetails(NamedTuple):
    class_name: Optional[str]
    homeroom_teacher: Optional[str]


def circulation_counts_by_borrower(db: Session, borrower_ids: List[int]) -> Dict[int, Counts]:
    """Retrieve active and overdue loan counts for a list of borrower internal IDs in batch."""
    if not borrower_ids or not hasattr(db, "query"):
        return {}

    # Active loans
    active_rows = (
        db.query(CirculationTransaction.borrower_id, func.count(CirculationTransaction.id))
        .filter(
            and_(
                CirculationTransaction.borrower_id.in_(borrower_ids),
                active_loan_predicate()
            )
        )
        .group_by(CirculationTransaction.borrower_id)
        .all()
    )
    active_map = {row[0]: row[1] for row in active_rows}

    # Overdue loans
    overdue_rows = (
        db.query(CirculationTransaction.borrower_id, func.count(CirculationTransaction.id))
        .filter(
            and_(
                CirculationTransaction.borrower_id.in_(borrower_ids),
                overdue_loan_predicate(date.today())
            )
        )
        .group_by(CirculationTransaction.borrower_id)
        .all()
    )
    overdue_map = {row[0]: row[1] for row in overdue_rows}

    return {
        bid: Counts(
            current_loans_count=active_map.get(bid, 0),
            overdue_count=overdue_map.get(bid, 0)
        )
        for bid in borrower_ids
    }


def class_details_by_id(db: Session, class_ids: List[int]) -> Dict[int, ClassDetails]:
    """Retrieve class names and homeroom teachers for a list of class IDs in batch."""
    unique_class_ids = [cid for cid in set(class_ids) if cid is not None]
    if not unique_class_ids or not hasattr(db, "query"):
        return {}

    classes = db.query(Class).filter(Class.id.in_(unique_class_ids)).all()
    return {
        c.id: ClassDetails(class_name=c.name, homeroom_teacher=c.homeroom_teacher)
        for c in classes
    }


def apply_borrower_enrichment(
    borrower: Borrower,
    counts: Counts,
    class_details: Optional[ClassDetails],
    policy: CirculationPolicy,
    settings_warning: bool,
) -> Borrower:
    """Apply enriched attributes to a borrower instance."""
    borrower.current_loans_count = counts.current_loans_count
    borrower.loan_limit = policy.loan_limit_for(borrower.role)
    borrower.loan_limit_warning = settings_warning
    borrower.overdue_count = counts.overdue_count
    if class_details:
        borrower.class_name = class_details.class_name
        borrower.homeroom_teacher = class_details.homeroom_teacher
    else:
        borrower.class_name = None
        borrower.homeroom_teacher = None
    return borrower
