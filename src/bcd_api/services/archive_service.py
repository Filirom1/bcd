"""Backward-compatible facade for the archive service."""

from .admin.archive import (
    archive_old_transactions,
    get_archived_transactions,
    get_archive_stats,
)

__all__ = [
    "archive_old_transactions",
    "get_archived_transactions",
    "get_archive_stats",
]
