"""Export Service

Service for exporting catalog records to Dublin Core CSV format.
"""

import csv
import json
import logging
from io import StringIO
from typing import List, Tuple

from sqlalchemy.orm import Session, joinedload

from src.bcd_api.core.exceptions import ExportTooLargeException, ExportFailedException
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.services.import_service import DublinCoreColumns
from src.shared.constants import BCD_BORROWER_COLUMNS, MAX_BORROWER_ROWS

logger = logging.getLogger(__name__)

# Export row limit to prevent memory issues and timeouts
MAX_EXPORT_ROWS = 10000


class ExportService:
    """Service for exporting catalog to CSV."""

    def __init__(self, db: Session):
        """Initialize export service.

        Args:
            db: Database session
        """
        self.db = db

    def export_catalog_to_csv(self) -> Tuple[str, int, int]:
        """Export entire catalog to Dublin Core CSV format.

        Strategy:
        1. Query all bibliographic records with items (use joinedload to avoid N+1)
        2. For each record with items, create one CSV row per item
        3. For records without items, create one row with empty item fields
        4. Stream CSV generation to avoid building entire file in memory

        Returns:
            Tuple of (csv_content: str, record_count: int, item_count: int)

        Raises:
            ExportTooLargeException: If export exceeds MAX_EXPORT_ROWS
            ExportFailedException: If export operation fails
        """
        try:
            # Query all bibliographic records with items
            records = (
                self.db.query(BiblographicRecord)
                .options(joinedload(BiblographicRecord.items))
                .all()
            )

            # Count total rows (items) for validation
            total_items = sum(len(record.items) if record.items else 1 for record in records)

            if total_items > MAX_EXPORT_ROWS:
                raise ExportTooLargeException(record_count=total_items, limit=MAX_EXPORT_ROWS)

            # Generate CSV
            output = StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=self._get_csv_fieldnames(),
                quoting=csv.QUOTE_MINIMAL
            )

            writer.writeheader()

            record_count = 0
            item_count = 0

            for record in records:
                if record.items:
                    # Create one row per item
                    for item in record.items:
                        row = self._record_to_dict(record, item)
                        writer.writerow(row)
                        item_count += 1
                else:
                    # Create one row with empty item fields
                    row = self._record_to_dict(record, None)
                    writer.writerow(row)
                    item_count += 1

                record_count += 1

            csv_content = output.getvalue()
            logger.info(f"Export complete: {record_count} records, {item_count} rows")

            return csv_content, record_count, item_count

        except ExportTooLargeException:
            raise
        except Exception as e:
            logger.exception("Export failed")
            raise ExportFailedException(
                reason=str(e),
                details={"error_type": type(e).__name__}
            )

    def _get_csv_fieldnames(self) -> List[str]:
        """Get CSV column names in Dublin Core format.

        Returns:
            List of column names
        """
        return [
            # Required
            DublinCoreColumns.TITLE,
            DublinCoreColumns.IDENTIFIER,

            # Recommended
            DublinCoreColumns.CREATOR,
            DublinCoreColumns.SUBJECT,
            DublinCoreColumns.DESCRIPTION,
            DublinCoreColumns.PUBLISHER,
            DublinCoreColumns.CONTRIBUTOR,
            DublinCoreColumns.DATE,
            DublinCoreColumns.TYPE,
            DublinCoreColumns.FORMAT,
            DublinCoreColumns.LANGUAGE,

            # Optional
            DublinCoreColumns.SOURCE,
            DublinCoreColumns.RELATION,
            DublinCoreColumns.COVERAGE,
            DublinCoreColumns.RIGHTS,

            # Extensions (item fields)
            DublinCoreColumns.ITEM_ID,
            DublinCoreColumns.CALL_NUMBER,
            DublinCoreColumns.ACQUISITION_DATE,
            DublinCoreColumns.FUNDING_SOURCE,
        ]

    def _record_to_dict(self, record: BiblographicRecord, item: Item = None) -> dict:
        """Convert BiblographicRecord (and optional Item) to Dublin Core CSV row.

        Args:
            record: BiblographicRecord instance
            item: Optional Item instance

        Returns:
            Dictionary mapping Dublin Core columns to values
        """
        return {
            # Required
            DublinCoreColumns.TITLE: record.title or "",
            DublinCoreColumns.IDENTIFIER: self._format_isbn(record.isbn),

            # Recommended
            DublinCoreColumns.CREATOR: self._format_authors(record.authors),
            DublinCoreColumns.SUBJECT: self._format_keywords(record.keywords),
            DublinCoreColumns.DESCRIPTION: record.description or "",
            DublinCoreColumns.PUBLISHER: record.publisher or "",
            DublinCoreColumns.CONTRIBUTOR: self._format_illustrators(record.illustrators),
            DublinCoreColumns.DATE: str(record.publication_year) if record.publication_year else "",
            DublinCoreColumns.TYPE: record.medium_type or "",
            DublinCoreColumns.FORMAT: self._format_page_count(record.page_count),
            DublinCoreColumns.LANGUAGE: record.language or "",

            # Optional
            DublinCoreColumns.SOURCE: record.collection or "",
            DublinCoreColumns.RELATION: record.series_number or "",
            DublinCoreColumns.COVERAGE: record.level or "",
            DublinCoreColumns.RIGHTS: self._format_loanable(item.loanable if item else None),

            # Extensions (item fields)
            DublinCoreColumns.ITEM_ID: item.item_id if item else "",
            DublinCoreColumns.CALL_NUMBER: item.call_number if item else "",
            DublinCoreColumns.ACQUISITION_DATE: str(item.acquisition_date) if item and item.acquisition_date else "",
            DublinCoreColumns.FUNDING_SOURCE: item.funding_source if item else "",
        }

    def _format_authors(self, authors_json: str) -> str:
        """Convert authors JSON array to pipe-separated string.

        Args:
            authors_json: JSON string like '["Author 1", "Author 2"]'

        Returns:
            Pipe-separated string like "Author 1|Author 2"
        """
        if not authors_json:
            return ""

        try:
            authors_list = json.loads(authors_json)
            return "|".join(authors_list)
        except (json.JSONDecodeError, TypeError):
            return ""

    def _format_illustrators(self, illustrators_json: str) -> str:
        """Convert illustrators JSON array to pipe-separated string.

        Args:
            illustrators_json: JSON string like '["Illustrator 1", "Illustrator 2"]'

        Returns:
            Pipe-separated string like "Illustrator 1|Illustrator 2"
        """
        if not illustrators_json:
            return ""

        try:
            illustrators_list = json.loads(illustrators_json)
            return "|".join(illustrators_list)
        except (json.JSONDecodeError, TypeError):
            return ""

    def _format_keywords(self, keywords_json: str) -> str:
        """Convert keywords JSON array to pipe-separated string.

        Args:
            keywords_json: JSON string like '["keyword1", "keyword2"]'

        Returns:
            Pipe-separated string like "keyword1|keyword2"
        """
        if not keywords_json:
            return ""

        try:
            keywords_list = json.loads(keywords_json)
            return "|".join(keywords_list)
        except (json.JSONDecodeError, TypeError):
            return ""

    def _format_isbn(self, isbn: str) -> str:
        """Format identifier for Dublin Core / CSV export.

        Values are already stored with prefix in the database.
        Returns the value as-is when already prefixed; adds ``isbn:`` prefix for
        legacy bare values (safety net for pre-migration data).

        Args:
            isbn: Identifier string

        Returns:
            Identifier with prefix (e.g., "isbn:9782070612758", "issn:1163-7706") or empty string
        """
        if not isbn:
            return ""
        if isbn.lower().startswith(("isbn:", "issn:")):
            return isbn  # already correctly prefixed
        return f"isbn:{isbn}"  # legacy bare value

    def _format_loanable(self, loanable: bool = None) -> str:
        """Convert boolean loanable to human-readable string.

        Args:
            loanable: Boolean indicating if item can be loaned

        Returns:
            "Loanable", "Not loanable", or empty string
        """
        if loanable is None:
            return ""

        return "Loanable" if loanable else "Not loanable"

    def _format_page_count(self, page_count: int) -> str:
        """Convert page count to Dublin Core format.

        Args:
            page_count: Number of pages

        Returns:
            Formatted string like "300 pages" or empty string
        """
        if not page_count:
            return ""

        return f"{page_count} pages"

    def export_borrowers_to_csv(self) -> Tuple[str, int]:
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
            from sqlalchemy.orm import joinedload
            borrowers = (
                self.db.query(Borrower)
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
                row = self._borrower_to_dict(borrower)
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
            )

    def _borrower_to_dict(self, borrower: Borrower) -> dict:
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
