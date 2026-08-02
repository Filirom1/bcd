"""Integration tests for circulation query read operations."""

import pytest

from src.bcd_api.services.circulation import queries


def test_get_borrower_current_loans_not_found(db_session):
    with pytest.raises(Exception):
        queries.get_borrower_current_loans(db_session, "NON_EXISTENT")


def test_get_item_circulation_history_not_found(db_session):
    with pytest.raises(Exception):
        queries.get_item_circulation_history(db_session, "NON_EXISTENT")
