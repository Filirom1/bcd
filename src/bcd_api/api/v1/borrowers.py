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
from ...services.export_service import ExportService

router = APIRouter(prefix="/borrowers", tags=["borrowers"])


def _get_borrower_class_info(db: Session, borrower) -> Tuple[Optional[str], Optional[str]]:
    """
    Get class name and homeroom teacher for a borrower.

    Args:
        db: Database session
        borrower: Borrower model instance

    Returns:
        Tuple of (class_name, homeroom_teacher), both can be None
    """
    if not borrower.class_id:
        return None, None

    from ...models import Class
    class_obj = db.query(Class).filter(Class.id == borrower.class_id).first()
    if class_obj:
        return class_obj.name, class_obj.homeroom_teacher
    return None, None


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
    import csv
    import io

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

        csv_reader = csv.DictReader(io.StringIO(csv_text))

        created = 0
        updated = 0
        failed = 0
        error_details = []
        total_rows = 0

        # Column name mappings to support different CSV formats
        column_mappings = {
            'StudentID': 'borrower_id',
            'FirstName': 'first_name',
            'LastName': 'last_name',
            'Class': 'class_name',
            'BlockReason': 'notes',
            'Role': 'role',
            'Active': 'active',
            'Email': 'email',
            'Phone': 'phone'
        }

        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            total_rows += 1

            # Normalize column names (handle both formats)
            normalized_row = {}
            for key, value in row.items():
                # Map old column names to new ones, or keep as-is
                normalized_key = column_mappings.get(key, key)
                normalized_row[normalized_key] = value
            row = normalized_row

            try:
                # Validate required fields
                if not row.get('borrower_id'):
                    failed += 1
                    error_details.append({
                        "row_number": row_num,
                        "error": "Missing required field: borrower_id"
                    })
                    continue

                if not row.get('first_name'):
                    failed += 1
                    error_details.append({
                        "row_number": row_num,
                        "error": "Missing required field: first_name"
                    })
                    continue

                if not row.get('last_name'):
                    failed += 1
                    error_details.append({
                        "row_number": row_num,
                        "error": "Missing required field: last_name"
                    })
                    continue

                # Validate and normalize role
                role = row.get('role', 'student').strip().lower() if row.get('role') else 'student'
                if role not in ['student', 'teacher', 'staff']:
                    failed += 1
                    error_details.append({
                        "row_number": row_num,
                        "error": f"Invalid role: '{role}' (must be student, teacher, or staff)"
                    })
                    continue

                # Get class ID from class name if provided (auto-create if not exists)
                class_id = None
                class_name = row.get('class') or row.get('class_name')
                if class_name and class_name.strip():
                    from ...services import class_service
                    try:
                        # Normalize class name for consistency
                        normalized_class = class_name.strip()
                        class_obj = class_service.get_class_by_name(db, normalized_class)
                        if class_obj:
                            class_id = class_obj.id
                        else:
                            # Auto-discover: Create class if it doesn't exist
                            new_class = class_service.create_class(
                                db=db,
                                name=normalized_class,
                                homeroom_teacher=None,
                                notes="Auto-created during borrower import"
                            )
                            class_id = new_class.id
                            logger.info(f"Auto-created class '{normalized_class}' (ID: {class_id})")
                    except Exception as e:
                        # If class creation fails, log but continue without class assignment
                        logger.warning(f"Could not create class '{class_name}': {e}")
                        pass

                # Parse active status (default to True)
                active = True
                if 'active' in row and row['active']:
                    active_val = str(row['active']).strip().lower()
                    active = active_val in ('true', '1', 'yes', 'oui', 'active', 'actif')

                # Parse blocked status
                blocked_reason = None
                if 'blocked_reason' in row and row['blocked_reason'].strip():
                    blocked_reason = row['blocked_reason'].strip()

                borrower_id_str = row['borrower_id'].strip()

                # UPSERT LOGIC: Try to get existing borrower
                try:
                    existing = borrower_service.get_borrower_by_id(db, borrower_id_str)

                    # Borrower exists - UPDATE
                    borrower_service.update_borrower(
                        db=db,
                        borrower_id=borrower_id_str,
                        first_name=row['first_name'].strip(),
                        last_name=row['last_name'].strip(),
                        class_id=class_id,
                        email=row.get('email', '').strip() if row.get('email') else None,
                        phone=row.get('phone', '').strip() if row.get('phone') else None,
                        notes=row.get('notes', '').strip() if row.get('notes') else None,
                        active=active,
                        blocked_reason=blocked_reason
                    )
                    updated += 1

                except NotFoundError:
                    # Borrower doesn't exist - CREATE
                    borrower_service.create_borrower(
                        db=db,
                        borrower_id=borrower_id_str,
                        first_name=row['first_name'].strip(),
                        last_name=row['last_name'].strip(),
                        role=role,
                        class_id=class_id,
                        email=row.get('email', '').strip() if row.get('email') else None,
                        phone=row.get('phone', '').strip() if row.get('phone') else None,
                        notes=row.get('notes', '').strip() if row.get('notes') else None
                    )
                    created += 1

            except ValidationError as e:
                failed += 1
                error_details.append({
                    "row_number": row_num,
                    "error": str(e.detail)
                })
            except KeyError as e:
                failed += 1
                error_details.append({
                    "row_number": row_num,
                    "error": f"Missing required column: {str(e)}"
                })
            except Exception as e:
                failed += 1
                error_details.append({
                    "row_number": row_num,
                    "error": str(e)
                })

        return {
            "total_rows": total_rows,
            "successful_rows": created + updated,
            "failed_rows": failed,
            "borrowers_created": created,
            "borrowers_updated": updated,
            "errors": error_details
        }

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
        # Create export service
        export_service = ExportService(db)

        # Generate CSV
        csv_content, borrower_count = export_service.export_borrowers_to_csv()

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
    from ...services import settings_service

    details = borrower_service.get_borrower_details(db, borrower_id)
    borrower = details["borrower"]

    # Get loan limit based on role from system settings
    settings = settings_service.get_settings(db)
    loan_limit = (
        settings.loan_limit_teacher
        if borrower.role == "teacher"
        else settings.loan_limit_default
    )

    # Get class name and homeroom teacher if borrower has a class
    class_name, homeroom_teacher = _get_borrower_class_info(db, borrower)

    borrower_detailed = BorrowerDetailed(
        **borrower.__dict__,
        barcode=borrower.barcode,  # Computed property not in __dict__
        current_loans_count=details["current_loans_count"],
        total_checkouts=details["total_checkouts"],
        overdue_count=details["overdue_count"],
        loan_limit=loan_limit,
        class_name=class_name,
        homeroom_teacher=homeroom_teacher,
    )

    # If detail requested, include current loans only.
    # Full paginated history is available via GET /circulation/borrower/{id}/history
    if detail:
        from ...services import circulation_service
        current_loans = circulation_service.get_borrower_current_loans(db, borrower_id)

        return {
            **borrower_detailed.model_dump(mode='json'),
            "current_loans": current_loans,
        }

    return borrower_detailed


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
    from ...services import settings_service

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
    enriched_borrowers = []

    for borrower in borrowers:
        # Get current loans count
        current_loans_count = db.query(CirculationTransaction).filter(
            and_(
                CirculationTransaction.borrower_id == borrower.id,
                CirculationTransaction.return_date.is_(None)
            )
        ).count()

        # Get overdue count
        overdue_count = db.query(CirculationTransaction).filter(
            and_(
                CirculationTransaction.borrower_id == borrower.id,
                CirculationTransaction.return_date.is_(None),
                CirculationTransaction.due_date < date.today()
            )
        ).count()

        # Determine loan limit based on role
        loan_limit = (
            settings.loan_limit_teacher
            if borrower.role in ("teacher", "staff")
            else settings.loan_limit_default
        )

        # Get class name and homeroom teacher if borrower has a class
        class_name, homeroom_teacher = _get_borrower_class_info(db, borrower)

        # Add attributes to borrower object
        borrower.current_loans_count = current_loans_count
        borrower.loan_limit = loan_limit
        borrower.overdue_count = overdue_count
        borrower.class_name = class_name
        borrower.homeroom_teacher = homeroom_teacher

        enriched_borrowers.append(borrower)

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


