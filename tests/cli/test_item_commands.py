from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.item import item


def response(status_code, payload=None, text="error"):
    result = MagicMock()
    result.status_code = status_code
    result.text = text
    result.json.return_value = payload or {}
    return result


def test_item_status_success_with_bibliographic_and_loan_details():
    client = MagicMock()
    client.get.side_effect = [
        response(200, {"bibliographic_record_id": 3, "call_number": "A-1", "status": "on_loan", "condition": "good", "loanable": True}),
        response(200, {"title": "Le livre", "authors": ["A", "B"]}),
        response(200, {"class_name": "CM1"}),
    ]
    client.get_item_history.return_value = {"current_loan": {"borrower_id": "12", "borrower_name": "Alice", "checkout_date": "2026-01-01", "due_date": "2026-01-10"}}
    with patch("bcd_cli.commands.item.get_client", return_value=client):
        result = CliRunner().invoke(item, ["status", "I1"])
    assert result.exit_code == 0
    assert "Le livre" in result.output
    assert "Alice" in result.output
    assert "CM1" in result.output


def test_item_status_not_found():
    client = MagicMock()
    client.get.return_value = response(404)
    with patch("bcd_cli.commands.item.get_client", return_value=client):
        result = CliRunner().invoke(item, ["status", "missing"])
    assert result.exit_code == 0
    assert "missing" in result.output


def test_item_history_displays_current_loan_and_limits_history():
    client = MagicMock()
    client.get.return_value = response(200, {
        "title": "Book",
        "current_loan": {"borrower_full_name": "A very long borrower name", "class_name": "CE2", "checkout_date": "2026-01-01", "due_date": "2026-01-10"},
        "history": [
            {"borrower_full_name": "A very long borrower name", "class_name": "CM1", "checkout_date": "2025-01-01", "return_date": "2025-01-15", "days_overdue": 3},
            {"borrower_full_name": "Second", "checkout_date": "2024-01-01"},
        ],
        "statistics": {"late_return_rate": 12.5},
    })
    with patch("bcd_cli.commands.item.get_client", return_value=client):
        result = CliRunner().invoke(item, ["history", "I1", "--limit", "1"])
    assert result.exit_code == 0
    assert "Current Loan" in result.output
    assert "+3j" in result.output
    assert "12.5%" in result.output
    assert "Second" not in result.output


def test_item_history_empty_and_not_found():
    client = MagicMock()
    client.get.return_value = response(200, {"title": "Book", "history": []})
    with patch("bcd_cli.commands.item.get_client", return_value=client):
        result = CliRunner().invoke(item, ["history", "I1"])
    assert result.exit_code == 0
    assert "No history" in result.output

    client.get.return_value = response(404)
    with patch("bcd_cli.commands.item.get_client", return_value=client):
        result = CliRunner().invoke(item, ["history", "missing"])
    assert result.exit_code == 0
    assert "missing" in result.output
