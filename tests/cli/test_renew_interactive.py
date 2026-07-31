from unittest.mock import MagicMock, patch

from src.bcd_cli.commands.renew import _renew_interactive


def test_renew_interactive_no_current_loans():
    client = MagicMock()
    client.get_borrower_current_loans.return_value = {"current_loans": []}
    with patch("src.bcd_cli.commands.renew.print_borrower_info"), patch("src.bcd_cli.commands.renew.print_current_loans_table"):
        _renew_interactive(client, "B1")
    client.renew_items.assert_not_called()


def test_renew_interactive_selects_items_and_confirms():
    client = MagicMock()
    client.get_borrower_current_loans.return_value = {"current_loans": [{"item_id": "I1"}, {"item_id": "I2"}]}
    client.renew_items.return_value = {"success": True}
    with patch("src.bcd_cli.commands.renew.print_borrower_info"), patch("src.bcd_cli.commands.renew.print_current_loans_table"), patch("src.bcd_cli.commands.renew.read_selection_from_list", return_value=[2]), patch("src.bcd_cli.commands.renew.confirm", return_value=True), patch("src.bcd_cli.commands.renew.print_renewal_summary"):
        _renew_interactive(client, "B1")
    client.renew_items.assert_called_once_with(borrower_id="B1", item_ids=["I2"])


def test_renew_interactive_api_failure_is_reported():
    client = MagicMock()
    client.get_borrower_current_loans.side_effect = RuntimeError("not found")
    _renew_interactive(client, "B1")
    client.renew_items.assert_not_called()
