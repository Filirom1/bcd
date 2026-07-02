"""Pydantic schemas for Borrower model."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.bcd_api.schemas.common import TimestampMixin
from src.shared.constants import BorrowerRole


class BorrowerBase(BaseModel):
    """Base schema for Borrower."""

    borrower_id: str = Field(..., min_length=1, max_length=20, description="Unique borrower ID")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    role: BorrowerRole = Field(..., description="Borrower role (student/teacher/staff)")
    class_id: Optional[int] = Field(None, description="Class ID (for students)")
    grade_level: Optional[str] = Field(None, max_length=20, description="Grade level")
    email: Optional[str] = Field(None, max_length=100, description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    notes: Optional[str] = Field(None, description="Additional notes")


class BorrowerCreate(BorrowerBase):
    """Schema for creating a new borrower."""

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v):
        """Validate and convert role to enum."""
        if isinstance(v, str):
            return BorrowerRole(v)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "borrower_id": "101",
                "first_name": "Amira",
                "last_name": "BENALI",
                "role": "student",
                "class_id": 1,
                "grade_level": "CP",
            }
        }
    )


class BorrowerUpdate(BaseModel):
    """Schema for updating a borrower."""

    borrower_id: Optional[str] = Field(None, min_length=1, max_length=20, description="New borrower ID")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[BorrowerRole] = None
    class_id: Optional[int] = None
    grade_level: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    active: Optional[bool] = None
    blocked_reason: Optional[str] = Field(None, max_length=200)

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v):
        """Validate and convert role to enum."""
        if v is None:
            return None
        if isinstance(v, str):
            return BorrowerRole(v)
        return v


class BorrowerResponse(BorrowerBase, TimestampMixin):
    """Schema for borrower response."""

    id: int
    full_name: str
    barcode: str
    active: bool
    blocked_reason: Optional[str]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "borrower_id": "101",
                "first_name": "Amira",
                "last_name": "BENALI",
                "full_name": "Amira BENALI",
                "role": "student",
                "class_id": 1,
                "grade_level": "CP",
                "barcode": "%101",
                "active": True,
                "blocked_reason": None,
                "created_at": "2026-01-30T10:00:00",
                "updated_at": "2026-01-30T10:00:00",
            }
        }
    )


class BorrowerSummary(BaseModel):
    """Summary schema for borrower (for lists)."""

    id: int
    borrower_id: str
    full_name: str
    role: BorrowerRole
    class_id: Optional[int]
    active: bool
    blocked_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class BorrowerDetailed(BorrowerResponse):
    """Detailed borrower schema with statistics."""

    current_loans_count: int = Field(0, description="Number of items currently on loan")
    total_checkouts: int = Field(0, description="Total number of checkouts (all time)")
    overdue_count: int = Field(0, description="Number of overdue items")
    loan_limit: int = Field(2, description="Maximum number of items that can be borrowed")
    loan_limit_warning: int = Field(1, description="Soft warning threshold for loans")
    class_name: Optional[str] = Field(None, description="Class name (if student)")
    homeroom_teacher: Optional[str] = Field(None, description="Homeroom teacher for the class")

    model_config = ConfigDict(from_attributes=True)
