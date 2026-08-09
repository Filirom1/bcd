from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.bcd_cli.commands.report import report


def resp(data, status=200):
    r = MagicMock(status_code=status)
    r.json.return_value = data
    r.text = "error"
    return r


def test_overdue_report_empty():
    client = MagicMock()
    client.get.return_value = resp({"total_overdue": 0, "items": []})
    with patch("src.bcd_cli.commands.report.get_client", return_value=client):
        result = CliRunner().invoke(report, ["overdue", "--class", "CP"])
    assert result.exit_code == 0
    assert "No overdue items" in result.output
    client.get.assert_called_once()


def test_overdue_report_shows_summary_and_details():
    client = MagicMock()
    client.get.side_effect = [
        resp({"total_overdue": 1, "items": [{"borrower_name": "Alice", "class_name": "CP", "item_id": "I1", "title": "Book", "due_date": "2025-01-01", "days_overdue": 3}]}),
        resp({"classes": [{"class_name": "CP", "overdue_count": 1}]}),
    ]
    with patch("src.bcd_cli.commands.report.get_client", return_value=client):
        result = CliRunner().invoke(report, ["overdue", "--academic-year", "2025-2026"])
    assert result.exit_code == 0
    assert "Alice" in result.output
    assert "CP" in result.output
    assert "+3j" in result.output


def test_most_borrowed_displays_titles():
    client = MagicMock()
    client.get.return_value = resp({"titles": [{"rank": 1, "title": "Book", "authors": "Author", "publication_year": 2024, "checkout_count": 8}]})
    with patch("src.bcd_cli.commands.report.get_client", return_value=client):
        result = CliRunner().invoke(report, ["most-borrowed", "--period", "month", "--limit", "5"])
    assert result.exit_code == 0
    assert "Book" in result.output
    assert client.get.call_args.kwargs["params"] == {"period": "month", "limit": 5}


def test_statistics_displays_counts():
    client = MagicMock()
    client.get.return_value = resp({"period": "year", "total_checkouts": 10, "items_on_loan": 2, "overdue_items": 1, "active_borrowers": 5, "average_loans_per_day": 0.5})
    with patch("src.bcd_cli.commands.report.get_client", return_value=client):
        result = CliRunner().invoke(report, ["statistics"])
    assert result.exit_code == 0
    assert "10" in result.output
    assert "0.5" in result.output


def test_never_borrowed_empty():
    client = MagicMock()
    client.get.return_value = resp({"total": 0, "items": []})
    with patch("src.bcd_cli.commands.report.get_client", return_value=client):
        result = CliRunner().invoke(report, ["never-borrowed", "--limit", "10"])
    assert result.exit_code == 0
    assert "All items have been borrowed" in result.output
