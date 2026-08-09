"""Shared constants for BCD library system."""

from enum import Enum


class BorrowerRole(str, Enum):
    """Borrower role types."""

    STUDENT = "student"
    TEACHER = "teacher"
    STAFF = "staff"


class ItemStatus(str, Enum):
    """Item availability status."""

    AVAILABLE = "available"
    ON_LOAN = "on_loan"
    ON_HOLD = "on_hold"
    IN_REPAIR = "in_repair"
    LOST = "lost"
    WITHDRAWN = "withdrawn"


class ItemCondition(str, Enum):
    """Physical condition of item (not circulation status)."""

    GOOD = "good"
    DAMAGED = "damaged"
    # Note: LOST and WITHDRAWN are circulation statuses, not physical conditions
    # Use ItemStatus.LOST and ItemStatus.WITHDRAWN instead


class MediumType(str, Enum):
    """Type of library material."""

    LIVRE = "Livre"  # Book
    CD = "CD"
    DVD = "DVD"
    FILM = "Film"  # Film/Video
    REVUE = "Revue"  # Magazine/Journal
    MAGAZINE = "Magazine"
    PERIODIQUE = "Périodique"  # Periodical
    LIVRE_CD_ROM = "Livre CD-ROM"  # Book with CD-ROM
    LIVRE_CD = "Livre CD"  # Book with CD
    AUTRE = "Autre"  # Other


class CirculationStatus(str, Enum):
    """Circulation transaction status."""

    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    RENEWED = "renewed"


class HoldStatus(str, Enum):
    """Hold/reservation status."""

    WAITING = "waiting"
    READY = "ready"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TargetAudience(str, Enum):
    """Reading level / target audience."""

    CHILD = "child"
    YOUTH = "youth"
    ADULT = "adult"


class BindingType(str, Enum):
    """Book binding type."""

    HARDCOVER = "hardcover"
    PAPERBACK = "paperback"
    SPIRAL = "spiral"
    OTHER = "other"


class BarcodeType(str, Enum):
    """Barcode symbology."""

    CODE39 = "code39"
    CODE128 = "code128"


class IDFormat(str, Enum):
    """ID format configuration."""

    NUMERIC = "numeric"
    ALPHANUMERIC = "alphanumeric"


class Language(str, Enum):
    """Supported languages."""

    FRENCH = "fr"
    ENGLISH = "en"


# Default configuration values
DEFAULT_LOAN_LIMIT = 2
DEFAULT_LOAN_LIMIT_WARNING = 1
DEFAULT_LOAN_LIMIT_TEACHER = 5
DEFAULT_LOAN_DURATION_DAYS = 14
DEFAULT_RENEWAL_LIMIT = 2
DEFAULT_HOLD_EXPIRATION_DAYS = 15

# Academic year configuration
ACADEMIC_YEAR_START_MONTH = 9  # September

# Pagination defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# API versioning
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# CSV Import/Export configuration
MAX_CATALOG_ROWS = 10000
MAX_BORROWER_ROWS = 5000

# Dublin Core CSV columns (standard field names for catalog import/export)
DUBLIN_CORE_COLUMNS = [
    'dc.title',
    'dc.identifier',
    'dc.creator',
    'dc.contributor',
    'dc.publisher',
    'dc.date',
    'dc.type',
    'dc.format',
    'dc.subject',
    'dc.description',
    'dc.language',
    'dc.coverage',
    'item.id',
    'item.callNumber',
    'item.acquisitionDate',
    'item.fundingSource',
    'dc.rights',
]

# BCD Borrower CSV columns (standard field names for borrower import/export)
BCD_BORROWER_COLUMNS = [
    'borrower_id',
    'first_name',
    'last_name',
    'role',
    'class',
    'barcode',
    'active',
    'blocked',
    'blocked_reason',
]
