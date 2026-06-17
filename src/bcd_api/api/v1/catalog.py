"""Catalog API Endpoints

Handles bibliographic records and items management.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response, status
from sqlalchemy.orm import Session

from ...core.deps import get_db
from ...core.exceptions import NotFoundError, NotFoundException, ValidationError, ConflictError, ExportTooLargeException, ExportFailedException
from ...schemas.bibliographic_record import (
    BiblographicRecordCreate,
    BiblographicRecordResponse,
)
from ...schemas.item import ItemCreate, ItemResponse, ItemWithCurrentLoan, AvailableIDsResponse
from ...schemas.common import PaginatedResponse
from ...services import catalog_service
from ...services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/locations")
def get_shelf_locations(db: Session = Depends(get_db)):
    """Returns distinct non-empty shelf_location values, sorted."""
    from ...models.item import Item
    results = (
        db.query(Item.shelf_location)
        .filter(Item.shelf_location.isnot(None), Item.shelf_location != "")
        .distinct()
        .order_by(Item.shelf_location)
        .all()
    )
    return {"locations": [r[0] for r in results]}


@router.post("/lookup-isbn")
def lookup_isbn_endpoint(
    isbn: str = Query(..., description="ISBN-10 or ISBN-13 to lookup"),
    db: Session = Depends(get_db)
):
    """
    Lookup ISBN in BNF / Google Books / SUDOC catalog.

    **Workflow:**
    1. First checks if ISBN already exists in local database
    2. If found locally, returns existing record with 409 status
    3. If not found locally, queries BNF → Google Books → SUDOC in order

    **Returns:**
    - 200: Bibliographic data found
    - 404: ISBN not found in any catalog
    - 409: ISBN already exists in local database (returns existing record)
    - 500: API error or timeout
    """
    from ...services.catalog_service import lookup_isbn

    # Use service layer for business logic
    # ConflictError is automatically handled by global exception handler
    data = lookup_isbn(db, isbn)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"ISBN {isbn} not found in any catalog"
        )

    return data


@router.post("/bibliographic", response_model=BiblographicRecordResponse, status_code=201)
def create_bibliographic_record(
    record_data: BiblographicRecordCreate,
    db: Session = Depends(get_db),
    isbn_lookup: bool = Query(
        False, description="Automatically lookup ISBN in BNF catalog if provided"
    ),
):
    """
    Create a new bibliographic record.

    **Request Body Example:**
    ```json
    {
        "title": "Example Book",
        "authors": ["Author Name"],
        "isbn": "978-1234567890",
        "publisher": "Publisher Name",
        "publication_year": 2024,
        "medium_type": "Livre",
        "target_audience": "child"
    }
    ```

    **Modes:**
    - **ISBN lookup mode**: If isbn_lookup=true and ISBN provided, automatically fetches
      metadata from BNF API
    - **Manual entry mode**: If isbn_lookup=false or no ISBN, uses provided data only

    **Returns:**
    - 201: Created bibliographic record
    - 400: Validation error
    - 409: Duplicate ISBN conflict
    """
    # Let BCDExceptions propagate to global handler
    db_record = catalog_service.create_bibliographic_record(
        db=db, record_data=record_data, isbn_lookup=isbn_lookup
    )
    return db_record


@router.get("/bibliographic/search")
def search_bibliographic_records(
    q: Optional[str] = Query(None, description="General search query (title, authors)"),
    title: Optional[str] = Query(None, description="Filter by title (partial match)"),
    author: Optional[str] = Query(None, description="Filter by author (partial match)"),
    isbn: Optional[str] = Query(None, description="Filter by ISBN (exact match)"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    level: Optional[str] = Query(None, description="Filter by reading level"),
    language: Optional[str] = Query(None, description="Filter by language code (e.g., 'fr', 'en')"),
    target_audience: Optional[str] = Query(
        None, description="Filter by target audience (child, youth, adult)"
    ),
    medium_type: Optional[str] = Query(None, description="Filter by medium type (Livre, CD, DVD)"),
    available_only: Optional[bool] = Query(None, description="Filter to available items only"),
    borrowed_only: Optional[bool] = Query(None, description="Filter to borrowed items only"),
    has_holds: Optional[bool] = Query(None, description="Filter to records with active holds"),
    shelf_location: Optional[str] = Query(None, description="Filter by shelf location"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Search bibliographic records with filters.

    **Search capabilities:**
    - General search (q): Searches in title and authors
    - Specific filters: title, author, ISBN, genre, language, audience, medium
    - Pagination: limit (max 100) and offset
    - Availability filter: available_only shows only items with available copies
    - Borrowed filter: borrowed_only shows only items with at least one copy borrowed

    **Examples:**
    - `/catalog/bibliographic/search?q=Harry Potter`
    - `/catalog/bibliographic/search?author=Rowling&language=fre`
    """
    # Pass availability filters to service for server-side SQL filtering
    records, total = catalog_service.search_bibliographic_records(
        db=db,
        q=q,
        title=title,
        author=author,
        isbn=isbn,
        genre=genre,
        level=level,
        language=language,
        target_audience=target_audience,
        medium_type=medium_type,
        available_only=available_only,
        borrowed_only=borrowed_only,
        has_holds=has_holds,
        shelf_location=shelf_location,
        limit=limit,
        offset=offset,
    )

    # Compute availability for each record
    import json
    from sqlalchemy import func, case
    from ...models.item import Item
    from ....shared.constants import ItemStatus

    from ...models.hold import Hold

    record_ids = [r.id for r in records]

    # Batch query: counts per record (total + available) in one pass
    counts_rows = (
        db.query(
            Item.bibliographic_record_id,
            func.count(Item.id).label("total"),
            func.sum(
                case((Item.status == ItemStatus.AVAILABLE.value, 1), else_=0)
            ).label("available"),
        )
        .filter(Item.bibliographic_record_id.in_(record_ids))
        .group_by(Item.bibliographic_record_id)
        .all()
    )
    counts_by_record = {row.bibliographic_record_id: row for row in counts_rows}

    # Batch query: active holds per record
    holds_rows = (
        db.query(Hold.bibliographic_record_id, func.count(Hold.id).label("holds"))
        .filter(
            Hold.bibliographic_record_id.in_(record_ids),
            Hold.status.in_(["waiting", "ready"])
        )
        .group_by(Hold.bibliographic_record_id)
        .all()
    )
    holds_by_record = {row.bibliographic_record_id: row.holds for row in holds_rows}

    # Batch query: first item per record (available preferred, then any)
    all_items = (
        db.query(Item)
        .filter(Item.bibliographic_record_id.in_(record_ids))
        .order_by(
            Item.bibliographic_record_id,
            case((Item.status == ItemStatus.AVAILABLE.value, 0), else_=1),
            Item.id,
        )
        .all()
    )
    first_item_by_record: dict = {}
    for item in all_items:
        if item.bibliographic_record_id not in first_item_by_record:
            first_item_by_record[item.bibliographic_record_id] = item

    records_with_availability = []
    for r in records:
        counts = counts_by_record.get(r.id)
        total_count = counts.total if counts else 0
        available_count = int(counts.available or 0) if counts else 0
        active_holds_count = holds_by_record.get(r.id, 0)

        first_item = first_item_by_record.get(r.id)

        # Deserialize authors if it's a JSON string
        authors = r.authors
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except (json.JSONDecodeError, TypeError):
                authors = []
        elif authors is None:
            authors = []

        # Convert to dict and add availability fields
        record_dict = {
            "id": r.id,
            "record_id": r.id,
            "isbn": r.isbn,
            "isbn_value": r.isbn_value,
            "identifier_type": r.identifier_type,
            "title": r.title,
            "subtitle": r.subtitle,
            "authors": authors,
            "publisher": r.publisher,
            "publication_year": r.publication_year,
            "collection": r.collection,
            "series_number": r.series_number,
            "genre": r.genre,
            "medium_type": r.medium_type,
            "target_audience": r.target_audience,
            "level": r.level,
            "language": r.language,
            "binding_type": r.binding_type,
            "page_count": r.page_count,
            "has_illustrations": r.has_illustrations,
            "total_items": total_count,
            "total_copies": total_count,
            "available_copies": available_count,
            "active_holds_count": active_holds_count,
            "cover_image": r.cover_image,
            "first_item_id": first_item.item_id if first_item else None,
            "shelf_location": first_item.shelf_location if first_item else None,
            "call_number": first_item.call_number if first_item else None,
        }
        records_with_availability.append(record_dict)

    # Return JSON response
    return PaginatedResponse(
        items=records_with_availability,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/bibliographic/{record_id}", response_model=BiblographicRecordResponse)
def get_bibliographic_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    Get bibliographic record by ID.

    **Returns:**
    - 200: Bibliographic record with all metadata
    - 404: Record not found
    """
    from ...models.item import Item
    record = catalog_service.get_bibliographic_record(db, record_id)
    record.total_items = db.query(Item).filter(Item.bibliographic_record_id == record_id).count()
    return record


@router.get("/bibliographic/{record_id}/items", response_model=list[ItemWithCurrentLoan])
def get_items_for_bibliographic_record(record_id: int, db: Session = Depends(get_db)):
    """Get all items (copies) for a bibliographic record with availability status."""
    # First verify record exists
    catalog_service.get_bibliographic_record(db, record_id)
    # Get all items
    items = catalog_service.get_items_for_bibliographic_record(db, record_id)
    return items


@router.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item (physical copy).

    **Required fields:**
    - item_id: Unique inventory number (configurable format: numeric or alphanumeric)
    - bibliographic_record_id: FK to bibliographic record

    **Optional fields:**
    - call_number: Dewey/CDU classification (e.g., "800.000")
    - shelf_location: Physical location (e.g., "Fiction - Section A")
    - condition: Item condition (good, damaged, lost, withdrawn)
    - loanable: Can be borrowed (default: true)
    - acquisition_date, funding_source
    """
    db_item = catalog_service.create_item(db, item)
    return db_item


@router.get(
    "/items/available-ids",
    response_model=AvailableIDsResponse,
    summary="Generate available item IDs for pre-printing barcode labels"
)
def get_available_item_ids_endpoint(
    count: int = Query(default=30, ge=1, le=1000, description="Number of IDs to generate"),
    start_from: Optional[str] = Query(default=None, description="Starting ID (optional, auto-detect if omitted)"),
    contiguous: bool = Query(default=True, description="If true, IDs form a gapless block; if false, scatter (gaps allowed)"),
    db: Session = Depends(get_db)
):
    """
    Generate a list of available item IDs that are not currently assigned to any items.

    This endpoint is used by the print labels page to generate free barcode IDs
    that can be pre-printed on sticker labels and applied to books before cataloging.

    **Workflow:**
    1. Librarian calls this endpoint to get a batch of free IDs
    2. Print barcode labels with these IDs
    3. Stick labels on physical books
    4. Later, scan barcode + ISBN to register books in the system

    **ID Format:**
    - Respects system settings (numeric or alphanumeric)
    - Numeric format: finds first contiguous block of free IDs (e.g., 2000, 2001, 2002...)
    - All returned IDs are guaranteed to be free and sequential with no gaps
    - Alphanumeric format: not yet implemented (raises NotImplementedError)

    **Parameters:**
    - count: How many IDs to generate (default: 30 labels = 2.5 Avery sheets)
    - start_from: Optional starting ID (if omitted, searches from 1)

    **Returns:**
    - start_id: First ID in range
    - end_id: Last ID in range
    - ids: Array of all generated IDs (all free, all contiguous)
    - count: Number of IDs generated
    - id_format: Current ID format setting

    **Example Response:**
    ```json
    {
      "start_id": "2000",
      "end_id": "2029",
      "ids": ["2000", "2001", "2002", ..., "2029"],
      "count": 30,
      "id_format": "numeric"
    }
    ```
    """
    try:
        return catalog_service.get_available_item_ids(db, count, start_from, contiguous)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: str, db: Session = Depends(get_db)):
    """Get item by item_id (inventory number)."""
    item = catalog_service.get_item(db, item_id)
    return item


