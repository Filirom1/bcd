"""Backward-compatible facade for the export service."""

from .catalog.export import (
    MAX_EXPORT_ROWS,
    ExportService,
)

__all__ = [
    "ExportService",
    "MAX_EXPORT_ROWS",
]
