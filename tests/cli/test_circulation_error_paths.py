from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.checkout import checkout
from bcd_cli.commands.return_cmd import return_items
from bcd_cli.commands.renew import renew


def test_checkout_api_error_is_reported():
    client = MagicMock()
    client.checkout.side_effect = RuntimeError("borrower blocked")
    with patch("bcd_cli.commands.checkout.get_client", return_value=client):
        result = CliRunner().invoke(checkout, ["B1", "I1"])
    assert result.exit_code != 0
    assert "Checkout failed" in result.output


def test_return_api_error_is_reported():
    client = MagicMock()
    client.return_items.side_effect = RuntimeError("item not on loan")
    with patch("bcd_cli.commands.return_cmd.get_client", return_value=client):
        result = CliRunner().invoke(return_items, ["I1"])
    assert result.exit_code != 0
    assert "Return failed" in result.output


def test_renew_api_error_is_reported():
    client = MagicMock()
    client.renew_items.side_effect = RuntimeError("not eligible")
    with patch("bcd_cli.commands.renew.get_client", return_value=client):
        result = CliRunner().invoke(renew, ["B1", "--all"])
    assert result.exit_code != 0
    assert "Renewal failed" in result.output