@router.get("/importers")
def list_importers():
    """
    List supported catalog import formats.

    Scans the scripts/convert/ directory for conversion scripts
    (*_to_dublin_core.py). Each script becomes a named importer.
    The importer name is derived from the filename by removing the
    _to_dublin_core.py suffix.

    **Returns**: List of importers with name, description and filename.
    """
    from bcd_converters import list_converters

    # Built-in native format always comes first
    importers = [
        {
            "name": "dublin_core",
            "description": "Dublin Core CSV — native BCD format (dc.title, dc.creator, dc.identifier, …)",
            "filename": None,
        }
    ]

    for conv in list_converters():
        importers.append({
            "name": conv["name"],
            "description": conv["description"],
            "filename": None,
        })

    return {"importers": importers}


@router.post("/import")
async def import_catalog(
    file: UploadFile = File(..., description="CSV file to import"),
    format: str = Query("dublin_core", description="Source format name (dublin_core or any importer from /importers)"),
    db: Session = Depends(get_db),
):
    """
    Import bibliographic records and items from a CSV file.

    When **format** is `dublin_core` (default), the file is imported directly.
    For any other format, the corresponding conversion script in `scripts/convert/`
    is used to convert the file to Dublin Core before importing. The available
    formats are listed by the `GET /catalog/importers` endpoint.

    **Dublin Core CSV Format** (comma-separated):
    ```
    dc.title,dc.identifier,dc.creator,dc.subject,dc.description,dc.publisher,
    dc.contributor,dc.date,dc.type,dc.format,dc.language,dc.source,dc.relation,
    dc.coverage,dc.rights,item.id,item.callNumber,item.acquisitionDate,item.fundingSource
    ```

    **Dublin Core Elements:**
    - dc.title (required): Title of the work
    - dc.identifier (required): ISBN or unique identifier
    - dc.creator: Authors (pipe-separated for multiple)
    - dc.contributor: Illustrators (pipe-separated)
    - dc.subject: Keywords (pipe-separated)
    - dc.description: Description
    - dc.publisher: Publisher name
    - dc.date: Publication year (YYYY)
    - dc.type: Medium type (Text, Sound, MovingImage, etc.)
    - dc.format: Physical format (e.g., "300 pages")
    - dc.language: ISO 639 language code
    - dc.source: Collection/Series name
    - dc.relation: Series number
    - dc.coverage: Target audience/level
    - dc.rights: Loanable status

    **Item Extensions:**
    - item.id: Item inventory number (required if dc.identifier is ISBN)
    - item.callNumber: Call number/Shelf location
    - item.acquisitionDate: Acquisition date (YYYY-MM-DD)
    - item.fundingSource: Funding source

    **Import Strategy:**
    1. Groups rows by ISBN (or Title if no ISBN) → creates one BiblographicRecord per title
    2. Creates one Item per row linked to BiblographicRecord
    3. Skips duplicates (existing ISBNs and item_ids)

    **Response:**
    - records_created: Number of new bibliographic records
    - items_created: Number of new items
    - records_skipped: Number of duplicate bibliographic records
    - items_skipped: Number of duplicate items
    - errors: List of errors with row numbers
    - total_rows: Total rows processed

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/catalog/import" \\
      -F "file=@catalog_dublin_core.csv"

    curl -X POST "http://localhost:8000/api/v1/catalog/import?format=bcdi" \\
      -F "file=@bcdi_export.csv"
    ```
    """
    from src.bcd_api.services.dublin_core_import import import_dublin_core_csv

    try:
        content = await file.read()

        if format == "dublin_core":
            csv_content = content.decode("utf-8")
        else:
            from bcd_converters import get_converter

            try:
                module = get_converter(format)
            except ModuleNotFoundError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown import format: '{format}'. See GET /catalog/importers for supported formats.",
                )

            if not hasattr(module, "convert"):
                raise HTTPException(
                    status_code=501,
                    detail=f"Format '{format}' does not support server-side conversion (missing convert() function).",
                )

            csv_content = module.convert(content)

        result = import_dublin_core_csv(db, csv_content)
        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error importing catalog CSV (format=%s)", format)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/export")
