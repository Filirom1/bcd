from datetime import date, datetime, timedelta

from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.services.circulation import queries


def test_get_circulation_actions_returns_checkout_and_return_with_class_details(
    db_session, test_borrower_student, test_item_available
):
    start = datetime(2026, 10, 19, 9, 0)
    checkout = start + timedelta(minutes=5)
    returned = start + timedelta(minutes=25)
    transaction = CirculationTransaction(
        borrower_id=test_borrower_student.id,
        item_id=test_item_available.id,
        bibliographic_record_id=test_item_available.bibliographic_record_id,
        checkout_date=checkout,
        return_date=returned,
        due_date=date(2026, 11, 2),
        status="returned",
    )
    db_session.add(transaction)
    db_session.flush()

    actions = queries.get_circulation_actions(
        db_session,
        start=start,
        end=start + timedelta(hours=1),
        class_id=test_borrower_student.class_id,
    )
    return_only = queries.get_circulation_actions(
        db_session,
        start=start + timedelta(minutes=20),
        end=start + timedelta(minutes=30),
        class_id=test_borrower_student.class_id,
    )

    assert [(action.action, action.occurred_at) for action in actions] == [
        ("checkout", checkout),
        ("return", returned),
    ]
    assert actions[0].borrower_id == test_borrower_student.borrower_id
    assert actions[0].class_name == "CP-A"
    assert actions[0].homeroom_teacher == "Mme Dupont"
    assert actions[0].title == test_item_available.bibliographic_record.title
    assert actions[0].item_id == test_item_available.item_id
    assert [(action.action, action.occurred_at) for action in return_only] == [("return", returned)]


def test_get_circulation_actions_uses_exclusive_end_and_class_filter(
    db_session, test_borrower_student, test_item_available
):
    start = datetime(2026, 10, 19, 9, 0)
    transaction = CirculationTransaction(
        borrower_id=test_borrower_student.id,
        item_id=test_item_available.id,
        bibliographic_record_id=test_item_available.bibliographic_record_id,
        checkout_date=start + timedelta(hours=1),
        due_date=date(2026, 11, 2),
        status="active",
    )
    db_session.add(transaction)
    db_session.flush()

    actions = queries.get_circulation_actions(
        db_session,
        start=start,
        end=start + timedelta(hours=1),
        class_id=test_borrower_student.class_id,
    )
    in_range = queries.get_circulation_actions(
        db_session,
        start=start,
        end=start + timedelta(hours=2),
        class_id=test_borrower_student.class_id,
    )
    wrong_class = queries.get_circulation_actions(
        db_session,
        start=start,
        end=start + timedelta(hours=2),
        class_id=test_borrower_student.class_id + 1,
    )

    assert actions == []
    assert len(in_range) == 1
    assert in_range[0].action == "checkout"
    assert wrong_class == []


def test_get_circulation_activity_days_counts_checkouts_and_returns(
    db_session, test_borrower_student, test_item_available
):
    checkout_date = datetime(2026, 10, 16, 9, 0)
    return_date = datetime(2026, 10, 19, 10, 0)
    transaction = CirculationTransaction(
        borrower_id=test_borrower_student.id,
        item_id=test_item_available.id,
        bibliographic_record_id=test_item_available.bibliographic_record_id,
        checkout_date=checkout_date,
        return_date=return_date,
        due_date=date(2026, 10, 30),
        status="returned",
    )
    db_session.add(transaction)
    db_session.flush()

    days = queries.get_circulation_activity_days(
        db_session,
        class_id=test_borrower_student.class_id,
    )

    assert [
        (
            day.activity_date,
            day.checkout_count,
            day.return_count,
            day.first_action_at,
            day.last_action_at,
        )
        for day in days
    ] == [
        (date(2026, 10, 19), 0, 1, return_date, return_date),
        (date(2026, 10, 16), 1, 0, checkout_date, checkout_date),
    ]
