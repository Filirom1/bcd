"""Shared serialization and parsing utilities for JSON lists, authors, and metadata."""

import json
from typing import Any, List, Optional


def parse_json_list(value: Any) -> List[str]:
    """Parse a JSON-serialized list of strings to a list of Python strings.
    If the value is already a list, it returns it directly (casting elements to string).
    If the value is a single string but not a JSON list, it parses it if it's JSON,
    or falls back to a single-element list.

    Args:
        value: JSON string, list of strings, or None.

    Returns:
        List of strings, or empty list if empty or invalid.
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        try:
            res = json.loads(value)
            if isinstance(res, list):
                return [str(item) for item in res if item is not None]
            return [str(res)] if res else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    return []


def deserialize_json_list(value: Any, join_char: str = ", ") -> Optional[str]:
    """Deserialize a JSON list and return its items joined by a character.

    Args:
        value: JSON string, list of strings, or None.
        join_char: Character/string used to join the items (default is ", ").

    Returns:
        String of joined items, or None if the input is invalid/empty.
    """
    items = parse_json_list(value)
    return join_char.join(items) if items else None


def first_item(value: Any) -> str:
    """Get the first item from a JSON list of strings, or empty string.

    Args:
        value: JSON string, list of strings, or None.

    Returns:
        First string item, or empty string if empty or invalid.
    """
    items = parse_json_list(value)
    return items[0] if items else ""
