"""Backward-compatible facade for the CSV transform service."""

from .catalog.transform import (
    transform_bcd_to_dublin_core,
)

__all__ = [
    "transform_bcd_to_dublin_core",
]
