"""
CLI Tests for Admin Backup Commands

Tests the Click-based CLI backup commands.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import json

from src.bcd_cli.commands.admin import admin, create_backup, list_backups, restore_backup


@pytest.fixture
def runner():
    """Create Click CLI test runner"""
    return CliRunner()


@pytest.fixture
def mock_client():
    """Mock HTTP client"""
    with patch('src.bcd_cli.commands.admin.get_client') as mock:
        yield mock


class TestBackupCommand:
    """Test 'bcd-cli admin backup' command"""

    def test_backup_success(self, runner, mock_client):
        """Test successful backup creation via CLI"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "backup": {
                "filename": "bcd_backup_20260205_120000.db",
                "file_path": "/path/to/backups/bcd_backup_20260205_120000.db",
                "size_mb": 5.42,
                "created_at": "2026-02-05T12:00:00",
                "age_days": 0
            },
            "message": "Backup created successfully"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(admin, ['backup'])

        assert result.exit_code == 0
        assert "Sauvegarde créée avec succès" in result.output or "Backup Created Successfully" in result.output
        assert "bcd_backup_20260205_120000.db" in result.output
        assert "5.42 MB" in result.output

    def test_backup_failure(self, runner, mock_client):
        """Test backup creation failure"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Backup failed: Disk full"

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(admin, ['backup'])

        assert result.exit_code == 1  # Click.Abort
        assert "Backup failed" in result.output

    def test_backup_with_custom_api_url(self, runner, mock_client):
        """Test backup with custom API URL"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "backup": {
                "filename": "backup.db",
                "file_path": "/path/backup.db",
                "size_mb": 1.0,
                "created_at": "2026-02-05T12:00:00",
                "age_days": 0
            }
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(admin, ['backup', '--api-url', 'http://custom:9000'])

        assert result.exit_code == 0
        mock_client.assert_called_with(base_url='http://custom:9000')

    def test_backup_connection_error(self, runner, mock_client):
        """Test backup when API is unreachable"""
        mock_client.side_effect = Exception("Connection refused")

        result = runner.invoke(admin, ['backup'])

        assert result.exit_code == 1
        assert "Error" in result.output or "Erreur" in result.output


class TestListBackupsCommand:
    """Test 'bcd-cli admin list-backups' command"""

    def test_list_backups_success(self, runner, mock_client):
        """Test listing backups successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "count": 2,
            "backups": [
                {
                    "filename": "bcd_backup_20260205_120000.db",
                    "size_mb": 5.42,
                    "created_at": "2026-02-05T12:00:00",
                    "age_days": 0
                },
                {
                    "filename": "bcd_backup_20260204_090000.db",
                    "size_mb": 5.38,
                    "created_at": "2026-02-04T09:00:00",
                    "age_days": 1
                }
            ],
            "database_info": {
                "size_mb": 5.45
            }
        }

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(admin, ['list-backups'])

        assert result.exit_code == 0
        # Check for partial filename matches (table may truncate long names)
        assert "bcd_backup_20260205" in result.output or "20260205_12" in result.output
        assert "bcd_backup_20260204" in result.output or "20260204_09" in result.output
        assert "5.42" in result.output
        assert "5.38" in result.output

    def test_list_backups_empty(self, runner, mock_client):
        """Test listing backups when none exist"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "count": 0,
            "backups": [],
            "database_info": {"size_mb": 5.45}
        }

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(admin, ['list-backups'])

        assert result.exit_code == 0
        assert "Aucune sauvegarde" in result.output or "No backups found" in result.output

    def test_list_backups_api_error(self, runner, mock_client):
        """Test list backups with API error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(admin, ['list-backups'])

        assert result.exit_code == 1
        assert "Failed to list backups" in result.output


class TestRestoreBackupCommand:
    """Test 'bcd-cli admin restore' command"""

    def test_restore_without_confirm_flag(self, runner, mock_client):
        """Test restore fails without --confirm flag"""
        result = runner.invoke(
            admin,
            ['restore', 'backups/backup.db']
        )

        # Should print warning and exit without calling API
        assert result.exit_code == 0
        assert "ATTENTION" in result.output or "WARNING" in result.output
        assert "--confirm" in result.output

        # API should not be called
        mock_client.assert_not_called()

    def test_restore_with_confirm_but_decline_prompt(self, runner, mock_client):
        """Test restore with --confirm but user declines at confirmation prompt"""
        result = runner.invoke(
            admin,
            ['restore', 'backups/backup.db', '--confirm'],
            input='n\n'  # User declines
        )

        assert result.exit_code == 0
        assert "annulée" in result.output or "cancelled" in result.output

    def test_restore_success(self, runner, mock_client):
        """Test successful restore operation"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "restored_from": "backups/bcd_backup_20260205_120000.db",
            "warning": "A safety backup was created in ./backups/pre_restore/",
            "message": "Database restored successfully"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(
            admin,
            ['restore', 'backups/bcd_backup_20260205_120000.db', '--confirm'],
            input='y\n'  # User confirms
        )

        assert result.exit_code == 0
        assert "Restauration réussie" in result.output or "Restore Successful" in result.output
        assert "safety backup" in result.output

    def test_restore_file_not_found(self, runner, mock_client):
        """Test restore with nonexistent backup file"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "detail": "Backup file not found: backups/nonexistent.db"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(
            admin,
            ['restore', 'backups/nonexistent.db', '--confirm'],
            input='y\n'
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_restore_invalid_backup(self, runner, mock_client):
        """Test restore with invalid backup file"""
        mock_response = MagicMock()
        mock_response.status_code = 400  # Fixed: was using == instead of =
        mock_response.json.return_value = {
            "detail": "Backup file is not a valid SQLite database"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(
            admin,
            ['restore', 'backups/invalid.db', '--confirm'],
            input='y\n'
        )

        assert result.exit_code == 1

    def test_restore_with_custom_api_url(self, runner, mock_client):
        """Test restore with custom API URL"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "restored_from": "backups/backup.db",
            "warning": "Safety backup created"
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = runner.invoke(
            admin,
            ['restore', 'backups/backup.db', '--confirm', '--api-url', 'http://custom:9000'],
            input='y\n'
        )

        assert result.exit_code == 0
        mock_client.assert_called_with(base_url='http://custom:9000')


