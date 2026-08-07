"""Backward-compatible facade for catalog services."""

from .catalog.commands import (
    create_bibliographic_record,
    update_record,
    bulk_edit_records,
    bulk_delete_records,
    create_item,
    update_item,
    delete_item,
)
from .catalog.queries import (
    get_bibliographic_record,
    get_bibliographic_record_with_counts,
    search_bibliographic_records,
    get_item,
    get_items_for_bibliographic_record,
    get_available_item_ids,
    get_shelf_locations,
)
from .catalog.lookup import lookup_isbn, _download_cover
from .catalog.projections import availability_by_record as enrich_bibliographic_records_with_availability
from .catalog._validation import _ean13_to_issn
from .catalog.import_dc import import_dublin_core_csv
from .catalog.export import export_catalog_to_dublin_core_csv

# External lookup backward-compatibility re-exports
from .external.bnf import search_by_isbn
from .external.google_books import search_by_isbn as google_search_by_isbn
from .external.sudoc import (
    search_by_isbn as sudoc_search_by_isbn,
    search_by_issn as sudoc_search_by_issn,
)

__all__ = [
    "create_bibliographic_record",
    "update_record",
    "bulk_edit_records",
    "bulk_delete_records",
    "create_item",
    "update_item",
    "delete_item",
    "get_bibliographic_record",
    "get_bibliographic_record_with_counts",
    "search_bibliographic_records",
    "get_item",
    "get_items_for_bibliographic_record",
    "get_available_item_ids",
    "get_shelf_locations",
    "lookup_isbn",
    "_download_cover",
    "enrich_bibliographic_records_with_availability",
    "_ean13_to_issn",
    "import_dublin_core_csv",
    "export_catalog_to_dublin_core_csv",
    "search_by_isbn",
    "google_search_by_isbn",
    "sudoc_search_by_isbn",
    "sudoc_search_by_issn",
]
