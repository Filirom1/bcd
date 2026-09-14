"""Borrower CSV import service."""

import csv
import io
import logging

from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import NotFoundError, ValidationError
from src.bcd_api.models.borrower import Borrower
from ...services import class_service
from .commands import create_borrower, update_borrower
from .queries import get_borrower_by_id, get_next_available_id

logger = logging.getLogger(__name__)


# Legacy column names accepted by the BCD borrower importer.
_COLUMN_MAPPINGS = {
    "StudentID": "borrower_id",
    "ExternalID": "external_id",
    "FirstName": "first_name",
    "LastName": "last_name",
    "Class": "class_name",
    "BlockReason": "notes",
    "Role": "role",
    "Active": "active",
    "Email": "email",
    "Phone": "phone",
}


def _normalize_row(row: dict) -> dict:
    """Normalize aliases and tolerate a UTF-8 BOM on the first header."""
    normalized = {}
    for key, value in row.items():
        clean_key = (key or "").lstrip("\ufeff").strip()
        normalized[_COLUMN_MAPPINGS.get(clean_key, clean_key)] = value
    return normalized


def _find_by_external_id(db: Session, external_id: str | None) -> Borrower | None:
    """Find a borrower by an optional external identifier."""
    if not external_id:
        return None
    return db.query(Borrower).filter(Borrower.external_id == external_id).first()


def import_borrowers_from_csv(db: Session, csv_text: str) -> dict:
    """Import borrowers from CSV with upsert and reusable internal IDs.

    ``borrower_id`` is optional in the input. When it is blank, BCD assigns the
    smallest available positive numeric ID, just like manual borrower creation.
    ``external_id`` is optional and can identify an existing borrower during an
    update (for example, an identifier supplied by a school information system).
    """
    csv_reader = csv.DictReader(io.StringIO(csv_text))

    created = 0
    updated = 0
    failed = 0
    error_details = []
    total_rows = 0

    for row_num, raw_row in enumerate(csv_reader, start=2):
        total_rows += 1
        row = _normalize_row(raw_row)

        try:
            first_name = (row.get("first_name") or "").strip()
            last_name = (row.get("last_name") or "").strip()
            if not first_name:
                failed += 1
                error_details.append({"row_number": row_num, "error": "Missing required field: first_name"})
                continue
            if not last_name:
                failed += 1
                error_details.append({"row_number": row_num, "error": "Missing required field: last_name"})
                continue

            role = (row.get("role") or "student").strip().lower()
            if role not in {"student", "teacher", "staff"}:
                failed += 1
                error_details.append({
                    "row_number": row_num,
                    "error": f"Invalid role: '{role}' (must be student, teacher, or staff)",
                })
                continue

            class_id = None
            class_name = row.get("class") or row.get("class_name")
            has_class = bool(class_name and class_name.strip())
            if has_class:
                normalized_class = class_name.strip()
                try:
                    class_obj = class_service.get_class_by_name(db, normalized_class)
                    if class_obj:
                        class_id = class_obj.id
                    else:
                        class_id = class_service.create_class(
                            db=db,
                            name=normalized_class,
                            homeroom_teacher=None,
                            notes="Auto-created during borrower import",
                        ).id
                except Exception as exc:
                    logger.warning("Could not create class '%s': %s", class_name, exc)

            has_active = bool(row.get("active"))
            active = True
            if has_active:
                active = str(row["active"]).strip().lower() in (
                    "true", "1", "yes", "oui", "active", "actif"
                )

            blocked_reason = (row.get("blocked_reason") or "").strip() or None
            requested_id = (row.get("borrower_id") or "").strip()
            external_id = (row.get("external_id") or "").strip() or None

            existing = None
            if requested_id:
                try:
                    existing = get_borrower_by_id(db, requested_id)
                except NotFoundError:
                    pass
            if existing is None:
                existing = _find_by_external_id(db, external_id)

            if existing:
                # Preserve the existing BCD ID, especially when matching by external_id.
                existing_borrower_id = getattr(existing, "borrower_id", requested_id)
                update_kwargs = {
                    "db": db,
                    "borrower_id": existing_borrower_id,
                    "external_id": external_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": (row.get("email") or "").strip() or None,
                    "phone": (row.get("phone") or "").strip() or None,
                    "notes": (row.get("notes") or "").strip() or None,
                }
                # Optional fields are only changed when their CSV column has a value.
                if has_class:
                    update_kwargs["class_id"] = class_id
                if has_active:
                    update_kwargs["active"] = active
                if "blocked_reason" in row:
                    update_kwargs["blocked_reason"] = blocked_reason
                update_borrower(**update_kwargs)
                updated += 1
            else:
                borrower_id = requested_id or get_next_available_id(db)
                create_borrower(
                    db=db,
                    borrower_id=borrower_id,
                    external_id=external_id,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    class_id=class_id,
                    email=(row.get("email") or "").strip() or None,
                    phone=(row.get("phone") or "").strip() or None,
                    notes=(row.get("notes") or "").strip() or None,
                    active=active,
                )
                created += 1

        except ValidationError as exc:
            failed += 1
            error_details.append({"row_number": row_num, "error": str(exc.detail)})
        except KeyError as exc:
            failed += 1
            error_details.append({"row_number": row_num, "error": f"Missing required column: {exc}"})
        except Exception as exc:
            failed += 1
            error_details.append({"row_number": row_num, "error": str(exc)})

    return {
        "total_rows": total_rows,
        "successful_rows": created + updated,
        "failed_rows": failed,
        "borrowers_created": created,
        "borrowers_updated": updated,
        "errors": error_details,
    }
