"""Validation and normalization helpers for inventory."""

from typing import Any, Optional


def normalize_field_value(value: Any) -> Optional[Any]:
    """Normalize empty string to None, otherwise keep the value."""
    if value == "":
        return None
    return value
