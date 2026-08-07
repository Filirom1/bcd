"""Backward-compatible facade for the settings service."""

from .admin.settings import (
    DEFAULT_CALL_NUMBER_RULES,
    DEFAULT_SHELF_LOCATIONS,
    get_settings,
    initialize_default_settings,
    reset_to_defaults,
    update_settings,
)

__all__ = [
    "DEFAULT_CALL_NUMBER_RULES",
    "DEFAULT_SHELF_LOCATIONS",
    "get_settings",
    "initialize_default_settings",
    "reset_to_defaults",
    "update_settings",
]
