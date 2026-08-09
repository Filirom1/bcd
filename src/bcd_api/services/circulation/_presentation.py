"""Presentation and Formatting Helpers for Circulation.

Centralizes visual/display formatting logic for API responses.
"""

from typing import Optional


def display_title(title: str, shelf_location: Optional[str] = None) -> str:
    """Format a display title appending shelf location.

    shelf_location → appended after title (if present)
    No extras → "Title"
    """
    parts = [title]
    if shelf_location:
        parts.append(shelf_location)
    return " \u00b7 ".join(parts)
