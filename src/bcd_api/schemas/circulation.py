"""Pydantic schemas for CirculationTransaction model."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.bcd_api.schemas.common import TimestampMixin
from src.shared.constants import CirculationStatus


class CheckoutRequest(BaseModel):
    """Schema for checkout request."""

    borrower_id: str = Field(..., description="Borrower ID")
    item_ids: list[str] = Field(..., min_length=1, description="List of item IDs to checkout")
    checked_out_by: Optional[str] = Field(None, max_length=100, description="Librarian who performed checkout")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "borrower_id": "101",
                "item_ids": ["785", "787"],
                "checked_out_by": "librarian@school.fr",
            }
        }
    )


class CheckoutResponse(BaseModel):
    """Schema for checkout response."""

    borrower_id: str
    borrower_name: str
    checkout_date: datetime
    due_date: date
    items_checked_out: int
    transactions: list[dict] = Field(..., description="Created transactions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "borrower_id": "101",
                "borrower_name": "Amira BENALI",
                "checkout_date": "2026-01-30T10:15:00",
                "due_date": "2026-02-13",
                "items_checked_out": 2,
                "transactions": [
                    {"transaction_id": 1, "item_id": "785", "title": "Ils ont arrêté mon père", "due_date": "2026-02-13"},
                    {"transaction_id": 2, "item_id": "787", "title": "Stuart Little", "due_date": "2026-02-13"},
                ],
            }
        }
    )


class ReturnRequest(BaseModel):
    """Schema for return request."""

    item_ids: list[str] = Field(..., min_length=1, description="List of item IDs to return")
    returned_by: Optional[str] = Field(None, max_length=100, description="Librarian who processed return")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_ids": ["785", "787"],
                "returned_by": "librarian@school.fr",
            }
        }
    )


class ReturnResponse(BaseModel):
    """Schema for return response."""

    items_returned: int
    return_date: datetime
    items: list[dict] = Field(..., description="Returned items with details")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items_returned": 2,
                "return_date": "2026-01-30T15:30:00",
                "items": [
                    {
                        "item_id": "785",
                        "title": "Ils ont arrêté mon père",
                        "borrower_id": "101",
                        "borrower_name": "Amira BENALI",
                        "checkout_date": "2026-01-30T10:15:00",
                        "due_date": "2026-02-13",
                        "return_date": "2026-01-30T15:30:00",
                        "was_overdue": False,
                        "days_overdue": 0,
                        "hold_ready": {
                            "borrower_id": "205",
                            "borrower_name": "Sophie MARTIN",
                            "class_name": "CE2-A",
                            "expiration_date": "2026-02-02"
                        }
                    },
                    {
                        "item_id": "787",
                        "title": "Stuart Little",
                        "borrower_id": "102",
                        "borrower_name": "Lucas DUBOIS",
                        "checkout_date": "2026-01-20T10:00:00",
                        "due_date": "2026-01-27",
                        "return_date": "2026-01-30T15:30:00",
                        "was_overdue": True,
                        "days_overdue": 3,
                        "hold_ready": None
                    }
                ]
            }
        }
    )


class RenewRequest(BaseModel):
    """Schema for renew request."""

    borrower_id: str = Field(..., description="Borrower ID")
    item_ids: Optional[list[str]] = Field(None, description="Item IDs to renew (if None, renew all eligible)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "borrower_id": "101",
                "item_ids": ["785"],
            }
        }
    )


class RenewResponse(BaseModel):
    """Schema for renew response."""

    borrower_id: str
    renewed_count: int
    failed_count: int
    renewed: list[dict] = Field(..., description="Renewed items")
    failed: list[dict] = Field(..., description="Items that could not be renewed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "borrower_id": "101",
                "renewed_count": 1,
                "failed_count": 1,
                "renewed": [
                    {
                        "item_id": "785",
                        "title": "Ils ont arrêté mon père",
                        "old_due_date": "2026-02-13",
                        "new_due_date": "2026-02-27",
                        "renewals_used": 1,
                        "renewals_remaining": 1
                    }
                ],
                "failed": [
                    {
                        "item_id": "787",
                        "reason": "Hold pending"
                    }
                ],
            }
        }
    )


class CirculationTransactionResponse(TimestampMixin):
    """Schema for circulation transaction response."""

    id: int
    borrower_id: int
    item_id: int
    bibliographic_record_id: int
    checkout_date: datetime
    due_date: date
    return_date: Optional[datetime]
    status: CirculationStatus
    renewal_count: int
    is_overdue: bool
    days_overdue: int

    model_config = ConfigDict(from_attributes=True)


class CurrentLoanResponse(BaseModel):
    """Schema for current loan information."""

    item_id: str
    title: str
    authors: Optional[list[str]]
    call_number: Optional[str]
    checkout_date: datetime
    due_date: date
    renewal_count: int
    is_overdue: bool
    days_overdue: int
    can_renew: bool
    cover_image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """Pagination metadata for paginated responses."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


class BorrowerHistoryItem(BaseModel):
    """A single completed loan in a borrower's history."""

    item_id: str
    bibliographic_record_id: int
    title: str
    checkout_date: datetime
    due_date: date
    return_date: datetime
    was_overdue: bool


class BorrowerHistoryResponse(BaseModel):
    """Paginated response for borrower circulation history."""

    borrower_id: str
    borrower_name: str
    history: list[BorrowerHistoryItem]
    pagination: PaginationMeta


class ItemHistoryItem(BaseModel):
    """A single loan entry in an item's history."""

    borrower_id: str
    borrower_name: str
    checkout_date: datetime
    due_date: date
    return_date: Optional[datetime]
    was_overdue: bool
    status: str


class ItemHistoryResponse(BaseModel):
    """Paginated response for item circulation history."""

    item_id: str
    title: str
    current_loan: Optional[ItemHistoryItem]
    history: list[ItemHistoryItem]
    pagination: PaginationMeta
