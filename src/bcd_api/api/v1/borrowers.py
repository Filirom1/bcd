"""
Borrowers API Endpoints

Provides REST API endpoints for borrower management.
"""

import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from datetime import datetime

from fastapi.responses import Response

from ...core.deps import get_db
from ...core.exceptions import NotFoundError, ValidationError
from ...schemas.borrower import (
    BorrowerCreate,
    BorrowerDetailed,
    BorrowerResponse,
    BorrowerUpdate,
)
from ...services import borrower_service

router = APIRouter(prefix="/borrowers", tags=["borrowers"])


def _get_borrower_class_info(db: Session, borrower) -> Tuple[Optional[str], Optional[str]]:
    """Deprecated: class info is now populated via borrower_service.enrich_borrower."""
    if not borrower:
        return None, None
    return getattr(borrower, "class_name", None), getattr(borrower, "homeroom_teacher", None)


@router.post("", response_model=BorrowerResponse, status_code=status.HTTP_201_CREATED)
def create_borrower(
    request: BorrowerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new borrower (student, teacher, or staff).

    Auto-generates barcode based on borrower_id.
    Validates ID format against system settings.

    **Errors**:
    - 400: Invalid borrower ID format or role
    - 404: Class not found (if class_id provided)
    - 409: Borrower ID already exists
    """
    borrower = borrower_service.create_borrower(
        db=db,
        borrower_id=request.borrower_id,
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role,
        class_id=request.class_id,
        email=request.email,
        phone=request.phone,
        notes=request.notes,
    )
    return borrower


@router.get("/template")
def get_borrowers_template():
    """
    Download the CSV template for borrower import.
    """
    from fastapi.responses import FileResponse
    from ...core.portable import get_bundled_resource

    template_path = get_bundled_resource("data/templates/borrowers_bcd.csv")
    if not template_path or not template_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Borrowers CSV template file not found"
        )
    return FileResponse(
        path=template_path,
        media_type="text/csv",
        filename="borrowers_template.csv"
    )


@router.post("/import")
async def import_borrowers_csv(
    file: UploadFile = File(..., description="CSV file with borrower data"),
    db: Session = Depends(get_db)
):
    """
    Import borrowers from CSV file with upsert behavior.

    Expected CSV format: borrower_id, first_name, last_name, role, class (optional)

    **Upsert Behavior**:
    - If borrower_id exists: Update existing borrower
    - If borrower_id is new: Create new borrower

    **Returns**:
    - total_rows: Total rows in CSV
    - successful_rows: Number of rows successfully processed
    - failed_rows: Number of rows that failed
    - borrowers_created: Number of new borrowers created
    - borrowers_updated: Number of existing borrowers updated
    - errors: List of error details with row numbers
    """
    try:
        # Read CSV file and handle different encodings
        contents = await file.read()

        # Try UTF-8 first, then Latin-1 (ISO-8859-1) which handles French characters
        try:
            csv_text = contents.decode('utf-8')
        except UnicodeDecodeError:
            try:
                csv_text = contents.decode('latin-1')
            except UnicodeDecodeError:
                csv_text = contents.decode('windows-1252')

        return borrower_service.import_borrowers_from_csv(db, csv_text)

    except Exception as e:
        logger.exception("Borrower import failed")
        raise HTTPException(status_code=400, detail=f"Failed to import CSV: {str(e)}")



@router.get("/export", response_class=Response)
def export_borrowers(db: Session = Depends(get_db)):
    """
    Export all borrowers to BCD borrower CSV format.

    Returns CSV file download with UTF-8 encoding and BOM for Excel compatibility.

    **CSV Columns**:
    - borrower_id: Unique borrower identifier
    - first_name: Borrower's first name
    - last_name: Borrower's last name
    - role: student, teacher, or staff
    - class: Class name (if applicable)
    - barcode: Barcode identifier
    - active: true or false
    - blocked: true or false
    - blocked_reason: Reason for blocking (if blocked)

    **Limits**:
    - Maximum 5,000 borrowers per export

    **Errors**:
    - 400: Export exceeds 5,000 borrower limit
    - 500: Export generation failed
    """
    try:
        # Generate CSV
        csv_content, borrower_count = borrower_service.export_borrowers_to_csv(db)

        # Add UTF-8 BOM for Excel compatibility
        csv_with_bom = '\ufeff' + csv_content

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'borrowers_export_{timestamp}.csv'

        logger.info(f"Borrower export successful: {borrower_count} borrowers exported")

        # Return as downloadable file
        return Response(
            content=csv_with_bom.encode('utf-8'),
            media_type='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Row limit exceeded
        logger.warning(f"Borrower export failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Database or other errors
        logger.exception("Unexpected error during borrower export")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/next-available-id")
def get_next_available_id(db: Session = Depends(get_db)):
    """
    Get the smallest positive borrower ID not currently in use.

    Enables reuse of IDs freed when students leave (e.g., CM2 deletion at year-end).
    Only considers numeric IDs; non-numeric IDs (e.g., "PROF1") are ignored.
    """
    next_id = borrower_service.get_next_available_id(db)
    return {"next_id": next_id}


@router.get("/{borrower_id}")
def get_borrower(
    borrower_id: str,
    detail: bool = Query(False, description="Return detailed view with circulation history"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a borrower.

    Includes current loans count, total checkouts, and overdue count.

    **Query Parameters**:
    - detail: If true, includes current loans (current_loans).
              Full paginated history is available via GET /circulation/borrower/{id}/history

    **Errors**:
    - 404: Borrower not found
    """
    return borrower_service.get_detailed_borrower(db, borrower_id, include_loans=detail)


@router.get("")
def list_borrowers(
    q: Optional[str] = Query(None, description="Search query (name, borrower_id)"),
    class_id: Optional[int] = Query(None, description="Filter by class ID"),
    role: Optional[str] = Query(None, description="Filter by role (student/teacher/staff)"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    blocked: Optional[bool] = Query(None, description="Filter by blocked status (True = blocked)"),
    has_overdue: Optional[bool] = Query(None, description="Filter by overdue status (True = has overdue items)"),
    # Support both parameter styles for pagination
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(None, ge=1, le=500, description="Items per page"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Maximum results (alternative to page_size)"),
    offset: Optional[int] = Query(None, ge=0, description="Pagination offset (alternative to page)"),
    db: Session = Depends(get_db)
):
    """
    List borrowers with optional filters.

    Supports filtering by class, role, active status, blocked status, and overdue status.
    Results are ordered by class, then last name.

    **Query Parameters**:
    - q: Search in name and borrower_id
    - class_id: Filter by class ID
    - role: Filter by role (student, teacher, staff)
    - active: Filter by active status (true/false)
    - blocked: Filter blocked borrowers (true) or active (false)
    - has_overdue: Filter borrowers with overdue items (true)
    - page: Page number (1-indexed, works with page_size)
    - page_size: Items per page (works with page)
    - limit: Maximum number of results (alternative to page_size, 1-500, default 10)
    - offset: Pagination offset (alternative to page, default 0)
    """
    from datetime import date

    from sqlalchemy import and_

    from ...models.circulation import CirculationTransaction
    from ...services.admin import settings as settings_service

    # Convert page/page_size to limit/offset if provided
    if page is not None and page_size is not None:
        actual_limit = page_size
        actual_offset = (page - 1) * page_size
    elif limit is not None or offset is not None:
        actual_limit = limit if limit is not None else 10
        actual_offset = offset if offset is not None else 0
    else:
        # Defaults
        actual_limit = 10
        actual_offset = 0

    # Get borrowers with server-side filtering and pagination
    borrowers, total = borrower_service.list_borrowers(
        db=db,
        search=q,
        class_id=class_id,
        role=role,
        active=active,
        blocked=blocked,
        has_overdue=has_overdue,
        limit=actual_limit,
        offset=actual_offset,
    )

    # Enrich borrowers with circulation data and loan limits
    settings = settings_service.get_settings(db)
    enriched_borrowers = borrower_service.enrich_borrowers(db, borrowers, settings)

    # Calculate page and page_size from limit/offset for response
    calculated_page = (actual_offset // actual_limit) + 1 if actual_limit > 0 else 1

    return {
        "items": enriched_borrowers,
        "total": total,
        "page": calculated_page,
        "page_size": actual_limit,
        "limit": actual_limit,
        "offset": actual_offset
    }


@router.get("/{borrower_id}/edit")
def get_borrower_edit_form(
    borrower_id: str,
    db: Session = Depends(get_db)
):
    """
    Get borrower data for editing.

    Returns borrower details and available classes.

    **Errors**:
    - 404: Borrower not found
    """
    from ...services import class_service

    # Get borrower details
    borrower = borrower_service.get_borrower_by_id(db, borrower_id)

    # Get all classes for the dropdown
    classes = class_service.list_classes(db)

    return {"borrower": borrower, "classes": classes}


@router.patch("/{borrower_id}")
def update_borrower(
    borrower_id: str,
    update_data: BorrowerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update borrower information.

    Can update borrower ID, name, role, class, contact info, active status, and blocked reason.

    **Errors**:
    - 404: Borrower not found or class not found
    - 409: New borrower ID already exists
    - 400: Invalid borrower ID format or invalid role
    """
    borrower = borrower_service.update_borrower(
        db=db,
        borrower_id=borrower_id,
        new_borrower_id=update_data.borrower_id,
        first_name=update_data.first_name,
        last_name=update_data.last_name,
        role=update_data.role,
        class_id=update_data.class_id,
        email=update_data.email,
        phone=update_data.phone,
        notes=update_data.notes,
        active=update_data.active,
        blocked_reason=update_data.blocked_reason,
    )

    return borrower


@router.post("/{borrower_id}/unblock", response_model=BorrowerResponse)
def unblock_borrower(
    borrower_id: str,
    db: Session = Depends(get_db)
):
    """
    Unblock a borrower by setting active=True and clearing blocked_reason.

    **Errors**:
    - 404: Borrower not found
    """
    borrower = borrower_service.unblock_borrower(db, borrower_id)
    return borrower


@router.post("/{borrower_id}/block", response_model=BorrowerResponse)
def block_borrower(
    borrower_id: str,
    reason: str = Query(..., description="Reason for blocking"),
    db: Session = Depends(get_db)
):
    """
    Block a borrower by setting active=False and setting blocked_reason.

    **Query Parameters**:
    - reason: Reason for blocking (required)

    **Errors**:
    - 404: Borrower not found
    """
    borrower = borrower_service.block_borrower(db, borrower_id, reason)
    return borrower


@router.delete("/{borrower_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_borrower(
    borrower_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a borrower and their circulation history.

    Validates that borrower has no active loans before deletion.

    **Errors**:
    - 404: Borrower not found
    - 400: Borrower has active loans (cannot delete)
    """
    # Reuse bulk delete with single ID
    borrower_service.bulk_delete_borrowers(db, [borrower_id])
    return None


