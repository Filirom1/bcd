from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.bcd_api.services import archive_service


def test_archive_rejects_invalid_years():
    with pytest.raises(ValueError, match="at least 1"):
        archive_service.archive_old_transactions(MagicMock(), older_than_years=0)


def test_archive_empty_result_does_not_execute_or_commit():
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 0
    result = archive_service.archive_old_transactions(db, older_than_years=2)
    assert result["archived_count"] == 0
    assert result["dry_run"] is False
    db.execute.assert_not_called()
    db.commit.assert_not_called()


def test_archive_dry_run_returns_estimate():
    old = SimpleNamespace(checkout_date=datetime(2020, 1, 1, tzinfo=timezone.utc))
    query = MagicMock()
    query.count.return_value = 2
    query.order_by.side_effect = [query, query]
    query.first.side_effect = [old, old]
    db = MagicMock()
    db.query.return_value.filter.return_value = query
    result = archive_service.archive_old_transactions(db, older_than_years=2, dry_run=True)
    assert result["archived_count"] == 2
    assert result["dry_run"] is True
    assert result["size_reduction_estimate_mb"] == 0.0
    db.execute.assert_not_called()


def test_archive_stats_empty_result():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (0, None, None, None, None)
    result = archive_service.get_archive_stats(db)
    assert result["total_archived"] == 0
    assert result["estimated_size_mb"] == 0


def test_archive_stats_populated_result():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (10, "2020-01-01", "2024-01-01", "2024-02-01", "2024-02-02")
    result = archive_service.get_archive_stats(db)
    assert result["total_archived"] == 10
    assert result["oldest_transaction_date"] == "2020-01-01"
    assert result["estimated_size_mb"] == 0.0


def test_get_archived_transactions_maps_rows_and_filters():
    row = SimpleNamespace(_mapping={"id": 1, "borrower_id": 2})
    db = MagicMock()
    db.execute.return_value = [row]
    result = archive_service.get_archived_transactions(db, borrower_id=2, item_id=3, limit=5, offset=1)
    assert result == [{"id": 1, "borrower_id": 2}]
    params = db.execute.call_args.args[1]
    assert params == {"borrower_id": 2, "item_id": 3, "limit": 5, "offset": 1}


def test_archive_transactions_executes_insert_delete_and_commit():
    old = SimpleNamespace(checkout_date=datetime(2020, 1, 1, tzinfo=timezone.utc))
    query = MagicMock()
    query.count.return_value = 1
    query.order_by.return_value = query
    query.first.return_value = old
    db = MagicMock()
    db.query.return_value.filter.return_value = query
    result = archive_service.archive_old_transactions(db, older_than_years=2)
    assert result["archived_count"] == 1
    assert result["dry_run"] is False
    assert db.execute.call_count == 2
    db.commit.assert_called_once()
