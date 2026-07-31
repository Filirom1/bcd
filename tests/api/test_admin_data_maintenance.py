from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.bcd_api.api.v1 import admin


def test_set_acquisition_dates_updates_valid_publication_years():
    valid = SimpleNamespace(bibliographic_record=SimpleNamespace(publication_year=2020), acquisition_date=None)
    invalid = SimpleNamespace(bibliographic_record=SimpleNamespace(publication_year=2200), acquisition_date=None)
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.all.return_value = [valid, invalid]
    result = admin.set_acquisition_dates_from_publication_year(db)
    assert result == {"updated_count": 1}
    assert valid.acquisition_date == date(2020, 1, 1)
    assert invalid.acquisition_date is None
    db.commit.assert_called_once()


def test_set_acquisition_dates_does_not_commit_when_nothing_changes():
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.all.return_value = []
    assert admin.set_acquisition_dates_from_publication_year(db) == {"updated_count": 0}
    db.commit.assert_not_called()
