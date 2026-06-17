"""Pydantic schemas for Class model."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.bcd_api.schemas.common import TimestampMixin


class ClassBase(BaseModel):
    """Base schema for Class."""

    name: str = Field(..., min_length=1, max_length=50, description="Class name (e.g., CP-A, CE1-B)")
    homeroom_teacher: Optional[str] = Field(None, max_length=100, description="Homeroom teacher name")
    notes: Optional[str] = Field(None, description="Additional notes")
    average_age: Optional[int] = Field(None, ge=3, le=18, description="Average age of students (used for sorting youngest to oldest)")


class ClassCreate(ClassBase):
    """Schema for creating a new class."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "CP-A",
                "homeroom_teacher": "Mme. Dupont",
                "notes": "Classe de 24 élèves",
            }
        }
    )


class ClassUpdate(BaseModel):
    """Schema for updating a class."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    homeroom_teacher: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    average_age: Optional[int] = Field(None, ge=3, le=18)


class ClassResponse(ClassBase, TimestampMixin):
    """Schema for class response."""

    id: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "CP-A",
                "homeroom_teacher": "Mme. Dupont",
                "notes": "Classe de 24 élèves",
                "average_age": 6,
                "created_at": "2026-01-30T10:00:00",
                "updated_at": "2026-01-30T10:00:00",
            }
        }
    )


class ClassWithBorrowerCount(ClassResponse):
    """Schema for class with borrower count."""

    borrower_count: int = Field(..., description="Number of borrowers in this class")

    model_config = ConfigDict(from_attributes=True)
