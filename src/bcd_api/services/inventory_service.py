"""Backward-compatible facade for inventory services."""

from .inventory._search import escape_like_pattern as _escape_like_pattern
from .inventory.commands import (
    bulk_mark_inventoried,
    bulk_update_items,
    delete_items_bulk,
    delete_orphan_records,
    mark_item_inventoried,
)
from .inventory.export import get_items_csv
from .inventory.queries import get_orphan_records, search_items

__all__ = [
    "_escape_like_pattern",
    "mark_item_inventoried",
    "bulk_mark_inventoried",
    "search_items",
    "bulk_update_items",
    "delete_items_bulk",
    "get_items_csv",
    "get_orphan_records",
    "delete_orphan_records",
]
