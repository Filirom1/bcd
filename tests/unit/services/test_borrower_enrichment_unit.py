from unittest.mock import MagicMock

from src.bcd_api.models.borrower import Borrower
from src.bcd_api.services.borrower._enrichment import (
    ClassDetails,
    Counts,
    apply_borrower_enrichment,
    circulation_counts_by_borrower,
    class_details_by_id,
)
from src.bcd_api.services.circulation.policy import CirculationPolicy


def test_circulation_counts_by_borrower_empty():
    assert circulation_counts_by_borrower(None, []) == {}
    assert circulation_counts_by_borrower(object(), [1]) == {}


def test_class_details_by_id_empty():
    assert class_details_by_id(None, []) == {}
    assert class_details_by_id(None, [None]) == {}
    assert class_details_by_id(object(), [1]) == {}


def test_apply_borrower_enrichment_no_class():
    borrower = Borrower(
        borrower_id="B001",
        first_name="Jean",
        last_name="Dupont",
        full_name="Jean Dupont",
        role="student",
        active=True,
    )
    counts = Counts(current_loans_count=2, overdue_count=1)
    policy = CirculationPolicy(
        default_loan_limit=5,
        teacher_loan_limit=10,
        kids_warning_limit=2,
        loan_duration_days=14,
        renewal_limit=2,
    )
    apply_borrower_enrichment(
        borrower,
        counts,
        class_details=None,
        policy=policy,
        settings_warning=True,
    )
    assert borrower.class_name is None
    assert borrower.homeroom_teacher is None
    assert borrower.current_loans_count == 2
    assert borrower.overdue_count == 1
    assert borrower.loan_limit == 5
    assert borrower.loan_limit_warning is True


def test_circulation_counts_by_borrower_with_db():
    db = MagicMock()
    # Mock query.filter().group_by().all() to return some records
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
        (1, 3),  # (borrower_id, count)
    ]
    res = circulation_counts_by_borrower(db, [1, 2])
    assert res[1] == Counts(current_loans_count=3, overdue_count=3)
    assert res[2] == Counts(current_loans_count=0, overdue_count=0)


def test_class_details_by_id_with_db():
    class_obj = MagicMock()
    class_obj.id = 10
    class_obj.name = "CM1"
    class_obj.homeroom_teacher = "M. Martin"

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [class_obj]

    res = class_details_by_id(db, [10])
    assert res[10] == ClassDetails(class_name="CM1", homeroom_teacher="M. Martin")
