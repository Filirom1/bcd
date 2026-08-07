"""CSV Export functionality for inventory workspace."""

import csv
import logging
from io import StringIO
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from ...models.item import Item
from ...models.system_settings import SystemSettings
from ._serialization import format_inventory_csv_row

logger = logging.getLogger(__name__)


def get_items_csv(db: Session, item_ids: list[str], barcode_prefix: Optional[str] = None) -> str:
    """
    Generate CSV export of items in working table.

    Args:
        db: Database session
        item_ids: List of item barcodes to export
        barcode_prefix: Optional custom prefix to prepend to item IDs. If None,
                        it will be read from SystemSettings (defaulting to ".").

    Returns:
        str: CSV string with 9 columns
    """
    # Fetch items with joined bibliographic_record
    items = (
        db.query(Item)
        .options(joinedload(Item.bibliographic_record))
        .filter(Item.item_id.in_(item_ids))
        .all()
    )

    # Determine prefix
    if barcode_prefix is None:
        settings = db.query(SystemSettings).first()
        if settings and hasattr(settings, "item_barcode_prefix") and isinstance(settings.item_barcode_prefix, str):
            barcode_prefix = settings.item_barcode_prefix
        else:
            barcode_prefix = "."

    # Build CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write header (FR-036 columns)
    writer.writerow([
        'barcode',
        'title',
        'author',
        'call_number',
        'location',
        'status',
        'condition',
        'last_loan_date',
        'last_inventory_date'
    ])

    # Write rows
    for item in items:
        row = format_inventory_csv_row(item, barcode_prefix)
        writer.writerow(row)

    return output.getvalue()
