"""Unit tests for pure circulation policy rules."""

from datetime import date, datetime

import pytest

from src.bcd_api.services.circulation.policy import (
    CirculationPolicy,
    is_overdue,
    overdue_days,
    was_returned_late,
)


@pytest.fixture
def policy():
    return CirculationPolicy(
        default_loan_limit=2,
        teacher_loan_limit=5,
        kids_warning_limit=1,
        loan_duration_days=14,
        renewal_limit=2,
    )


def test_loan_limit_for(policy):
    assert policy.loan_limit_for("student") == 2
    assert policy.loan_limit_for("teacher") == 5
    assert policy.loan_limit_for("staff") == 5


def test_checkout_decision_student_under_limit(policy):
    decision = policy.checkout_decision(
        role="student",
        current_loans_count=0,
        additional_count=1,
        is_godot_ui=False,
    )
    assert decision.allowed is True


def test_checkout_decision_student_exceeds_limit(policy):
    decision = policy.checkout_decision(
        role="student",
        current_loans_count=2,
        additional_count=1,
        is_godot_ui=False,
    )
    assert decision.allowed is False
    assert decision.error_code == "LOAN_LIMIT_EXCEEDED"


def test_checkout_decision_teacher_higher_limit(policy):
    decision = policy.checkout_decision(
        role="teacher",
        current_loans_count=3,
        additional_count=1,
        is_godot_ui=False,
    )
    assert decision.allowed is True


def test_checkout_decision_godot_warning_exceeded(policy):
    # Warning limit is 1, so 1 current loan + 1 additional loan = 2, which exceeds warning limit 1
    decision = policy.checkout_decision(
        role="student",
        current_loans_count=1,
        additional_count=1,
        is_godot_ui=True,
    )
    assert decision.allowed is False
    assert decision.error_code == "LOAN_LIMIT_WARNING_EXCEEDED"


def test_checkout_decision_godot_warning_teacher_ignored(policy):
    # Warning limits only apply to students
    decision = policy.checkout_decision(
        role="teacher",
        current_loans_count=1,
        additional_count=1,
        is_godot_ui=True,
    )
    assert decision.allowed is True


def test_checkout_due_date(policy):
    today = date(2026, 1, 1)
    assert policy.checkout_due_date(today) == date(2026, 1, 15)


def test_renewed_due_date(policy):
    prev_due = date(2026, 1, 15)
    assert policy.renewed_due_date(prev_due) == date(2026, 1, 29)


def test_renewal_decision_allowed(policy):
    decision = policy.renewal_decision(renewal_count=1, has_active_hold=False)
    assert decision.allowed is True


def test_renewal_decision_limit_reached(policy):
    decision = policy.renewal_decision(renewal_count=2, has_active_hold=False)
    assert decision.allowed is False
    assert decision.error_code == "RENEWAL_LIMIT_EXCEEDED"


def test_renewal_decision_blocked_by_hold(policy):
    decision = policy.renewal_decision(renewal_count=0, has_active_hold=True)
    assert decision.allowed is False
    assert decision.error_code == "ITEM_HAS_HOLDS"


def test_is_overdue():
    due_date = date(2026, 1, 15)
    assert is_overdue(due_date, date(2026, 1, 14)) is False
    assert is_overdue(due_date, date(2026, 1, 15)) is False
    assert is_overdue(due_date, date(2026, 1, 16)) is True


def test_overdue_days():
    due_date = date(2026, 1, 15)
    assert overdue_days(due_date, date(2026, 1, 14)) == 0
    assert overdue_days(due_date, date(2026, 1, 15)) == 0
    assert overdue_days(due_date, date(2026, 1, 16)) == 1
    assert overdue_days(due_date, date(2026, 1, 25)) == 10


def test_was_returned_late():
    due_date = date(2026, 1, 15)
    assert was_returned_late(due_date, datetime(2026, 1, 14, 12, 0)) is False
    assert was_returned_late(due_date, datetime(2026, 1, 15, 12, 0)) is False
    assert was_returned_late(due_date, datetime(2026, 1, 16, 12, 0)) is True
