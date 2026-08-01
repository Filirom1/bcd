"""Catalog Service Package Façade

Main entry point for bibliographic records and items management.
Re-exports implementations from records and items submodules.
"""

from ..bnf_service import search_by_isbn
from ..google_books_service import search_by_isbn as google_search_by_isbn
from ..sudoc_service import (
    search_by_isbn as sudoc_search_by_isbn,
    search_by_issn as sudoc_search_by_issn,
)

from .records import (
    _download_cover,
    _ean13_to_issn,
    create_bibliographic_record,
    lookup_isbn,
    get_bibliographic_record,
    search_bibliographic_records,
    bulk_edit_records,
    bulk_delete_records,
    update_record,
    get_shelf_locations,
    enrich_bibliographic_records_with_availability,
)

from .items import (
    create_item,
    get_item,
    get_items_for_bibliographic_record,
    update_item,
    delete_item,
    get_available_item_ids,
)

__all__ = [
    "search_by_isbn",
    "google_search_by_isbn",
    "sudoc_search_by_isbn",
    "sudoc_search_by_issn",
    "_download_cover",
    "_ean13_to_issn",
    "create_bibliographic_record",
    "lookup_isbn",
    "get_bibliographic_record",
    "search_bibliographic_records",
    "bulk_edit_records",
    "bulk_delete_records",
    "update_record",
    "get_shelf_locations",
    "enrich_bibliographic_records_with_availability",
    "create_item",
    "get_item",
    "get_items_for_bibliographic_record",
    "update_item",
    "delete_item",
    "get_available_item_ids",
]
