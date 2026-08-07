"""Serialization helpers for inventory items and records."""

from datetime import datetime, timezone
from ...models.item import Item
from ...utils.serialization import parse_json_list, first_item


def parse_authors(value: str | None) -> list[str]:
    """Parse authors JSON string to a list of strings."""
    return parse_json_list(value)


def first_author(value: str | None) -> str:
    """Get the first author from JSON string, or empty string."""
    return first_item(value)


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
