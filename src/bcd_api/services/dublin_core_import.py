"""Backward-compatible facade for the Dublin Core import service."""

from .catalog.import_dc import (
    import_dublin_core_csv,
)

__all__ = [
    "import_dublin_core_csv",
]
