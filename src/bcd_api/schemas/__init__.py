"""Pydantic schemas for BCD library system."""

# Common schemas
# Bibliographic Record schemas
from src.bcd_api.schemas.bibliographic_record import (
    BibliographicRecordCreate,
    BibliographicRecordResponse,
    BibliographicRecordSummary,
    BibliographicRecordUpdate,
    BibliographicRecordWithAvailability,
)

# Borrower schemas
from src.bcd_api.schemas.borrower import (
    BorrowerCreate,
    BorrowerDetailed,
    BorrowerResponse,
    BorrowerSummary,
    BorrowerUpdate,
)

# Circulation schemas
from src.bcd_api.schemas.circulation import (
    CheckoutRequest,
    CheckoutResponse,
    CirculationTransactionResponse,
    CurrentLoanResponse,
    RenewRequest,
    RenewResponse,
    ReturnRequest,
    ReturnResponse,
)

# Class schemas
from src.bcd_api.schemas.class_schema import (
    ClassCreate,
    ClassResponse,
    ClassUpdate,
    ClassWithBorrowerCount,
)
from src.bcd_api.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)

# Hold schemas
from src.bcd_api.schemas.hold import (
    HoldCreate,
    HoldReadyForPickup,
    HoldResponse,
    HoldSummary,
)

# Item schemas
from src.bcd_api.schemas.item import (
    ItemCreate,
    ItemResponse,
    ItemSummary,
    ItemUpdate,
    ItemWithBiblio,
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
    "BibliographicRecordCreate",
    "BibliographicRecordUpdate",
    "BibliographicRecordResponse",
    "BibliographicRecordSummary",
    "BibliographicRecordWithAvailability",
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
