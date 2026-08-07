"""Catalog Export Service

Service for exporting catalog records to Dublin Core CSV format.
"""

import csv
import json
import logging
from io import StringIO
from typing import List, Tuple

from sqlalchemy.orm import Session, joinedload

from src.bcd_api.core.exceptions import ExportFailedException, ExportTooLargeException
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from .import_ import DublinCoreColumns

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
                self.db.query(BibliographicRecord)
                .options(joinedload(BibliographicRecord.items))
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
            logger.exception("Catalog export failed")
            raise ExportFailedException(
                reason=str(e),
                details={"error_type": type(e).__name__}
            ) from e

    def _get_csv_fieldnames(self) -> List[str]:
        """Get list of CSV fieldnames (standard 15 DC fields + item fields)."""
        return [
            # Standard Dublin Core fields
            DublinCoreColumns.TITLE,
            DublinCoreColumns.IDENTIFIER,
            DublinCoreColumns.CREATOR,
            DublinCoreColumns.SUBJECT,
            DublinCoreColumns.DESCRIPTION,
            DublinCoreColumns.PUBLISHER,
            DublinCoreColumns.CONTRIBUTOR,
            DublinCoreColumns.DATE,
            DublinCoreColumns.TYPE,
            DublinCoreColumns.FORMAT,
            DublinCoreColumns.LANGUAGE,
            DublinCoreColumns.SOURCE,
            DublinCoreColumns.RELATION,
            DublinCoreColumns.COVERAGE,
            DublinCoreColumns.RIGHTS,
            # BCD extensions for items
            "item.id",
            "item.callNumber",
            "item.acquisitionDate",
            "item.fundingSource",
        ]

    def _record_to_dict(self, record: BibliographicRecord, item: Item = None) -> dict:
        """Convert bibliographic record and optional item to flat CSV dict.

        Args:
            record: Bibliographic record
            item: Item (optional)

        Returns:
            Dictionary mapping CSV fieldnames to values
        """
        # Parse authors (JSON list in DB -> pipe-separated)
        creators = self._deserialize_list_to_pipe(record.authors)

        # Parse illustrators (JSON list in DB -> pipe-separated)
        contributors = self._deserialize_list_to_pipe(record.illustrators)

        # Parse keywords (JSON list in DB -> pipe-separated)
        subjects = self._deserialize_list_to_pipe(record.keywords)

        # Format publication date (year)
        date_str = str(record.publication_year) if record.publication_year else ""

        # Map medium type back to Dublin Core type
        # For simple mapping (reverse of import)
        dc_type = record.medium_type or ""

        # Format format (page count + "pages" suffix)
        format_str = self._format_page_count(record.page_count)

        # Format rights (loanable boolean -> Loanable/Not loanable)
        rights_str = ""
        if item:
            rights_str = self._format_loanable(item.loanable)

        # Base record fields
        row = {
            DublinCoreColumns.TITLE: record.title or "",
            DublinCoreColumns.IDENTIFIER: self._format_isbn(record.isbn),
            DublinCoreColumns.CREATOR: creators,
            DublinCoreColumns.SUBJECT: subjects,
            DublinCoreColumns.DESCRIPTION: record.description or "",
            DublinCoreColumns.PUBLISHER: record.publisher or "",
            DublinCoreColumns.CONTRIBUTOR: contributors,
            DublinCoreColumns.DATE: date_str,
            DublinCoreColumns.TYPE: dc_type,
            DublinCoreColumns.FORMAT: format_str,
            DublinCoreColumns.LANGUAGE: record.language or "",
            DublinCoreColumns.SOURCE: record.collection or "",
            DublinCoreColumns.RELATION: record.series_number or "",
            DublinCoreColumns.COVERAGE: record.level or "",
            DublinCoreColumns.RIGHTS: rights_str,
        }

        # Item fields
        if item:
            row.update({
                "item.id": item.item_id or "",
                "item.callNumber": item.call_number or "",
                "item.acquisitionDate": item.acquisition_date.isoformat() if item.acquisition_date else "",
                "item.fundingSource": item.funding_source or "",
            })
        else:
            row.update({
                "item.id": "",
                "item.callNumber": "",
                "item.acquisitionDate": "",
                "item.fundingSource": "",
            })

        return row

    def _deserialize_list_to_pipe(self, keywords_json: str) -> str:
        """Convert JSON serialized list to pipe-separated string.

        Args:
            keywords_json: JSON string representing list of strings

        Returns:
            Pipe-separated string or empty string
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


def export_catalog_to_dublin_core_csv(db: Session) -> Tuple[str, int, int]:
    """Helper wrapper function to export catalog to Dublin Core CSV."""
    exporter = ExportService(db)
    return exporter.export_catalog_to_csv()
