from types import SimpleNamespace
from unittest.mock import MagicMock

from src.bcd_api.services import inventory_service


def test_escape_like_pattern_escapes_wildcards():
    assert inventory_service._escape_like_pattern(r"a%b_c\\d") == r"a\%b\_c\\\\d"
    assert inventory_service._escape_like_pattern("") == ""


def test_bulk_mark_inventoried_reports_missing_ids():
    first = SimpleNamespace(item_id="I1", last_inventoried_at=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [first]
    result = inventory_service.bulk_mark_inventoried(db, ["I1", "MISSING"])
    assert result["items_updated"] == 1
    assert result["items_not_found"] == ["MISSING"]
    assert first.last_inventoried_at is not None
    db.commit.assert_called_once()


def test_bulk_mark_inventoried_empty_input_commits_empty_result():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    result = inventory_service.bulk_mark_inventoried(db, [])
    assert result["items_updated"] == 0
    assert result["items_not_found"] == []
    db.commit.assert_called_once()
