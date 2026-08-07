"""Report Service Package Façade

Main entry point for generating library reports and statistics.
Re-exports implementations from internal report submodules.
"""

from .loans import (
    _deserialize_authors,
    get_overdue_items,
    get_overdue_summary_by_class,
    get_holds_report,
    get_active_loans,
)

from .catalog import (
    get_never_borrowed_items,
    get_most_borrowed_titles,
)

from .stats import (
    get_collection_stats,
    get_circulation_statistics,
    get_borrower_statistics,
)

__all__ = [
    "_deserialize_authors",
    "get_overdue_items",
    "get_overdue_summary_by_class",
    "get_holds_report",
    "get_active_loans",
    "get_never_borrowed_items",
    "get_most_borrowed_titles",
    "get_collection_stats",
    "get_circulation_statistics",
    "get_borrower_statistics",
]
