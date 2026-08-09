"""Borrower Export Service

Service for exporting borrowers to BCD CSV format.
"""

import csv
import logging
from io import StringIO
from typing import Tuple

from sqlalchemy.orm import Session, joinedload

from src.bcd_api.core.exceptions import ExportFailedException, ExportTooLargeException
from src.bcd_api.models.borrower import Borrower
from src.shared.constants import BCD_BORROWER_COLUMNS, MAX_BORROWER_ROWS

logger = logging.getLogger(__name__)


def export_borrowers_to_csv(db: Session) -> Tuple[str, int]:
    """Export all borrowers to BCD borrower CSV format.

    Strategy:
    1. Query all borrowers with class information (use joinedload)
    2. Export one CSV row per borrower
    3. Stream CSV generation to avoid building entire file in memory

    Returns:
        Tuple of (csv_content: str, borrower_count: int)

    Raises:
        ExportTooLargeException: If export exceeds MAX_BORROWER_ROWS
        ExportFailedException: If export operation fails
    """
    try:
        # Query all borrowers with class info
        borrowers = (
            db.query(Borrower)
            .options(joinedload(Borrower.class_))
            .all()
        )

        # Count total borrowers for validation
        total_borrowers = len(borrowers)

        if total_borrowers > MAX_BORROWER_ROWS:
            raise ExportTooLargeException(
                record_count=total_borrowers,
                limit=MAX_BORROWER_ROWS
            )

        # Generate CSV
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=BCD_BORROWER_COLUMNS,
            quoting=csv.QUOTE_MINIMAL
        )

        writer.writeheader()

        for borrower in borrowers:
            row = _borrower_to_dict(borrower)
            writer.writerow(row)

        csv_content = output.getvalue()
        logger.info(f"Borrower export complete: {total_borrowers} borrowers")

        return csv_content, total_borrowers

    except ExportTooLargeException:
        raise
    except Exception as e:
        logger.exception("Borrower export failed")
        raise ExportFailedException(
            reason=str(e),
            details={"error_type": type(e).__name__}
        ) from e


def _borrower_to_dict(borrower: Borrower) -> dict:
    """Convert Borrower to BCD borrower CSV row.

    Args:
        borrower: Borrower instance

    Returns:
        Dictionary mapping BCD borrower columns to values
    """
    # Get class name from relationship (if exists)
    class_name = ""
    if borrower.class_:
        class_name = borrower.class_.name

    return {
        'borrower_id': borrower.borrower_id,
        'first_name': borrower.first_name,
        'last_name': borrower.last_name,
        'role': borrower.role,
        'class': class_name,
        'barcode': borrower.barcode,
        'active': str(borrower.active).lower(),  # "true" or "false"
        'blocked': str(bool(borrower.blocked_reason)).lower(),  # "true" if blocked_reason exists
        'blocked_reason': borrower.blocked_reason or '',
    }
