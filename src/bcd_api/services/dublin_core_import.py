"""Dublin Core CSV Import Service

Standard Dublin Core CSV import for library catalog interoperability.
"""

import csv
import json
import logging
from datetime import datetime
from io import StringIO

from sqlalchemy.orm import Session

from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.services.import_service import ImportResult, DublinCoreColumns, _normalize_isbn

logger = logging.getLogger(__name__)


def import_dublin_core_csv(db: Session, csv_content: str) -> ImportResult:
    """
    Import bibliographic records and items from Dublin Core CSV file.

    Dublin Core CSV Format (comma or semicolon-separated):
    Required: dc.title, dc.identifier (ISBN or item ID)
    Optional: dc.creator, dc.subject, dc.description, dc.publisher, dc.contributor,
              dc.date, dc.type, dc.format, dc.language, dc.source, dc.relation,
              dc.coverage, dc.rights
    Extensions: item.id, item.callNumber, item.acquisitionDate, item.fundingSource

    Multi-valued fields (pipe-separated): dc.creator, dc.contributor, dc.subject

    Strategy:
    1. Group rows by ISBN or title
    2. Create one BiblographicRecord per unique title
    3. Create one Item per row
    4. BULK INSERT for performance

    Args:
        db: Database session
        csv_content: CSV file content as string

    Returns:
        ImportResult with statistics and errors
    """
    result = ImportResult()

    # Auto-detect delimiter (comma or semicolon)
    sniffer = csv.Sniffer()
    sample = csv_content[:1024]
    delimiter = sniffer.sniff(sample).delimiter

    logger.info(f"Detected delimiter: {repr(delimiter)}")

    # Parse CSV
    csv_file = StringIO(csv_content)
    reader = csv.DictReader(csv_file, delimiter=delimiter)

    # Group rows by ISBN or Title
    biblio_map = {}  # Key: ISBN or Title -> dict of biblio data
    items_to_create = []  # List of (row_num, row_data, biblio_key)

    row_num = 1  # Start at 1 (header is row 0)
    for row in reader:
        row_num += 1

        # Debug first row
        if row_num == 2:
            logger.info(f"First row keys: {list(row.keys())[:5]}")
            logger.info(f"First row dc.title value: {row.get('dc.title', 'NOT FOUND')}")
            logger.info(f"Full first row: {dict(list(row.items())[:3])}")

        try:
            # Validate required fields
            title = row.get(DublinCoreColumns.TITLE, "").strip()
            if not title:
                result.add_error(row_num, f"Missing required field: {DublinCoreColumns.TITLE}")
                continue

            # Get ISBN from dc.identifier
            identifier = row.get(DublinCoreColumns.IDENTIFIER, "").strip()
            isbn = _normalize_isbn(identifier) if identifier else None

            # Determine bibliographic record key
            biblio_key = isbn if isbn else title

            # Store row for item creation later
            items_to_create.append((row_num, row, biblio_key))

            # Skip if we already have this bibliographic record queued
            if biblio_key in biblio_map:
                continue

            # Parse multi-valued fields (pipe-separated)
            creators = [c.strip() for c in row.get(DublinCoreColumns.CREATOR, "").split("|") if c.strip()]
            contributors = [c.strip() for c in row.get(DublinCoreColumns.CONTRIBUTOR, "").split("|") if c.strip()]
            subjects = [s.strip() for s in row.get(DublinCoreColumns.SUBJECT, "").split("|") if s.strip()]

            # Parse date (year)
            publication_year = None
            date_str = row.get(DublinCoreColumns.DATE, "").strip()
            if date_str:
                try:
                    # Try to extract year (YYYY or YYYY-MM-DD)
                    if "-" in date_str:
                        publication_year = int(date_str.split("-")[0])
                    else:
                        publication_year = int(date_str)
                    if publication_year < 1000 or publication_year > 2100:
                        publication_year = None
                except ValueError:
                    pass

            # Map Dublin Core type to medium type string
            dc_type = row.get(DublinCoreColumns.TYPE, "").strip()
            medium_type = _map_dc_type_to_medium_type(dc_type)

            # Parse format for page count (e.g., "300 pages" or "173 p")
            page_count = None
            format_str = row.get(DublinCoreColumns.FORMAT, "").strip()
            if format_str:
                import re
                match = re.search(r"(\d+)\s*(?:p|pages|page)", format_str.lower())
                if match:
                    page_count = int(match.group(1))

            # Create bibliographic record data
            biblio_data = {
                "title": title,
                "subtitle": None,  # Dublin Core doesn't have subtitle
                "isbn": isbn,
                "authors": creators,
                "illustrators": contributors,
                "publisher": row.get(DublinCoreColumns.PUBLISHER, "").strip() or None,
                "publication_year": publication_year,
                "collection": row.get(DublinCoreColumns.SOURCE, "").strip() or None,
                "series_number": row.get(DublinCoreColumns.RELATION, "").strip() or None,
                "genre": None,  # No direct mapping
                "medium_type": medium_type,
                "keywords": subjects,
                "level": row.get(DublinCoreColumns.COVERAGE, "").strip() or None,
                "description": row.get(DublinCoreColumns.DESCRIPTION, "").strip() or None,
                "page_count": page_count,
                "language": row.get(DublinCoreColumns.LANGUAGE, "").strip() or None,
            }

            # Store for creation
            biblio_map[biblio_key] = biblio_data

        except Exception as e:
            logger.exception(f"Error processing row {row_num}")
            result.add_error(row_num, str(e))
            continue

    # BULK OPERATION 1: Check for existing records and prepare new ones
    isbns_to_check = [data["isbn"] for data in biblio_map.values() if data["isbn"]]
    titles_to_check = [data["title"] for data in biblio_map.values() if not data["isbn"]]
    existing_records = {}

    # Check for existing records by ISBN
    if isbns_to_check:
        existing_by_isbn = (
            db.query(BiblographicRecord)
            .filter(BiblographicRecord.isbn.in_(isbns_to_check))
            .all()
        )
        for record in existing_by_isbn:
            existing_records[record.isbn] = record
            result.records_skipped += 1
            logger.info(f"Bibliographic record already exists (ISBN): {record.isbn} (ID: {record.id})")

    # Check for existing records by TITLE (for records without ISBN)
    if titles_to_check:
        existing_by_title = (
            db.query(BiblographicRecord)
            .filter(BiblographicRecord.title.in_(titles_to_check))
            .filter(BiblographicRecord.isbn.is_(None))  # Only match records without ISBN
            .all()
        )
        for record in existing_by_title:
            existing_records[record.title] = record
            result.records_skipped += 1
            logger.info(f"Bibliographic record already exists (Title): {record.title} (ID: {record.id})")

    # Prepare bibliographic records for bulk insert
    new_biblio_objects = []
    created_biblios = {}

    for biblio_key, biblio_data in biblio_map.items():
        # Skip if already exists (check by ISBN or Title)
        if biblio_key in existing_records:
            created_biblios[biblio_key] = existing_records[biblio_key]
            continue

        # Prepare data for BiblographicRecord (convert lists to JSON strings)
        db_data = biblio_data.copy()

        # Convert lists to JSON strings
        if "authors" in db_data and isinstance(db_data["authors"], list):
            db_data["authors"] = json.dumps(db_data["authors"])
        if "illustrators" in db_data and isinstance(db_data["illustrators"], list):
            db_data["illustrators"] = json.dumps(db_data["illustrators"])
        if "keywords" in db_data and isinstance(db_data["keywords"], list):
            db_data["keywords"] = json.dumps(db_data["keywords"])

        # Create BiblographicRecord object
        db_record = BiblographicRecord(**db_data)
        new_biblio_objects.append((biblio_key, db_record))

    # Bulk insert bibliographic records
    if new_biblio_objects:
        db.add_all([obj for _, obj in new_biblio_objects])
        db.flush()  # Flush to get IDs without committing

        for biblio_key, db_record in new_biblio_objects:
            created_biblios[biblio_key] = db_record
            result.records_created += 1
            logger.info(f"Created bibliographic record: {biblio_key} (ID: {db_record.id})")

    # BULK OPERATION 2: Check for existing items and prepare new ones
    # Get item IDs from item.id column or dc.identifier if no item.id
    item_ids_to_check = []
    for _, row, _ in items_to_create:
        item_id = row.get(DublinCoreColumns.ITEM_ID, "").strip()
        if not item_id:
            item_id = row.get(DublinCoreColumns.IDENTIFIER, "").strip()
        if item_id:
            item_ids_to_check.append(item_id)

    existing_items_set = set()
    if item_ids_to_check:
        existing_items = (
            db.query(Item.item_id)
            .filter(Item.item_id.in_(item_ids_to_check))
            .all()
        )
        existing_items_set = {item.item_id for item in existing_items}

    # Prepare items for bulk insert
    new_item_objects = []
    seen_item_ids = set()

    for row_num, row, biblio_key in items_to_create:
        try:
            # Skip if bibliographic record wasn't created
            if biblio_key not in created_biblios:
                result.items_skipped += 1
                continue

            biblio_record = created_biblios[biblio_key]

            # Get item ID from item.id or dc.identifier
            item_id = row.get(DublinCoreColumns.ITEM_ID, "").strip()
            if not item_id:
                item_id = row.get(DublinCoreColumns.IDENTIFIER, "").strip()

            if not item_id:
                result.add_error(row_num, f"Missing item ID (need {DublinCoreColumns.ITEM_ID} or {DublinCoreColumns.IDENTIFIER})")
                result.items_skipped += 1
                continue

            # Skip if item already exists in database
            if item_id in existing_items_set:
                logger.info(f"Item already exists in database: {item_id}")
                result.items_skipped += 1
                continue

            # Skip if duplicate within this CSV import
            if item_id in seen_item_ids:
                logger.warning(f"Duplicate item_id in CSV: {item_id} (row {row_num})")
                result.items_skipped += 1
                continue

            seen_item_ids.add(item_id)

            # Parse acquisition date
            acquisition_date = None
            acq_date_str = row.get(DublinCoreColumns.ACQUISITION_DATE, "").strip()
            if acq_date_str:
                try:
                    acquisition_date = datetime.strptime(acq_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Parse loanable from dc.rights
            loanable = True  # Default
            rights = row.get(DublinCoreColumns.RIGHTS, "").strip().lower()
            if rights in ["not loanable", "reference only", "non"]:
                loanable = False

            # Create Item object (barcode is auto-computed from item_id via property)
            db_item = Item(
                item_id=item_id,
                bibliographic_record_id=biblio_record.id,
                call_number=row.get(DublinCoreColumns.CALL_NUMBER, "").strip() or None,
                loanable=loanable,
                acquisition_date=acquisition_date,
                funding_source=row.get(DublinCoreColumns.FUNDING_SOURCE, "").strip() or None,
            )
            new_item_objects.append(db_item)
            result.items_created += 1

        except Exception as e:
            logger.exception(f"Error preparing item at row {row_num}")
            result.add_error(row_num, f"Item preparation failed: {str(e)}")
            continue

    # Bulk insert items
    if new_item_objects:
        db.add_all(new_item_objects)
        db.flush()  # Flush so items get IDs and are visible within the transaction

        # Reconcile total_items counter for all touched bibliographic records.
        # The counter may be stale (set at record creation time before items existed).
        touched_record_ids = {item.bibliographic_record_id for item in new_item_objects}
        for record_id in touched_record_ids:
            count = (
                db.query(Item)
                .filter(Item.bibliographic_record_id == record_id)
                .count()
            )
            db.query(BiblographicRecord).filter(
                BiblographicRecord.id == record_id
            ).update({"total_items": count}, synchronize_session=False)

    # SINGLE COMMIT for all operations
    db.commit()

    logger.info(
        f"Dublin Core import complete: {result.records_created} records, "
        f"{result.items_created} items created, "
        f"{len(result.errors)} errors"
    )

    return result


def _map_dc_type_to_medium_type(dc_type: str) -> str:
    """
    Map Dublin Core Type to medium type string.

    Dublin Core Type vocabulary: Text, Image, Sound, MovingImage, Dataset, etc.

    Args:
        dc_type: Dublin Core type value

    Returns:
        Medium type string (e.g., "Livre", "CD", "DVD", etc.)
    """
    if not dc_type or not dc_type.strip():
        return "Livre"

    dc_type_lower = dc_type.strip().lower()

    # Map DC types to medium type strings (supports both Dublin Core standard values and French labels)
    # Check periodical before text because 'Text;Periodical' contains 'text'
    if "periodical" in dc_type_lower or "journal" in dc_type_lower or "magazine" in dc_type_lower or "revue" in dc_type_lower or "périodique" in dc_type_lower:
        return "Périodique"
    elif "text" in dc_type_lower or "book" in dc_type_lower or "livre" in dc_type_lower:
        return "Livre"
    elif "sound" in dc_type_lower or "audio" in dc_type_lower or "cd" in dc_type_lower:
        return "CD"
    elif "movingimage" in dc_type_lower or "video" in dc_type_lower or "dvd" in dc_type_lower or "film" in dc_type_lower:
        return "DVD"
    elif "autre" in dc_type_lower or "other" in dc_type_lower:
        return "Autre"
    else:
        # Return as-is if it doesn't match any known pattern (allows custom values)
        return dc_type.strip()
