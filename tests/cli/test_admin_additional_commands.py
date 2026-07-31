from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.admin import admin


def test_list_backups_displays_metadata():
    client = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {"backups": [{"filename": "bcd.db", "size_mb": 2, "created_at": "2026-01-01T12:00:00", "age_days": 2}], "database_info": {"size_mb": 4}}
    client.get.return_value = response
    with patch("bcd_cli.commands.admin.get_client", return_value=client):
        result = CliRunner().invoke(admin, ["list-backups"])
    assert result.exit_code == 0
    assert "bcd.db" in result.output
    assert "4 MB" in result.output


def test_list_backups_empty():
    client = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {"backups": [], "database_info": {}}
    client.get.return_value = response
    with patch("bcd_cli.commands.admin.get_client", return_value=client):
        result = CliRunner().invoke(admin, ["list-backups"])
    assert result.exit_code == 0
    assert "No backups found" in result.output


def test_restore_requires_confirm_before_http_call():
    client = MagicMock()
    with patch("bcd_cli.commands.admin.get_client", return_value=client):
        result = CliRunner().invoke(admin, ["restore", "backup.db"])
    assert result.exit_code == 0
    client.post.assert_not_called()
    assert "--confirm" in result.output


def test_health_success_and_failure():
    client = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {"status": "healthy", "database": "ok"}
    client.get.return_value = response
    with patch("bcd_cli.commands.admin.get_client", return_value=client):
        result = CliRunner().invoke(admin, ["health"])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower()

    client.get.return_value = MagicMock(status_code=503, text="unavailable")
    with patch("bcd_cli.commands.admin.get_client", return_value=client):
        failed = CliRunner().invoke(admin, ["health"])
    assert failed.exit_code == 0
    assert "unavailable" in failed.output
