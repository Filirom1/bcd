"""Backward-compatible facade for the export service."""

from .catalog.export import (
    ExportService,
    MAX_EXPORT_ROWS,
)

__all__ = [
    "ExportService",
    "MAX_EXPORT_ROWS",
]
