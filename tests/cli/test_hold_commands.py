from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.hold import hold


def resp(code, data=None, text="error", content_type="application/json"):
    r = MagicMock()
    r.status_code = code
    r.json.return_value = data if data is not None else {}
    r.text = text
    r.headers = {"content-type": content_type}
    return r


def test_add_hold_success_and_queue_estimate():
    client = MagicMock()
    client.get.side_effect = [
        resp(200, {"id": 7, "borrower_id": "B7", "full_name": "Alice", "class_name": "CM1"}),
        resp(200, {"title": "Book", "authors": ["Author"], "total_items": 2}),
        resp(200, [{"status": "available"}, {"status": "on_loan"}]),
    ]
    client.post.return_value = resp(201, {"id": 8, "queue_position": 2})
    with patch("bcd_cli.commands.hold.get_client", return_value=client):
        result = CliRunner().invoke(hold, ["add", "B7", "4", "--notes", "urgent"], input="y\n")
    assert result.exit_code == 0
    assert "Hold created" in result.output
    assert "14 jours" in result.output
    assert client.post.call_args.kwargs["json"]["notes"] == "urgent"


def test_add_hold_requires_both_ids():
    result = CliRunner().invoke(hold, ["add"])
    assert result.exit_code != 0
    assert "required" in result.output


def test_list_holds_displays_empty_and_ready_holds():
    client = MagicMock()
    client.get.side_effect = [
        resp(200, {"id": 7, "full_name": "Alice"}),
        resp(200, [{"id": 8, "title": "Book", "queue_position": 1, "status": "waiting", "hold_date": "2026-01-01"}]),
    ]
    with patch("bcd_cli.commands.hold.get_client", return_value=client):
        result = CliRunner().invoke(hold, ["list", "B7"])
    assert result.exit_code == 0
    assert "Book" in result.output
    assert "En attente" in result.output


def test_cancel_hold_confirmed():
    client = MagicMock()
    client.get.return_value = resp(200, {"borrower_name": "Alice", "title": "Book", "status": "waiting"})
    client.delete.return_value = resp(204)
    with patch("bcd_cli.commands.hold.get_client", return_value=client):
        result = CliRunner().invoke(hold, ["cancel", "8"], input="y\n")
    assert result.exit_code == 0
    assert "Hold cancelled" in result.output


def test_ready_holds_empty():
    client = MagicMock()
    client.get.return_value = resp(200, [])
    with patch("bcd_cli.commands.hold.get_client", return_value=client):
        result = CliRunner().invoke(hold, ["ready"])
    assert result.exit_code == 0
    assert "No holds ready" in result.output
