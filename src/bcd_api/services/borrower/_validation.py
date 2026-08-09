"""Private validation helpers for the borrower domain."""

from typing import Optional
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import InvalidIDFormatException, NotFoundException
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.system_settings import SystemSettings
from src.shared.constants import BorrowerRole
from src.shared.validators import validate_id_format


def validate_role(role: str) -> str:
    """Validate borrower role and return the standard string representation."""
    try:
        role_enum = BorrowerRole(role) if isinstance(role, str) else role
        return role_enum.value
    except ValueError:
        valid_roles = ", ".join([r.value for r in BorrowerRole])
        raise InvalidIDFormatException("role", role, valid_roles)


def validate_borrower_id(
    borrower_id: str,
    settings: Optional[SystemSettings],
) -> None:
    """Validate borrower ID format against system settings."""
    if settings:
        if not validate_id_format(borrower_id, settings.id_validation_regex):
            raise InvalidIDFormatException("borrower_id", borrower_id, settings.id_format)


def require_class(db: Session, class_id: int) -> Class:
    """Verify class exists and return it, raising NotFoundException otherwise."""
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise NotFoundException("Class", class_id)
    return class_obj


def full_name(first_name: str, last_name: str) -> str:
    """Generate standardized full name."""
    return f"{first_name} {last_name}"
