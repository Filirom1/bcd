"""Pydantic schemas for Item model."""

from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from src.shared.constants import ItemStatus, ItemCondition
from src.bcd_api.schemas.common import TimestampMixin


class ItemBase(BaseModel):
    """Base schema for Item."""

    item_id: str = Field(..., min_length=1, max_length=20, description="Unique item ID")
    bibliographic_record_id: int = Field(..., description="Bibliographic record ID")
    call_number: Optional[str] = Field(None, max_length=50, description="Call number (Dewey/CDU)")
    shelf_location: Optional[str] = Field(None, max_length=100, description="Physical shelf location")
    condition: ItemCondition = Field(ItemCondition.GOOD, description="Physical condition")
    status: ItemStatus = Field(ItemStatus.AVAILABLE, description="Availability status")
    loanable: bool = Field(True, description="Can be borrowed?")
    acquisition_date: Optional[date] = Field(None, description="Acquisition date")
    funding_source: Optional[str] = Field(None, max_length=100, description="Funding source")


class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_id": "785",
                "bibliographic_record_id": 1,
                "call_number": "800.000",
                "shelf_location": "Fiction - Section A - Row 3",
                "loanable": True,
                "acquisition_date": "2024-09-15",
                "funding_source": "Budget 2024-2025",
            }
        }
    )


class ItemUpdate(BaseModel):
    """Schema for updating an item."""

    call_number: Optional[str] = Field(None, max_length=50)
    shelf_location: Optional[str] = Field(None, max_length=100)
    condition: Optional[ItemCondition] = None
    status: Optional[ItemStatus] = None
    loanable: Optional[bool] = None
    acquisition_date: Optional[date] = None
    funding_source: Optional[str] = Field(None, max_length=100)


class ItemResponse(ItemBase, TimestampMixin):
    """Schema for item response."""

    id: int
    barcode: str
    last_borrowed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ItemSummary(BaseModel):
    """Summary schema for item (for lists)."""

    id: int
    item_id: str
    barcode: str
    call_number: Optional[str]
    status: ItemStatus
    condition: ItemCondition
    loanable: bool

    model_config = ConfigDict(from_attributes=True)


class ItemWithBiblio(ItemResponse):
    """Item with bibliographic record information."""

    title: str = Field(..., description="Title from bibliographic record")
    authors: Optional[list[str]] = Field(None, description="Authors")

    model_config = ConfigDict(from_attributes=True)


class CurrentLoanInfo(BaseModel):
    """Current loan information for an item."""

    borrower_id: str
    borrower_name: str
    due_date: str  # Formatted date string
    is_overdue: bool
    days_overdue: int


class ItemWithCurrentLoan(BaseModel):
    """Item with current loan information (for catalog display)."""

    id: int  # Database ID needed for editing
    item_id: str
    call_number: Optional[str]
    shelf_location: Optional[str]
    status: ItemStatus
    condition: ItemCondition
    loanable: bool
    acquisition_date: Optional[date] = None
    funding_source: Optional[str] = None
    current_loan: Optional[CurrentLoanInfo] = None

    model_config = ConfigDict(from_attributes=True)


class AvailableIDsResponse(BaseModel):
    """Response schema for available item IDs endpoint."""

    start_id: str = Field(..., description="First ID in the generated range")
    end_id: str = Field(..., description="Last ID in the generated range")
    ids: list[str] = Field(..., description="List of available item IDs")
    count: int = Field(..., description="Number of IDs generated")
    id_format: str = Field(..., description="ID format (numeric or alphanumeric)")
    contiguous: bool = Field(True, description="Whether IDs form a gapless block")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_id": "2000",
                "end_id": "2029",
                "ids": ["2000", "2001", "2002"],
                "count": 30,
                "id_format": "numeric",
                "contiguous": True
            }
        }
    )
