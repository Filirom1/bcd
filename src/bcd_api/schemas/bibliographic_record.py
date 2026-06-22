"""Pydantic schemas for BiblographicRecord model."""

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.bcd_api.schemas.common import TimestampMixin
from src.shared.constants import BindingType, TargetAudience
from src.shared.validators import clean_call_number


class BiblographicRecordBase(BaseModel):
    """Base schema for BiblographicRecord."""

    isbn: Optional[str] = Field(
        None,
        max_length=22,
        description="Identifier with prefix: isbn:NNNN for books, issn:NNNN-NNNX for periodicals",
    )
    title: str = Field(..., min_length=1, max_length=500, description="Title")
    subtitle: Optional[str] = Field(None, max_length=500, description="Subtitle")
    authors: Optional[list[str]] = Field(None, description="List of authors")
    illustrators: Optional[list[str]] = Field(None, description="List of illustrators")
    publisher: Optional[str] = Field(None, max_length=200, description="Publisher")
    publication_year: Optional[int] = Field(None, ge=1000, le=2100, description="Publication year")
    collection: Optional[str] = Field(None, max_length=200, description="Collection/Series")
    series_number: Optional[str] = Field(None, max_length=50, description="Volume number")
    language: Optional[str] = Field(None, max_length=10, description="ISO 639 language code")
    country_code: Optional[str] = Field(None, max_length=5, description="Country code")
    binding_type: Optional[BindingType] = Field(None, description="Binding type")
    level: Optional[str] = Field(None, max_length=50, description="Reading level")
    medium_type: str = Field(
        default="Livre",
        max_length=50,
        description="Medium type (any string: Livre, CD, DVD, Bande dessinée, etc.)",
    )
    target_audience: Optional[TargetAudience] = Field(None, description="Target audience")
    keywords: Optional[list[str]] = Field(None, description="Keywords")
    description: Optional[str] = Field(None, description="Description/summary")
    dewey_number: Optional[str] = Field(
        None, description="Dewey classification number from BnF 676$a"
    )
    page_count: Optional[int] = Field(None, ge=0, description="Number of pages")
    has_illustrations: Optional[bool] = Field(None, description="Has illustrations?")
    dimensions: Optional[str] = Field(None, max_length=50, description="Dimensions")
    physical_size: Optional[str] = Field(
        None, max_length=100, description="Full physical description"
    )
    cover_image: Optional[str] = Field(
        None, max_length=50, description="Local cover filename ({isbn}.jpg)"
    )


class BiblographicRecordCreate(BiblographicRecordBase):
    """Schema for creating a new bibliographic record."""

    @field_validator("isbn", mode="before")
    @classmethod
    def normalize_isbn(cls, v):
        """Ensure isbn/issn are stored with their prefix."""
        if v is None:
            return v
        v = str(v).strip()
        if v.startswith("isbn:") or v.startswith("issn:"):
            return v
        # Strip hyphens/spaces to check length
        digits = v.replace("-", "").replace(" ", "")
        if len(digits) == 8 or "-" in v and v.count("-") >= 2 and len(digits) < 13:
            return f"issn:{v}"
        return f"isbn:{v}"

    @field_validator("dewey_number", mode="before")
    @classmethod
    def clean_dewey(cls, v):
        """Clean dewey number to keep only alphanumeric characters, dots, and spaces."""
        return clean_call_number(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "isbn": "978-2-8006-8734-6",
                "title": "Ils ont arrêté mon père",
                "authors": ["Carmi, Danielle"],
                "publisher": "Flammarion",
                "publication_year": 2004,
                "language": "fr",
                "medium_type": "Livre",
                "target_audience": "child",
            }
        }
    )


class BiblographicRecordUpdate(BaseModel):
    """Schema for updating a bibliographic record."""

    isbn: Optional[str] = Field(None, max_length=22)

    @field_validator("isbn", mode="before")
    @classmethod
    def normalize_isbn(cls, v):
        """Ensure isbn/issn are stored with their prefix."""
        if v is None:
            return v
        v = str(v).strip()
        if v.startswith("isbn:") or v.startswith("issn:"):
            return v
        digits = v.replace("-", "").replace(" ", "")
        if len(digits) == 8 or "-" in v and v.count("-") >= 2 and len(digits) < 13:
            return f"issn:{v}"
        return f"isbn:{v}"

    @field_validator("dewey_number", mode="before")
    @classmethod
    def clean_dewey(cls, v):
        """Clean dewey number to keep only alphanumeric characters, dots, and spaces."""
        return clean_call_number(v)

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    authors: Optional[list[str]] = None
    illustrators: Optional[list[str]] = None
    publisher: Optional[str] = Field(None, max_length=200)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    collection: Optional[str] = Field(None, max_length=200)
    series_number: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    country_code: Optional[str] = Field(None, max_length=5)
    binding_type: Optional[BindingType] = None
    level: Optional[str] = Field(None, max_length=50)
    medium_type: Optional[str] = Field(None, max_length=50)
    target_audience: Optional[TargetAudience] = None
    keywords: Optional[list[str]] = None
    description: Optional[str] = None
    page_count: Optional[int] = Field(None, ge=0)
    has_illustrations: Optional[bool] = None
    dimensions: Optional[str] = Field(None, max_length=50)
    physical_size: Optional[str] = Field(None, max_length=100)
    dewey_number: Optional[str] = None


class BiblographicRecordResponse(BiblographicRecordBase, TimestampMixin):
    """Schema for bibliographic record response."""

    id: int
    total_items: int
    isbn_value: Optional[str] = None
    identifier_type: str = "isbn"

    model_config = ConfigDict(from_attributes=True)

    @field_validator("authors", "illustrators", "keywords", mode="before")
    @classmethod
    def deserialize_json_fields(cls, v):
        """Deserialize JSON string fields to lists."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []


class BiblographicRecordSummary(BaseModel):
    """Summary schema for bibliographic record (for lists)."""

    id: int
    isbn: Optional[str]
    isbn_value: Optional[str] = None
    identifier_type: str = "isbn"
    title: str
    authors: Optional[list[str]]
    publication_year: Optional[int]
    medium_type: str
    total_items: int
    cover_image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("authors", mode="before")
    @classmethod
    def deserialize_authors(cls, v):
        """Deserialize JSON string to list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []


class BiblographicRecordWithAvailability(BiblographicRecordResponse):
    """Bibliographic record with availability information."""

    available_items: int = Field(..., description="Number of available items")
    on_loan_items: int = Field(..., description="Number of items on loan")

    model_config = ConfigDict(from_attributes=True)
