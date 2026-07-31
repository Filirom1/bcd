from unittest.mock import MagicMock, patch

from bcd_cli.commands.checkout import _checkout_interactive
from bcd_cli.commands.return_cmd import _return_interactive


def test_interactive_checkout_empty_borrower_does_not_call_api():
    client = MagicMock()
    with patch("bcd_cli.commands.checkout.read_barcode_input", return_value=""):
        _checkout_interactive(client)
    client.checkout.assert_not_called()
    client.get_borrower_current_loans.assert_not_called()


def test_interactive_checkout_blocked_borrower_stops():
    client = MagicMock()
    client.get_borrower_current_loans.return_value = {"active": False, "blocked_reason": "late"}
    with patch("bcd_cli.commands.checkout.read_barcode_input", return_value="B1"):
        _checkout_interactive(client)
    client.checkout.assert_not_called()


def test_interactive_return_without_scans_does_not_call_api():
    client = MagicMock()
    with patch("bcd_cli.commands.return_cmd.read_barcode_input", return_value=""):
        _return_interactive(client)
    client.return_items.assert_not_called()
