"""Serialization helpers for inventory items and records."""

import json
from datetime import datetime, timezone
from ...models.item import Item


def parse_authors(value: str | None) -> list[str]:
    """Parse authors JSON string to a list of strings."""
    if not value:
        return []
    try:
        authors_list = json.loads(value)
        if isinstance(authors_list, list):
            return [str(a) for a in authors_list]
        return []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def first_author(value: str | None) -> str:
    """Get the first author from JSON string, or empty string."""
    authors = parse_authors(value)
    return authors[0] if authors else ""


def format_inventory_csv_row(item: Item, prefix: str) -> list[str]:
    """Format an item as a CSV row list."""
    record = item.bibliographic_record
    author_str = first_author(record.authors) if record else ""
    title_str = record.title if record else ""

    last_loan_date = item.last_borrowed_at.date().isoformat() if item.last_borrowed_at else ""
    last_inventory_date = item.last_inventoried_at.date().isoformat() if item.last_inventoried_at else ""

    return [
        f"{prefix}{item.item_id}",
        title_str,
        author_str,
        item.call_number or "",
        item.shelf_location or "",
        item.status,
        item.condition,
        last_loan_date,
        last_inventory_date
    ]
