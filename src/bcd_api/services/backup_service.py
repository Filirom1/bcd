"""Backward-compatible facade for the backup service."""

from .admin.backup import (
    BackupMetadata,
    create_backup,
    restore_backup,
    list_backups,
    cleanup_old_backups,
    verify_backup,
    get_database_size,
    get_database_path,
    settings,
)

__all__ = [
    "BackupMetadata",
    "create_backup",
    "restore_backup",
    "list_backups",
    "cleanup_old_backups",
    "verify_backup",
    "get_database_size",
    "get_database_path",
    "settings",
]
