from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.borrower import borrower


def resp(code, data=None):
    r = MagicMock()
    r.status_code = code
    r.json.return_value = data or {}
    r.text = "error"
    return r


def test_add_borrower_sends_optional_fields():
    client = MagicMock()
    client.post.return_value = resp(201, {"borrower_id": "B1", "full_name": "Alice Doe", "barcode": "BC1", "role": "student", "class_id": 2})
    with patch("bcd_cli.commands.borrower.get_client", return_value=client):
        result = CliRunner().invoke(borrower, ["add", "--borrower-id", "B1", "--first-name", "Alice", "--last-name", "Doe", "--class-id", "2", "--email", "a@example.org", "--notes", "note"])
    assert result.exit_code == 0
    payload = client.post.call_args.kwargs["json"]
    assert payload["class_id"] == 2
    assert payload["email"] == "a@example.org"
    assert "Borrower created successfully" in result.output


def test_list_borrowers_supports_paginated_response_and_filters():
    client = MagicMock()
    client.get.return_value = resp(200, {"items": [{"borrower_id": "B1", "full_name": "Alice", "role": "student", "class_id": 3, "active": True}], "total": 1})
    with patch("bcd_cli.commands.borrower.get_client", return_value=client):
        result = CliRunner().invoke(borrower, ["list", "--role", "student", "--class-id", "3", "--active", "--limit", "5"])
    assert result.exit_code == 0
    params = client.get.call_args.kwargs["params"]
    assert params == {"limit": 5, "role": "student", "class_id": 3, "active": True}
    assert "Alice" in result.output


def test_list_borrowers_empty():
    client = MagicMock()
    client.get.return_value = resp(200, [])
    with patch("bcd_cli.commands.borrower.get_client", return_value=client):
        result = CliRunner().invoke(borrower, ["list"])
    assert result.exit_code == 0
    assert "No borrowers found" in result.output


def test_show_borrower_and_block_unblock():
    client = MagicMock()
    client.get.return_value = resp(200, {"borrower_id": "B1", "full_name": "Alice", "role": "student", "barcode": "BC1", "active": False, "class_id": 2, "blocked_reason": "late", "current_loans_count": 1, "total_checkouts": 3, "overdue_count": 1})
    with patch("bcd_cli.commands.borrower.get_client", return_value=client):
        result = CliRunner().invoke(borrower, ["show", "B1"])
    assert result.exit_code == 0
    assert "Blocked Reason" in result.output
    assert "Alice" in result.output

    client.post.return_value = resp(200)
    with patch("bcd_cli.commands.borrower.get_client", return_value=client):
        blocked = CliRunner().invoke(borrower, ["block", "B1", "--reason", "late"])
        unblocked = CliRunner().invoke(borrower, ["unblock", "B1"])
    assert blocked.exit_code == 0 and "blocked" in blocked.output
    assert unblocked.exit_code == 0 and "unblocked" in unblocked.output
