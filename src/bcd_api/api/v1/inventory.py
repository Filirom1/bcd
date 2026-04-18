"""Inventory API Endpoints

REST API for collection inventory operations (récolement/weeding).
"""

import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.deps import get_db
from ...core.exceptions import ItemNotFoundException
from ...services import inventory_service
from ...schemas.inventory import (
    ItemInventoryResponse,
    BulkInventoryRequest,
    BulkInventoryResponse,
    InventorySearchResponse,
    BulkUpdateRequest,
    BulkUpdateResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    ExportCSVRequest
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["inventory"])


# ==================== User Story 1: Barcode Scanning ====================


@router.patch("/items/{item_id}", response_model=ItemInventoryResponse)
def mark_item_inventoried_endpoint(
    item_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a single item as inventoried (barcode scan).

    Updates `last_inventoried_at` timestamp to current time.

    **Path Parameters:**
    - item_id: Item barcode (e.g., "0785")

    **Returns:**
    - 200: Item marked successfully with inventory timestamp
    - 404: Item not found

    **Usage:** Barcode scanner workflow
    """
    try:
        item = inventory_service.mark_item_inventoried(db, item_id)

        # Build response from item + bibliographic_record (all fields for working table display)
        record = item.bibliographic_record
        return ItemInventoryResponse(
            # Item fields
            item_id=item.item_id,
            bibliographic_record_id=item.bibliographic_record_id,
            status=item.status,
            condition=item.condition,
            loanable=item.loanable,
            shelf_location=item.shelf_location,
            last_inventoried_at=item.last_inventoried_at,
            # Record fields
            title=record.title,
            genre=record.genre,
            level=record.level,
            target_audience=record.target_audience,
            language=record.language,
            medium_type=record.medium_type
        )

    except ItemNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error marking item {item_id} as inventoried: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark item as inventoried: {str(e)}")


# ==================== User Story 2: Search-Based Item Discovery ====================


@router.post("/items/bulk-mark", response_model=BulkInventoryResponse)
def bulk_mark_inventoried_endpoint(
    request: BulkInventoryRequest,
    db: Session = Depends(get_db)
):
    """
    Mark multiple items as inventoried (file import, search add).

    Updates `last_inventoried_at` timestamp for all items in the list.

    **Request Body:**
    - item_ids: List of item barcodes (e.g., ["0785", "0784", "0312"])

    **Returns:**
    - 200: Items marked successfully with counts and timestamp
    - 422: Validation error (empty list, etc.)

    **Usage:** File import workflow, search results bulk add
    """
    try:
        result = inventory_service.bulk_mark_inventoried(db, request.item_ids)
        return BulkInventoryResponse(**result)

    except Exception as e:
        logger.error(f"Error bulk marking items as inventoried: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to bulk mark items: {str(e)}")


@router.get("/items/search", response_model=InventorySearchResponse)
def search_items_endpoint(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Free text search (title, author, ISBN, call number)"),
    status: Optional[str] = Query(None, description="Item status filter"),
    condition: Optional[str] = Query(None, description="Item condition filter"),
    shelf_location: Optional[str] = Query(None, description="Partial match on location"),
    never_inventoried: Optional[bool] = Query(None, description="Only items with NULL last_inventoried_at"),
    inventoried_before: Optional[date] = Query(None, description="Items not inventoried since this date"),
    acquired_before: Optional[date] = Query(None, description="Items acquired before this date (for age filtering)"),
    medium_type: Optional[str] = Query(None, description="Bibliographic medium type"),
    target_audience: Optional[str] = Query(None, description="child, youth, adult"),
    genre: Optional[str] = Query(None, description="Partial match on genre"),
    level: Optional[str] = Query(None, description="Partial match on reading level"),
    language: Optional[str] = Query(None, description="Language code filter (ISO 639-1, e.g. 'fr', 'en'); use '__none__' for records with no language set"),
    publication_year_min: Optional[int] = Query(None, description="Min publication year"),
    publication_year_max: Optional[int] = Query(None, description="Max publication year"),
    max_borrows: Optional[int] = Query(None, description="Max loans in period (rotation filter)"),
    since_date: Optional[date] = Query(None, description="Start date for rotation filter"),
    no_limit: bool = Query(False, description="Skip result limit, return all matching items")
):
    """
    Search items matching inventory criteria (rotation, last inventoried, condition, etc.).

    Supports 15 optional query parameters for filtering. Results capped at 200 items.

    **Query Parameters:** (all optional)
    - Text search: q
    - Item filters: status, condition, shelf_location
    - Inventory filters: never_inventoried, inventoried_before, acquired_before
    - Record filters: medium_type, target_audience, genre, level, language
    - Publication year: publication_year_min, publication_year_max
    - Rotation filter (CREW method): max_borrows + since_date

    **Returns:**
    - 200: Search results with items, counts, and archive cutoff date
    - 422: Validation error

    **Usage:** Search tab in inventory page
    """
    try:
        result = inventory_service.search_items(
            db=db,
            q=q,
            status=status,
            condition=condition,
            shelf_location=shelf_location,
            never_inventoried=never_inventoried,
            inventoried_before=inventoried_before,
            acquired_before=acquired_before,
            medium_type=medium_type,
            target_audience=target_audience,
            genre=genre,
            level=level,
            language=language,
            publication_year_min=publication_year_min,
            publication_year_max=publication_year_max,
            max_borrows=max_borrows,
            since_date=since_date,
            no_limit=no_limit
        )
        return InventorySearchResponse(**result)

    except Exception as e:
        logger.error(f"Error searching items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search items: {str(e)}")


# ==================== User Story 3: Bulk Edit of Items and Records ====================


@router.post("/items/bulk-update", response_model=BulkUpdateResponse)
def bulk_update_items_endpoint(
    request: BulkUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Apply same changes to multiple items + their parent records (bulk edit).

    **Request Body:**
    - item_ids: List of item barcodes to update
    - item_updates: Optional item field updates (status, condition, loanable, shelf_location)
    - record_updates: Optional record field updates (genre, level, target_audience)

    **Returns:**
    - 200: Items and records updated successfully with counts
    - 422: Validation error

    **Usage:** Bulk edit panel in inventory page
    """
    try:
        # Convert Pydantic models to dicts (excluding None values)
        item_updates_dict = request.item_updates.model_dump(exclude_none=True) if request.item_updates else None
        record_updates_dict = request.record_updates.model_dump(exclude_none=True) if request.record_updates else None

        result = inventory_service.bulk_update_items(
            db=db,
            item_ids=request.item_ids,
            item_updates=item_updates_dict,
            record_updates=record_updates_dict
        )
        return BulkUpdateResponse(**result)

    except Exception as e:
        logger.error(f"Error bulk updating items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to bulk update items: {str(e)}")


# ==================== User Story 5: Bulk Deaccessioning and Deletion ====================


@router.delete("/items/bulk", response_model=BulkDeleteResponse)
def delete_items_bulk_endpoint(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Permanently delete items from system (on_loan items excluded, holds cancelled).

    **Request Body:**
    - item_ids: List of item barcodes to delete

    **Returns:**
    - 200: Items deleted successfully with counts
    - 422: Validation error

    **Usage:** Delete button in bulk edit panel
    """
    try:
        result = inventory_service.delete_items_bulk(db, request.item_ids)
        return BulkDeleteResponse(**result)

    except Exception as e:
        logger.error(f"Error deleting items in bulk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete items: {str(e)}")


# ==================== User Story 6: Working Table Management and Export ====================


@router.post("/export-csv")
def export_csv_endpoint(
    request: ExportCSVRequest,
    db: Session = Depends(get_db)
):
    """
    Export working table to CSV file.

    **Request Body:**
    - item_ids: List of item barcodes to export

    **Returns:**
    - 200: CSV file with Content-Type: text/csv
    - 422: Validation error

    **Usage:** Export CSV button in admin dropdown
    """
    from fastapi.responses import Response
    from datetime import datetime

    try:
        csv_content = inventory_service.get_items_csv(db, request.item_ids)

        # Generate filename with current date
        filename = f"inventory_{datetime.now().strftime('%Y-%m-%d')}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")
