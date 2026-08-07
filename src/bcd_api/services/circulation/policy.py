"""Circulation Policy - Pure domain rules for limits, due dates, and overdues.

This module is a "pure" library containing stateless business logic.
It has zero dependencies on SQLAlchemy, FastAPI, or any database connection.
All parameters (like current dates or limits) are injected explicitly.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class CheckoutDecision:
    """Represents the outcome of a checkout limits validation."""
    allowed: bool
    reason: Optional[str] = None
    error_code: Optional[str] = None


@dataclass(frozen=True)
class RenewalDecision:
    """Represents the outcome of a renewal validation."""
    allowed: bool
    reason: Optional[str] = None
    error_code: Optional[str] = None


@dataclass(frozen=True)
class CirculationPolicy:
    """Pure domain policies for checkout and renewal limits."""
    default_loan_limit: int
    teacher_loan_limit: int
    kids_warning_limit: int
    loan_duration_days: int
    renewal_limit: int

    @classmethod
    def from_settings(cls, settings) -> "CirculationPolicy":
        """Factory method to construct policy from DB settings object."""
        return cls(
            default_loan_limit=settings.loan_limit_default,
            teacher_loan_limit=settings.loan_limit_teacher,
            kids_warning_limit=settings.loan_limit_warning,
            loan_duration_days=settings.loan_duration_days,
            renewal_limit=settings.renewal_limit,
        )

    def loan_limit_for(self, role: str) -> int:
        """Get maximum active loans allowed based on borrower role."""
        if role in ("teacher", "staff"):
            return self.teacher_loan_limit
        return self.default_loan_limit

    def checkout_decision(
        self,
        role: str,
        current_loans_count: int,
        additional_count: int,
        is_godot_ui: bool,
    ) -> CheckoutDecision:
        """Validate if checkout is permitted based on borrower role and current loan counts."""
        limit = self.loan_limit_for(role)

        # Check kids warning limit first if request is from kids Godot client
        if is_godot_ui and self.kids_warning_limit > 0:
            if role not in ("teacher", "staff") and current_loans_count + additional_count > self.kids_warning_limit:
                return CheckoutDecision(
                    allowed=False,
                    reason="LOAN_LIMIT_WARNING_EXCEEDED",
                    error_code="LOAN_LIMIT_WARNING_EXCEEDED",
                )

        # Check strict limit
        if current_loans_count + additional_count > limit:
            return CheckoutDecision(
                allowed=False,
                reason="LOAN_LIMIT_EXCEEDED",
                error_code="LOAN_LIMIT_EXCEEDED",
            )

        return CheckoutDecision(allowed=True)

    def checkout_due_date(self, today: date) -> date:
        """Calculate the due date from checkout date."""
        return today + timedelta(days=self.loan_duration_days)

    def renewed_due_date(self, previous_due_date: date) -> date:
        """Calculate the new due date from previous due date."""
        return previous_due_date + timedelta(days=self.loan_duration_days)

    def renewal_decision(self, renewal_count: int, has_active_hold: bool) -> RenewalDecision:
        """Validate if a loan renewal is allowed."""
        if has_active_hold:
            return RenewalDecision(
                allowed=False,
                reason="ITEM_HAS_HOLDS",
                error_code="ITEM_HAS_HOLDS",
            )

        if renewal_count >= self.renewal_limit:
            return RenewalDecision(
                allowed=False,
                reason="RENEWAL_LIMIT_EXCEEDED",
                error_code="RENEWAL_LIMIT_EXCEEDED",
            )

        return RenewalDecision(allowed=True)


# Pure utility functions

def is_overdue(due_date: date, observed_on: date) -> bool:
    """Check if the loan is overdue relative to an observed date."""
    return due_date < observed_on


def overdue_days(due_date: date, observed_on: date) -> int:
    """Calculate the number of days overdue relative to an observed date (0 if not overdue)."""
    if due_date >= observed_on:
        return 0
    return (observed_on - due_date).days


def was_returned_late(due_date: date, returned_at: datetime) -> bool:
    """Check if a loan was returned after its due date."""
    return returned_at.date() > due_date
