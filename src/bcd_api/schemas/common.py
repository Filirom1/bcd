"""Common Pydantic schemas used across the application."""

from datetime import datetime
from typing import Optional, TypeVar, Generic
from pydantic import BaseModel, ConfigDict


class PaginationParams(BaseModel):
    """Pagination parameters for list queries."""

    limit: int = 50
    offset: int = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "limit": 50,
                "offset": 0,
            }
        }
    )


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for created_at and updated_at timestamps."""

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str


class ErrorDetail(BaseModel):
    """Error detail schema."""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error: str
    details: Optional[list[ErrorDetail]] = None
