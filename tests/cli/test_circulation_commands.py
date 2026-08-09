from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.checkout import checkout
from bcd_cli.commands.return_cmd import return_items
from bcd_cli.commands.renew import renew


def test_checkout_direct_calls_client():
    client = MagicMock()
    client.checkout.return_value = {"success": True, "transactions": []}
    with patch("bcd_cli.commands.checkout.get_client", return_value=client):
        result = CliRunner().invoke(checkout, ["B1", "I1", "I2"])
    assert result.exit_code == 0
    client.checkout.assert_called_once_with(borrower_id="B1", item_ids=["I1", "I2"], checked_out_by="cli")


def test_checkout_without_items_is_rejected():
    with patch("bcd_cli.commands.checkout.get_client", return_value=MagicMock()):
        result = CliRunner().invoke(checkout, ["B1"])
    assert result.exit_code != 0
    assert "At least one item" in result.output


def test_return_direct_calls_client():
    client = MagicMock()
    client.return_items.return_value = {"success": True, "transactions": []}
    with patch("bcd_cli.commands.return_cmd.get_client", return_value=client):
        result = CliRunner().invoke(return_items, ["I1", "I2"])
    assert result.exit_code == 0
    client.return_items.assert_called_once_with(item_ids=["I1", "I2"], returned_by="cli")


def test_renew_all_calls_client_without_item_ids():
    client = MagicMock()
    client.renew_items.return_value = {"success": True, "transactions": []}
    with patch("bcd_cli.commands.renew.get_client", return_value=client):
        result = CliRunner().invoke(renew, ["B1", "--all"])
    assert result.exit_code == 0
    client.renew_items.assert_called_once_with(borrower_id="B1", item_ids=None)