def export_catalog(db: Session = Depends(get_db)):
    """
    Export entire catalog to Dublin Core CSV format.

    Generates a CSV file with bibliographic records and items.
    - One row per item (physical copy)
    - Records without items generate one row with empty item fields
    - UTF-8 encoding for French character support
    - Dublin Core standard column names (dc.title, dc.creator, etc.)

    **Returns:**
    - CSV file download with timestamped filename
    - Content-Type: text/csv; charset=utf-8

    **Limitations:**
    - Maximum 10,000 rows per export
    - Use filtering or batching for larger catalogs

    **Example CSV columns:**
    ```
    dc.title,dc.identifier,dc.creator,dc.publisher,dc.type,item.id,item.callNumber
    ```
    """
    try:
        # Create export service
        export_service = ExportService(db)

        # Generate CSV
        csv_content, record_count, item_count = export_service.export_catalog_to_csv()

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"catalog_export_{timestamp}.csv"

        # Return CSV as download
        # Use UTF-8 encoding (UTF-8-sig for Excel compatibility could be added as query param)
        return Response(
            content=csv_content.encode('utf-8'),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Record-Count": str(record_count),
                "X-Item-Count": str(item_count)
            }
        )

    except ExportTooLargeException as e:
        logger.warning(f"Export too large: {e.context}")
        raise HTTPException(
            status_code=400,
            detail=e.detail
        )
    except ExportFailedException as e:
        logger.exception(f"Export failed: {e.detail}")
        raise HTTPException(
            status_code=500,
            detail=e.detail
        )
    except Exception as e:
        logger.exception("Unexpected error during catalog export")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


