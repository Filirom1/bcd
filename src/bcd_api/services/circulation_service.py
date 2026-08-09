"""Backward-compatible facade for the circulation service."""

from .circulation._presentation import display_title as _display_title  # noqa: F401
from .circulation.commands import (  # noqa: F401
    checkout_items,
    renew_items,
    return_items,
)
from .circulation.queries import (  # noqa: F401
    get_borrower_circulation_history,
    get_borrower_current_loans,
    get_item_circulation_history,
)

__all__ = [
    "checkout_items",
    "return_items",
    "renew_items",
    "get_borrower_current_loans",
    "get_item_circulation_history",
    "get_borrower_circulation_history",
]
