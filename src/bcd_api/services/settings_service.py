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

DEFAULT_CALL_NUMBER_RULES = '[{"medium_type":"Périodique","genre":null,"pattern":""},{"medium_type":null,"genre":"Album","pattern":"A {AUT1}"},{"medium_type":null,"genre":"Roman","pattern":"R {AUT3}"},{"medium_type":null,"genre":"Conte","pattern":"C {AUT1}"},{"medium_type":null,"genre":"Poésie","pattern":"P {AUT1}"},{"medium_type":null,"genre":"Théâtre","pattern":"T {AUT1}"},{"medium_type":null,"genre":"Bande dessinée","pattern":"BD {AUT1}"},{"medium_type":null,"genre":"Manga","pattern":"M {AUT1}"},{"medium_type":null,"genre":"Documentaire","pattern":"{DEWEY} {AUT3}"},{"medium_type":null,"genre":null,"pattern":"{AUT3}"}]'


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
        catalog_call_number_rules=DEFAULT_CALL_NUMBER_RULES,
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
    
    # Backfill default rules if they are missing
    if settings.catalog_call_number_rules is None:
        settings.catalog_call_number_rules = DEFAULT_CALL_NUMBER_RULES
        db.commit()
        db.refresh(settings)

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
        "catalog_call_number_rules",
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
    settings.catalog_medium_types = "Livre, Périodique, Audio, Vidéo, Jeu, Numérique, Autre"
    settings.catalog_genres = "Album, Roman, Conte, Poésie, Théâtre, Bande dessinée, Manga, Documentaire, Autre"
    settings.catalog_call_number_rules = DEFAULT_CALL_NUMBER_RULES

    db.commit()
    db.refresh(settings)

    return settings
