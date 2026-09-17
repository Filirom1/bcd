"""Tests for application-settings CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.bcd_cli.commands.settings import SHELF_LOCATIONS, settings


def test_create_locations_dry_run_does_not_call_api():
    with patch("src.bcd_cli.commands.settings.get_client") as get_client:
        result = CliRunner().invoke(settings, ["create-locations", "--dry-run"])

    assert result.exit_code == 0, result.output
    get_client.assert_not_called()
    assert "Documentaires" in result.output
    assert "Périodique" in result.output


def test_create_locations_sends_locations_to_settings_api():
    client = MagicMock()
    response = MagicMock(status_code=200)
    client.put.return_value = response

    with patch("src.bcd_cli.commands.settings.get_client", return_value=client):
        result = CliRunner().invoke(settings, ["create-locations", "--yes"])

    assert result.exit_code == 0, result.output
    client.put.assert_called_once_with(
        "/api/v1/admin/settings",
        json={"updates": {"catalog_shelf_locations": SHELF_LOCATIONS}},
    )
