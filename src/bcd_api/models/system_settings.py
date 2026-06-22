"""SystemSettings model - stores configurable system parameters (singleton table)."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import validates

from src.bcd_api.core.database import Base
from src.shared.constants import (
    ACADEMIC_YEAR_START_MONTH,
    DEFAULT_HOLD_EXPIRATION_DAYS,
    DEFAULT_LOAN_DURATION_DAYS,
    DEFAULT_LOAN_LIMIT,
    DEFAULT_LOAN_LIMIT_TEACHER,
    DEFAULT_RENEWAL_LIMIT,
    BarcodeType,
    IDFormat,
    Language,
)


class SystemSettings(Base):
    """Stores configurable system parameters (singleton table - only one row)."""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, nullable=False)

    # ID format configuration
    id_format = Column(String(20), nullable=False, default=IDFormat.NUMERIC.value)
    id_validation_regex = Column(String(200), nullable=False, default=r"^\d{1,6}$")
    id_length_min = Column(Integer, nullable=False, default=1)
    id_length_max = Column(Integer, nullable=False, default=10)

    # Barcode configuration
    barcode_type = Column(String(20), nullable=False, default=BarcodeType.CODE39.value)
    borrower_barcode_prefix = Column(String(10), nullable=False, default="%")
    item_barcode_prefix = Column(String(10), nullable=False, default=".")

    # Circulation policies
    loan_limit_default = Column(Integer, nullable=False, default=DEFAULT_LOAN_LIMIT)
    loan_limit_teacher = Column(Integer, nullable=False, default=DEFAULT_LOAN_LIMIT_TEACHER)
    loan_duration_days = Column(Integer, nullable=False, default=DEFAULT_LOAN_DURATION_DAYS)
    renewal_limit = Column(Integer, nullable=False, default=DEFAULT_RENEWAL_LIMIT)

    # Hold policies
    hold_expiration_days = Column(Integer, nullable=False, default=DEFAULT_HOLD_EXPIRATION_DAYS)
    hold_queue_enabled = Column(Boolean, nullable=False, default=True)
    max_holds_per_borrower = Column(Integer, nullable=False, default=1)

    # Inventory policies
    inventory_search_result_limit = Column(Integer, nullable=False, default=200)

    # Localization
    language = Column(String(5), nullable=False, default=Language.FRENCH.value)
    date_format = Column(String(20), nullable=False, default="DD/MM/YYYY")

    # Academic year
    academic_year_start_month = Column(Integer, nullable=False, default=ACADEMIC_YEAR_START_MONTH)
    academic_year_current = Column(String(9), nullable=False, default="2025-2026")

    # System information
    library_name = Column(String(200), nullable=False, default="Bibliothèque que Claude a Développée")
    library_code = Column(String(50), nullable=True)

    # Catalog vocabulary lists (CSV strings)
    catalog_medium_types = Column(Text, nullable=True, default="Livre, Périodique, Audio, Vidéo, Jeu, Numérique, Autre")
    catalog_languages = Column(Text, nullable=True, default="fr, en, es, de, ar")
    catalog_levels = Column(Text, nullable=True, default="CP, CE1, CE2, CM1, CM2, 6e, 5e, 4e, 3e, Lycée, Adulte")

    # Dewey classification colors (JSON array of 10 hex strings, index = class 0–9)
    dewey_colors = Column(Text, nullable=True, default='["#000000","#9e6633","#f20000","#ff9813","#ffee00","#409d42","#0fafe9","#98238b","#d3d5d4","#ffffff"]')

    # Shelf locations (JSON array of {label, color|null})
    catalog_shelf_locations = Column(Text, nullable=True, default='[{"label":"Romans","color":"#c0392b"},{"label":"Albums","color":"#e67e22"},{"label":"Bandes dessinées","color":"#2980b9"},{"label":"Documentaires","color":"#27ae60"},{"label":"Périodiques","color":"#16a085"},{"label":"Contes","color":"#f39c12"},{"label":"Poésie","color":"#8e44ad"}]')

    # Call number rules (JSON array of {medium_type|null, shelf_location|null, pattern})
    catalog_call_number_rules = Column(Text, nullable=True, default='[{"medium_type":"Périodique","shelf_location":null,"pattern":""},{"medium_type":null,"shelf_location":"Albums","pattern":"A {AUT1}"},{"medium_type":null,"shelf_location":"Romans","pattern":"R {AUT3}"},{"medium_type":null,"shelf_location":"Contes","pattern":"C {AUT1}"},{"medium_type":null,"shelf_location":"Poésie","pattern":"P {AUT1}"},{"medium_type":null,"shelf_location":"Bandes dessinées","pattern":"BD {AUT1}"},{"medium_type":null,"shelf_location":"Documentaires","pattern":"{DEWEY} {AUT3}"},{"medium_type":null,"shelf_location":null,"pattern":"{AUT3}"}]')

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton_settings"),
        CheckConstraint(
            f"id_format IN ('{IDFormat.NUMERIC.value}', '{IDFormat.ALPHANUMERIC.value}')",
            name="check_id_format"
        ),
        CheckConstraint(
            f"barcode_type IN ('{BarcodeType.CODE39.value}', '{BarcodeType.CODE128.value}')",
            name="check_barcode_type"
        ),
        CheckConstraint(
            f"language IN ('{Language.FRENCH.value}', '{Language.ENGLISH.value}')",
            name="check_language"
        ),
        CheckConstraint(
            "loan_limit_default > 0 AND loan_limit_default <= 10",
            name="check_loan_limit_default_range"
        ),
        CheckConstraint(
            "loan_duration_days > 0 AND loan_duration_days <= 365",
            name="check_loan_duration_range"
        ),
        CheckConstraint(
            "academic_year_start_month >= 1 AND academic_year_start_month <= 12",
            name="check_academic_year_start_month"
        ),
    )

    @validates('id')
    def validate_singleton_id(self, key, value):
        """Ensure only one row exists with id=1."""
        if value != 1:
            raise ValueError("SystemSettings must have id=1 (singleton pattern)")
        return value

    def __repr__(self):
        return f"<SystemSettings(id={self.id}, library_name={self.library_name})>"
