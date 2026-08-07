"""Borrower Import Service

Handles import operations for borrowers from CSV files with validation,
upsert behavior, and auto-class creation.
"""

import csv
import io
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import ValidationError, NotFoundError
from .queries import get_borrower_by_id
from .commands import create_borrower, update_borrower
from ...services import class_service

logger = logging.getLogger(__name__)


def import_borrowers_from_csv(db: Session, csv_text: str) -> dict:
    """
    Import borrowers from CSV text with upsert behavior.

    Expected CSV format: borrower_id, first_name, last_name, role, class (optional)

    **Upsert Behavior**:
    - If borrower_id exists: Update existing borrower
    - If borrower_id is new: Create new borrower

    Returns dictionary with stats and error details.
    """
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
                existing = get_borrower_by_id(db, borrower_id_str)

                # Borrower exists - UPDATE
                update_borrower(
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
                create_borrower(
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
