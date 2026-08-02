"""Query Filters for Circulation.

Provides reusable SQLAlchemy query predicates to avoid duplicate logic across domains.
"""

from sqlalchemy import and_

from ...models.circulation import CirculationTransaction


def active_loan_predicate():
    """SQLAlchemy predicate: item is currently on loan (not returned)."""
    return CirculationTransaction.return_date.is_(None)


def overdue_loan_predicate(today):
    """SQLAlchemy predicate: loan is currently active and overdue."""
    return and_(
        CirculationTransaction.return_date.is_(None),
        CirculationTransaction.due_date < today
    )
