"""Backward-compatible facade for the holds service."""

from .holds.commands import (
    auto_fill_holds_on_return,
    auto_fill_holds_on_return_in_transaction,
    cancel_hold,
    cancel_hold_in_transaction,
    cancel_holds_for_records_in_transaction,
    create_hold,
    create_hold_in_transaction,
    expire_ready_holds,
    expire_ready_holds_in_transaction,
    fulfill_hold,
    fulfill_hold_in_transaction,
    mark_hold_ready,
    mark_hold_ready_in_transaction,
)
from .holds.queries import (
    get_hold,
    get_holds_for_bibliographic_record,
    get_holds_for_borrower,
    get_ready_holds,
)

__all__ = [
    "create_hold",
    "create_hold_in_transaction",
    "expire_ready_holds",
    "expire_ready_holds_in_transaction",
    "mark_hold_ready",
    "mark_hold_ready_in_transaction",
    "fulfill_hold",
    "fulfill_hold_in_transaction",
    "cancel_hold",
    "cancel_hold_in_transaction",
    "cancel_holds_for_records_in_transaction",
    "auto_fill_holds_on_return",
    "auto_fill_holds_on_return_in_transaction",
    "get_hold",
    "get_holds_for_borrower",
    "get_holds_for_bibliographic_record",
    "get_ready_holds",
]