# === US6: Single Catalog Record/Item Editing ===


@router.patch("/records/{record_id}", response_model=BiblographicRecordResponse)
def update_record_endpoint(
    record_id: int,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """
    Update a single bibliographic record (US6).

    Allows editing metadata fields for catalog records.

    Args:
        record_id: Record ID
        update_data: Fields to update
        db: Database session

    Returns:
        Updated bibliographic record

    Raises:
        404: Record not found
    """
    try:
        record = catalog_service.update_record(
            db=db,
            record_id=record_id,
            update_data=update_data
        )
        return record
    except Exception as e:
        logger.error(f"Update record failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Update record failed: {str(e)}")


@router.patch("/items/{item_id}", response_model=ItemResponse)
def update_item_endpoint(
    item_id: str,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """
    Update a single item (US6).

    Allows editing item details including barcode, call number, location, etc.
    Validates barcode uniqueness if item_id is being changed.

    Args:
        item_id: Item database ID (not item_id/barcode)
        update_data: Fields to update
        db: Database session

    Returns:
        Updated item

    Raises:
        404: Item not found
        409: Duplicate barcode
    """
    try:
        item = catalog_service.update_item(
            db=db,
            item_id=item_id,
            update_data=update_data
        )
        return item
    except Exception as e:
        logger.error(f"Update item failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Update item failed: {str(e)}")


@router.delete("/items/{item_id}", status_code=204)
def delete_item_endpoint(
    item_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a single item.

    WARNING: This permanently deletes the physical item and all associated circulation history.
    """
    catalog_service.delete_item(db, item_id)
    return Response(status_code=204)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bibliographic_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a bibliographic record and all associated items.

    Validates that no items have active loans before deletion.
    CASCADE deletes all items and circulation history.

    **Errors**:
    - 404: Record not found
    - 400: One or more items have active loans (cannot delete)
    """
    # Reuse bulk delete with single ID
    catalog_service.bulk_delete_records(db, [record_id])
    return None
