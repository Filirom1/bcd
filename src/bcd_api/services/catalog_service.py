"""Backward-compatible facade for catalog services."""

from src.bcd_api.utils.catalog_input import _ean13_to_issn

from .catalog.commands import (
    bulk_delete_records,
    bulk_edit_records,
    create_bibliographic_record,
    create_item,
    delete_item,
    merge_bibliographic_records,
    update_item,
    update_record,
)
from .catalog.export import export_catalog_to_dublin_core_csv
from .catalog.import_dc import import_dublin_core_csv
from .catalog.lookup import (
    _download_cover,
    classify_catalog_input,
    lookup_isbn,
    lookup_notice_source,
    search_local_notices,
    source_configuration,
    test_external_source,
)
from .catalog.projections import (
    availability_by_record as enrich_bibliographic_records_with_availability,
)
from .catalog.queries import (
    get_available_item_ids,
    get_bibliographic_record,
    get_bibliographic_record_with_counts,
    get_item,
    get_items_for_bibliographic_record,
    get_shelf_locations,
    search_bibliographic_records,
)

# External lookup backward-compatibility re-exports
from .external.bnf import search_by_isbn
from .external.google_books import search_by_isbn as google_search_by_isbn
from .external.sudoc import (
    search_by_isbn as sudoc_search_by_isbn,
)
from .external.sudoc import (
    search_by_issn as sudoc_search_by_issn,
)

__all__ = [
    "create_bibliographic_record",
    "update_record",
    "bulk_edit_records",
    "bulk_delete_records",
    "merge_bibliographic_records",
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
    "classify_catalog_input",
    "lookup_notice_source",
    "search_local_notices",
    "source_configuration",
    "test_external_source",
    "enrich_bibliographic_records_with_availability",
    "_ean13_to_issn",
    "import_dublin_core_csv",
    "export_catalog_to_dublin_core_csv",
    "search_by_isbn",
    "google_search_by_isbn",
    "sudoc_search_by_isbn",
    "sudoc_search_by_issn",
]
