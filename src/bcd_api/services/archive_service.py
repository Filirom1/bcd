"""Backward-compatible facade for the archive service."""

from .admin.archive import (
    archive_old_transactions,
    get_archive_stats,
    get_archived_transactions,
)

__all__ = [
    "archive_old_transactions",
    "get_archived_transactions",
    "get_archive_stats",
]