class TestBackupCommandsHelp:
    """Test help messages for backup commands"""

    def test_backup_help(self, runner):
        """Test backup command help message"""
        result = runner.invoke(admin, ['backup', '--help'])

        assert result.exit_code == 0
        assert "Create a database backup" in result.output
        assert "--output" in result.output
        assert "--api-url" in result.output

    def test_list_backups_help(self, runner):
        """Test list-backups command help message"""
        result = runner.invoke(admin, ['list-backups', '--help'])

        assert result.exit_code == 0
        assert "List all available database backups" in result.output

    def test_restore_help(self, runner):
        """Test restore command help message"""
        result = runner.invoke(admin, ['restore', '--help'])

        assert result.exit_code == 0
        assert "Restore database from a backup file" in result.output
        assert "DANGEROUS OPERATION" in result.output
        assert "--confirm" in result.output


class TestBackupCommandsIntegration:
    """Integration tests combining multiple backup commands"""

    def test_backup_list_restore_workflow(self, runner, mock_client):
        """Test complete backup workflow: create, list, restore"""
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        # Step 1: Create backup
        backup_response = MagicMock()
        backup_response.status_code = 200
        backup_response.json.return_value = {
            "success": True,
            "backup": {
                "filename": "test_backup.db",
                "file_path": "/path/test_backup.db",
                "size_mb": 1.0,
                "created_at": "2026-02-05T12:00:00",
                "age_days": 0
            }
        }
        mock_client_instance.post.return_value = backup_response

        backup_result = runner.invoke(admin, ['backup'])
        assert backup_result.exit_code == 0

        # Step 2: List backups
        list_response = MagicMock()
        list_response.status_code = 200
        list_response.json.return_value = {
            "success": True,
            "count": 1,
            "backups": [{
                "filename": "test_backup.db",
                "size_mb": 1.0,
                "created_at": "2026-02-05T12:00:00",
                "age_days": 0
            }],
            "database_info": {"size_mb": 1.0}
        }
        mock_client_instance.get.return_value = list_response

        list_result = runner.invoke(admin, ['list-backups'])
        assert list_result.exit_code == 0
        assert "test_backup.db" in list_result.output

        # Step 3: Restore backup
        restore_response = MagicMock()
        restore_response.status_code = 200
        restore_response.json.return_value = {
            "success": True,
            "restored_from": "/path/test_backup.db",
            "warning": "Safety backup created"
        }
        mock_client_instance.post.return_value = restore_response

        restore_result = runner.invoke(
            admin,
            ['restore', '/path/test_backup.db', '--confirm'],
            input='y\n'
        )
        assert restore_result.exit_code == 0

    def test_backup_commands_with_environment_variable(self, runner, mock_client):
        """Test backup commands using BCD_API_URL environment variable"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "backup": {
                "filename": "backup.db",
                "file_path": "/path/backup.db",
                "size_mb": 1.0,
                "created_at": "2026-02-05T12:00:00",
                "age_days": 0
            }
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        # Set environment variable
        result = runner.invoke(
            admin,
            ['backup'],
            env={'BCD_API_URL': 'http://env-api:8000'}
        )

        assert result.exit_code == 0
        # Should use env var URL
        mock_client.assert_called_with(base_url='http://env-api:8000')
