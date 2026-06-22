"""Pydantic schemas for Hold model."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.bcd_api.schemas.common import TimestampMixin
from src.shared.constants import HoldStatus


class HoldCreate(BaseModel):
    """Schema for creating a new hold."""

    borrower_id: int = Field(..., description="Borrower database ID")
    bibliographic_record_id: int = Field(..., description="Bibliographic record ID")
    created_by: Optional[str] = Field(None, max_length=100, description="Librarian who placed hold")
    notes: Optional[str] = Field(None, description="Additional notes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "borrower_id": 1,
                "bibliographic_record_id": 1,
                "created_by": "librarian@school.fr",
            }
        }
    )


class HoldResponse(TimestampMixin):
    """Schema for hold response."""

    id: int
    borrower_id: int
    bibliographic_record_id: int
    hold_date: datetime
    queue_position: int
    status: HoldStatus
    available_date: Optional[datetime]
    expiration_date: Optional[date]
    fulfilled_date: Optional[datetime]
    notified: bool
    notification_method: Optional[str]
    created_by: Optional[str]
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class HoldSummary(BaseModel):
    """Summary schema for hold (for lists)."""

    id: int
    borrower_id: int
    borrower_name: str
    bibliographic_record_id: int
    title: str
    queue_position: int
    status: HoldStatus
    hold_date: datetime

    model_config = ConfigDict(from_attributes=True)


class HoldReadyForPickup(BaseModel):
    """Schema for holds ready for pickup."""

    id: int
    borrower_id: int
    borrower_name: str
    class_name: Optional[str]
    title: str
    available_date: datetime
    expiration_date: date
    expires_in_days: int

    model_config = ConfigDict(from_attributes=True)


class HoldWithDetails(HoldResponse):
    """Hold response with borrower and bibliographic record details."""

    borrower_name: Optional[str] = None
    borrower_string_id: Optional[str] = None
    borrower_class: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
