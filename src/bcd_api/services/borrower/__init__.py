"""Borrower Service Package Façade

Main entry point for borrower management.
Re-exports implementations from internal borrower submodules.
"""

from .commands import (
    block_borrower,
    bulk_change_class,
    bulk_change_role,
    bulk_delete_borrowers,
    create_borrower,
    unblock_borrower,
    update_borrower,
)
from .export import export_borrowers_to_csv
from .import_ import import_borrowers_from_csv
from .queries import (
    enrich_borrower,
    enrich_borrowers,
    get_borrower_by_id,
    get_borrower_details,
    get_detailed_borrower,
    get_next_available_id,
    list_borrowers,
)

__all__ = [
    "create_borrower",
    "update_borrower",
    "unblock_borrower",
    "block_borrower",
    "bulk_change_class",
    "bulk_change_role",
    "bulk_delete_borrowers",
    "get_borrower_by_id",
    "get_borrower_details",
    "get_detailed_borrower",
    "get_next_available_id",
    "list_borrowers",
    "get_borrower_details",
    "enrich_borrower",
    "enrich_borrowers",
    "import_borrowers_from_csv",
    "export_borrowers_to_csv",
]
