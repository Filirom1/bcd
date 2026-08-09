"""Pydantic schemas for SystemSettings model."""

import json
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.shared.constants import BarcodeType, IDFormat, Language


class ShelfLocationSchema(BaseModel):
    """Schema for a shelf location."""
    label: str
    color: Optional[str] = None


class CallNumberRuleSchema(BaseModel):
    """Schema for a call number rule."""
    medium_type: Optional[str] = None
    shelf_location: Optional[str] = None
    pattern: str


class SystemSettingsResponse(BaseModel):
    """Schema for system settings response."""

    id: int = Field(1, description="Always 1 (singleton)")
    id_format: IDFormat
    id_validation_regex: str
    id_length_min: int
    id_length_max: int
    barcode_type: BarcodeType
    borrower_barcode_prefix: str
    item_barcode_prefix: str
    loan_limit_default: int
    loan_limit_warning: int
    loan_limit_teacher: int
    loan_duration_days: int
    renewal_limit: int
    hold_expiration_days: int
    hold_queue_enabled: bool
    max_holds_per_borrower: int
    language: Language
    date_format: str
    academic_year_start_month: int
    academic_year_current: str
    library_name: str
    library_code: Optional[str]
    catalog_medium_types: Optional[str] = None
    catalog_genres: Optional[str] = None
    catalog_languages: Optional[str] = None
    catalog_levels: Optional[str] = None
    inventory_search_result_limit: int = 200
    dewey_colors: Optional[List[str]] = None
    catalog_shelf_locations: Optional[List[ShelfLocationSchema]] = None
    catalog_call_number_rules: Optional[List[CallNumberRuleSchema]] = None

    @field_validator("dewey_colors", mode="before")
    @classmethod
    def parse_dewey_colors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("catalog_shelf_locations", mode="before")
    @classmethod
    def parse_shelf_locations(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("catalog_call_number_rules", mode="before")
    @classmethod
    def parse_call_number_rules(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "id_format": "numeric",
                "id_validation_regex": "^\\d+$",
                "id_length_min": 1,
                "id_length_max": 10,
                "barcode_type": "code39",
                "borrower_barcode_prefix": "%",
                "item_barcode_prefix": ".",
                "loan_limit_default": 2,
                "loan_limit_warning": 1,
                "loan_limit_teacher": 5,
                "loan_duration_days": 14,
                "renewal_limit": 2,
                "hold_expiration_days": 3,
                "hold_queue_enabled": True,
                "language": "fr",
                "date_format": "DD/MM/YYYY",
                "academic_year_start_month": 9,
                "academic_year_current": "2025-2026",
                "library_name": "BCD École Primaire",
                "library_code": "EPH-BCD-001",
            }
        }
    )


class SystemSettingsUpdate(BaseModel):
    """Schema for updating system settings."""

    id_format: Optional[IDFormat] = None
    id_validation_regex: Optional[str] = Field(None, max_length=200)
    id_length_min: Optional[int] = Field(None, ge=1)
    id_length_max: Optional[int] = Field(None, ge=1, le=50)
    barcode_type: Optional[BarcodeType] = None
    borrower_barcode_prefix: Optional[str] = Field(None, max_length=10)
    item_barcode_prefix: Optional[str] = Field(None, max_length=10)
    loan_limit_default: Optional[int] = Field(None, ge=1, le=10)
    loan_limit_warning: Optional[int] = Field(None, ge=0, le=10)
    loan_limit_teacher: Optional[int] = Field(None, ge=1, le=20)
    loan_duration_days: Optional[int] = Field(None, ge=1, le=365)
    renewal_limit: Optional[int] = Field(None, ge=0, le=10)
    hold_expiration_days: Optional[int] = Field(None, ge=1, le=30)
    hold_queue_enabled: Optional[bool] = None
    max_holds_per_borrower: Optional[int] = Field(None, ge=1, le=10)
    language: Optional[Language] = None
    date_format: Optional[str] = Field(None, max_length=20)
    academic_year_start_month: Optional[int] = Field(None, ge=1, le=12)
    academic_year_current: Optional[str] = Field(None, pattern=r"^\d{4}-\d{4}$")
    library_name: Optional[str] = Field(None, max_length=200)
    library_code: Optional[str] = Field(None, max_length=50)
    catalog_medium_types: Optional[str] = None
    catalog_genres: Optional[str] = None
    catalog_languages: Optional[str] = None
    catalog_levels: Optional[str] = None
    inventory_search_result_limit: Optional[int] = Field(None, ge=1, le=1000)
    dewey_colors: Optional[List[str]] = None
    catalog_shelf_locations: Optional[List[ShelfLocationSchema]] = None
    catalog_call_number_rules: Optional[List[CallNumberRuleSchema]] = None
