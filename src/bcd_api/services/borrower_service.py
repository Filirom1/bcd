"""Backward-compatible facade for borrower services."""

from .borrower.commands import (
    block_borrower,
    bulk_change_class,
    bulk_change_role,
    bulk_delete_borrowers,
    create_borrower,
    unblock_borrower,
    update_borrower,
)
from .borrower.export import export_borrowers_to_csv
from .borrower.import_ import import_borrowers_from_csv
from .borrower.queries import (
    enrich_borrower,
    enrich_borrowers,
    get_borrower_by_id,
    get_borrower_details,
    get_detailed_borrower,
    get_next_available_id,
    list_borrowers,
)

__all__ = [
    "block_borrower",
    "bulk_change_class",
    "bulk_change_role",
    "bulk_delete_borrowers",
    "create_borrower",
    "unblock_borrower",
    "update_borrower",
    "export_borrowers_to_csv",
    "import_borrowers_from_csv",
    "enrich_borrower",
    "enrich_borrowers",
    "get_borrower_by_id",
    "get_borrower_details",
    "get_detailed_borrower",
    "get_next_available_id",
    "list_borrowers",
]
