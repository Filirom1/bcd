from datetime import date

from src.bcd_api.services.holds._policy import (
    hold_expiration_date,
    is_hold_expired,
    is_transition_allowed,
)


def test_hold_expiration_date():
    base_date = date(2023, 10, 15)
    assert hold_expiration_date(base_date, 1) == date(2023, 10, 16)
    assert hold_expiration_date(base_date, 3) == date(2023, 10, 18)
    assert hold_expiration_date(base_date, 7) == date(2023, 10, 22)

    # Passage de fin de mois (31 jan -> 3 fév)
    end_of_jan = date(2023, 1, 31)
    assert hold_expiration_date(end_of_jan, 3) == date(2023, 2, 3)

    # Passage d'année (30 déc -> 2 jan)
    end_of_year = date(2023, 12, 30)
    assert hold_expiration_date(end_of_year, 3) == date(2024, 1, 2)


def test_is_hold_expired():
    today = date(2023, 10, 15)
    assert not is_hold_expired(None, today)
    assert is_hold_expired(date(2023, 10, 14), today)  # yesterday -> expired
    assert not is_hold_expired(date(2023, 10, 15), today)  # today -> still valid
    assert not is_hold_expired(date(2023, 10, 16), today)  # tomorrow -> valid


def test_is_transition_allowed():
    assert is_transition_allowed("mark_ready", "waiting") is True
    assert is_transition_allowed("mark_ready", "ready") is False
    assert is_transition_allowed("fulfill", "ready") is True
    assert is_transition_allowed("fulfill", "waiting") is False
    assert is_transition_allowed("cancel", "waiting") is True
    assert is_transition_allowed("cancel", "ready") is True
    assert is_transition_allowed("cancel", "cancelled") is False
    assert is_transition_allowed("cancel", "fulfilled") is False
    assert is_transition_allowed("cancel", "expired") is False
    assert is_transition_allowed("unknown", "waiting") is False
