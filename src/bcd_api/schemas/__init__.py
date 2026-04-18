"""Pydantic schemas for BCD library system."""

# Common schemas
from src.bcd_api.schemas.common import (
    PaginationParams,
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
)

# Class schemas
from src.bcd_api.schemas.class_schema import (
    ClassCreate,
    ClassUpdate,
    ClassResponse,
    ClassWithBorrowerCount,
)

# Borrower schemas
from src.bcd_api.schemas.borrower import (
    BorrowerCreate,
    BorrowerUpdate,
    BorrowerResponse,
    BorrowerSummary,
    BorrowerDetailed,
)

# Bibliographic Record schemas
from src.bcd_api.schemas.bibliographic_record import (
    BiblographicRecordCreate,
    BiblographicRecordUpdate,
    BiblographicRecordResponse,
    BiblographicRecordSummary,
    BiblographicRecordWithAvailability,
)

# Item schemas
from src.bcd_api.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemSummary,
    ItemWithBiblio,
)

# Circulation schemas
from src.bcd_api.schemas.circulation import (
    CheckoutRequest,
    CheckoutResponse,
    ReturnRequest,
    ReturnResponse,
    RenewRequest,
    RenewResponse,
    CirculationTransactionResponse,
    CurrentLoanResponse,
)

# Hold schemas
from src.bcd_api.schemas.hold import (
    HoldCreate,
    HoldResponse,
    HoldSummary,
    HoldReadyForPickup,
)

# System Settings schemas
from src.bcd_api.schemas.system_settings import (
    SystemSettingsResponse,
    SystemSettingsUpdate,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    # Class
    "ClassCreate",
    "ClassUpdate",
    "ClassResponse",
    "ClassWithBorrowerCount",
    # Borrower
    "BorrowerCreate",
    "BorrowerUpdate",
    "BorrowerResponse",
    "BorrowerSummary",
    "BorrowerDetailed",
    # Bibliographic Record
    "BiblographicRecordCreate",
    "BiblographicRecordUpdate",
    "BiblographicRecordResponse",
    "BiblographicRecordSummary",
    "BiblographicRecordWithAvailability",
    # Item
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    "ItemSummary",
    "ItemWithBiblio",
    # Circulation
    "CheckoutRequest",
    "CheckoutResponse",
    "ReturnRequest",
    "ReturnResponse",
    "RenewRequest",
    "RenewResponse",
    "CirculationTransactionResponse",
    "CurrentLoanResponse",
    # Hold
    "HoldCreate",
    "HoldResponse",
    "HoldSummary",
    "HoldReadyForPickup",
    # System Settings
    "SystemSettingsResponse",
    "SystemSettingsUpdate",
]
