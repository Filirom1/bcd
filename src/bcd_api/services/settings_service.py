"""
Settings Service

Business logic for managing system settings.
"""

import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.system_settings import SystemSettings
from ..core.exceptions import NotFoundError

DEFAULT_SHELF_LOCATIONS = json.dumps([
    {"label": "Romans",           "color": "#c0392b"},
    {"label": "Albums",           "color": "#e67e22"},
    {"label": "Bandes dessinées", "color": "#2980b9"},
    {"label": "Documentaires",    "color": "#27ae60"},
    {"label": "Périodiques",      "color": "#16a085"},
    {"label": "Contes",           "color": "#f39c12"},
    {"label": "Poésie",           "color": "#8e44ad"},
])


def initialize_default_settings(db: Session) -> SystemSettings:
    """
    Create default system settings if they don't exist.

    Args:
        db: Database session

    Returns:
        SystemSettings object (existing or newly created)
    """
    # Check if settings already exist
    settings = db.query(SystemSettings).first()
    if settings:
        return settings

    # Create default settings
    settings = SystemSettings(
        id=1,
        library_name="Bibliothèque que Claude a Développée",
        library_code=None,
        language="fr",
        date_format="DD/MM/YYYY",
        academic_year_current="2025-2026",
        academic_year_start_month=9,
        loan_duration_days=14,
        loan_limit_default=3,
        loan_limit_teacher=10,
        renewal_limit=1,
        hold_expiration_days=7,
        hold_queue_enabled=False,
        max_holds_per_borrower=1,
        barcode_type="code39",
        id_format="numeric",
        id_validation_regex=r"^\d+$",
        id_length_min=4,
        id_length_max=10,
        catalog_shelf_locations=DEFAULT_SHELF_LOCATIONS,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)

    return settings


def get_settings(db: Session) -> SystemSettings:
    """
    Get system settings.

    Args:
        db: Database session

    Returns:
        SystemSettings object

    Raises:
        NotFoundError: If settings not found (should never happen with proper init)
    """
    settings = db.query(SystemSettings).first()
    if not settings:
        raise NotFoundError("SystemSettings", "default")
    return settings


def update_settings(
    db: Session,
    updates: Dict[str, Any],
) -> SystemSettings:
    """
    Update system settings.

    Args:
        db: Database session
        updates: Dictionary of setting key-value pairs to update

    Returns:
        Updated SystemSettings object

    Raises:
        NotFoundError: If settings not found
    """
    settings = get_settings(db)

    # Update allowed fields
    allowed_fields = {
        "library_name",
        "library_code",
        "language",
        "date_format",
        "academic_year_current",
        "academic_year_start_month",
        "loan_duration_days",
        "loan_limit_default",
        "loan_limit_teacher",
        "renewal_limit",
        "hold_expiration_days",
        "hold_queue_enabled",
        "max_holds_per_borrower",
        "barcode_type",
        "borrower_barcode_prefix",
        "item_barcode_prefix",
        "id_format",
        "id_validation_regex",
        "id_length_min",
        "id_length_max",
        "catalog_medium_types",
        "catalog_genres",
        "catalog_languages",
        "catalog_levels",
        "inventory_search_result_limit",
        "dewey_colors",
        "catalog_shelf_locations",
    }

    for key, value in updates.items():
        if key in allowed_fields and hasattr(settings, key):
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return settings


def reset_to_defaults(db: Session) -> SystemSettings:
    """
    Reset all settings to default values.

    Args:
        db: Database session

    Returns:
        Reset SystemSettings object
    """
    settings = get_settings(db)

    # Reset to defaults
    settings.library_name = "Bibliothèque que Claude a Développée"
    settings.library_code = None
    settings.language = "fr"
    settings.date_format = "DD/MM/YYYY"
    settings.academic_year_current = "2025-2026"
    settings.academic_year_start_month = 9
    settings.loan_duration_days = 14
    settings.loan_limit_default = 2
    settings.loan_limit_teacher = 5
    settings.renewal_limit = 2
    settings.hold_expiration_days = 3
    settings.hold_queue_enabled = True
    settings.max_holds_per_borrower = 1
    settings.barcode_type = "code39"
    settings.id_format = "numeric"
    settings.id_validation_regex = r"^\d+$"
    settings.id_length_min = 1
    settings.id_length_max = 10

    db.commit()
    db.refresh(settings)

    return settings
