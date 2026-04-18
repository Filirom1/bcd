# BCD Architecture Patterns & Best Practices

**Version**: 1.0.0
**Last Updated**: 2026-02-06
**Purpose**: Document proven architectural patterns from the BCD codebase that all future development MUST follow

---

## Overview

This document captures the **exemplary architectural patterns** established in the BCD codebase. All AI-assisted development must follow these patterns to maintain consistency, quality, and constitution compliance.

**Audience**: AI developers (Claude, GitHub Copilot, etc.) working on BCD features
**Authority**: This document complements the project constitution and provides concrete implementation patterns

---

## Table of Contents

1. [Service Layer Architecture](#1-service-layer-architecture)
2. [Database Design Patterns](#2-database-design-patterns)
3. [API Design Patterns](#3-api-design-patterns)
4. [CLI Design Patterns](#4-cli-design-patterns)
5. [Vue 3 Web UI Patterns](#5-vue-3-web-ui-patterns)
6. [Testing Patterns](#6-testing-patterns)
7. [Error Handling Patterns](#7-error-handling-patterns)
8. [Internationalization Patterns](#8-internationalization-patterns)
9. [Cross-Platform Patterns](#9-cross-platform-patterns)
10. [Performance Patterns](#10-performance-patterns)

---

## 1. Service Layer Architecture

### Pattern: Three-Layer Clean Architecture

**✅ FOLLOW THIS PATTERN:**

```
API/CLI/Web (Presentation)
    ↓
Services (Business Logic)
    ↓
Models (Data Access)
```

**Implementation Example:**

```python
# ❌ BAD - Business logic in API route
@router.post("/checkout")
def checkout(borrower_id: str, item_id: str, db: Session = Depends(get_db)):
    # Don't put business logic here!
    borrower = db.query(Borrower).filter(...).first()
    if borrower.active and borrower.current_loans_count < 2:
        # ... more logic
        db.commit()
    return borrower

# ✅ GOOD - Thin API route calls service
@router.post("/checkout")
def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    """Checkout items to a borrower."""
    result = circulation_service.checkout_items(
        db=db,
        borrower_id=request.borrower_id,
        item_ids=request.item_ids
    )
    return result
```

**Service Layer Rules:**

1. **All business logic lives in `src/bcd_api/services/`**
2. **API routes are thin wrappers** that call services and handle HTTP concerns
3. **Services are pure Python functions** - no FastAPI dependencies (except Session)
4. **Services handle transactions** - commit/rollback logic in service layer
5. **Services raise exceptions** - API layer catches and converts to HTTP status codes

**Real Example from Codebase:**

```python
# src/bcd_api/services/circulation_service.py
def checkout_items(
    db: Session,
    borrower_id: str,
    item_ids: list[str],
    transaction_date: Optional[date] = None
) -> CheckoutResult:
    """
    Checkout multiple items to a borrower.

    This is business logic, not HTTP handling.
    """
    # 1. Validate borrower
    borrower = borrower_service.get_borrower_by_id(db, borrower_id)

    # 2. Check limits
    if borrower.current_loans_count >= settings.max_items_per_borrower:
        raise ValidationError("Borrower at loan limit")

    # 3. Process each item
    # ... business logic

    # 4. Commit transaction
    db.commit()
    return CheckoutResult(...)
```

### Service Organization Pattern

**File Structure:**

```
src/bcd_api/services/
├── borrower_service.py      # Borrower CRUD + validation
├── catalog_service.py        # Bibliographic records + items
├── circulation_service.py    # Checkout/return/renew
├── class_service.py          # Class management
├── hold_service.py           # Hold queue management
├── report_service.py         # Statistics + reports
├── settings_service.py       # System configuration
├── backup_service.py         # Backup/restore
├── import_service.py         # CSV import
└── bnf_service.py            # External API (BNF)
```

**Rules:**
- One service file per domain entity or functional area
- Services can call other services (e.g., `circulation_service` calls `borrower_service`)
- No circular dependencies between services

---

## 2. Database Design Patterns

### Pattern: Comprehensive Indexing

**✅ FOLLOW THIS PATTERN:**

Index every field that will be used in:
- WHERE clauses (filtering)
- JOIN conditions (foreign keys)
- ORDER BY clauses (sorting)
- Frequent lookups (barcodes, IDs)

**Implementation Example:**

```python
# ❌ BAD - Missing indexes on lookup fields
class Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True)
    item_id = Column(String(20), nullable=False, unique=True)  # ❌ No index!
    status = Column(String(20), nullable=False)                # ❌ No index!
    bibliographic_record_id = Column(Integer, ForeignKey(...)) # ❌ No index!

# ✅ GOOD - All lookup fields indexed
class Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(String(20), nullable=False, unique=True, index=True)  # ✅ Barcode lookup
    status = Column(String(20), nullable=False, index=True)                # ✅ Filter by status
    bibliographic_record_id = Column(
        Integer,
        ForeignKey("bibliographic_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # ✅ JOIN performance
    )
```

**Real Example - Circulation Model (All Critical Fields Indexed):**

```python
class Circulation(Base):
    id = Column(Integer, primary_key=True, index=True)
    borrower_id = Column(Integer, ForeignKey(...), index=True)      # Lookup by borrower
    item_id = Column(Integer, ForeignKey(...), index=True)          # Lookup by item
    librarian_id = Column(Integer, ForeignKey(...), index=True)     # Reports by librarian
    checkout_date = Column(DateTime, nullable=False, index=True)    # Date range queries
    due_date = Column(Date, nullable=False, index=True)             # Overdue reports
    status = Column(String(20), nullable=False, index=True)         # Filter active loans
```

**Indexing Checklist:**
- ✅ Primary keys (`id`)
- ✅ Foreign keys (all `*_id` columns)
- ✅ Unique identifiers (barcodes, ISBNs)
- ✅ Status/state fields (for filtering)
- ✅ Date fields (for range queries)
- ✅ Name fields (for search/sorting)

### Pattern: Timezone-Aware Timestamps

**✅ FOLLOW THIS PATTERN:**

Always use UTC for timestamps with timezone awareness.

```python
# ❌ BAD - Naive datetime (deprecated)
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# ✅ GOOD - Timezone-aware UTC
from datetime import datetime, timezone
created_at = Column(
    DateTime,
    default=lambda: datetime.now(timezone.utc),
    nullable=False
)
updated_at = Column(
    DateTime,
    default=lambda: datetime.now(timezone.utc),
    onupdate=lambda: datetime.now(timezone.utc),
    nullable=False
)
```

**Why**: Prevents timezone bugs, follows Python 3.12+ best practices, ensures consistent timestamps across deployments.

### Pattern: Denormalized Performance Counters

**✅ FOLLOW THIS PATTERN:**

Store frequently accessed counts directly on parent entities.

```python
class Borrower(Base):
    # ... other fields

    # ✅ Denormalized counter - no JOIN needed to check loan count
    current_loans_count = Column(Integer, nullable=False, default=0)

    # Update this counter in circulation_service when checking out/returning
```

**Benefits:**
- Fast limit checks (no COUNT query needed)
- Enables efficient filtering (e.g., "borrowers with overdue items")
- Critical for legacy hardware performance

**When to Denormalize:**
- Counts used in business logic validation
- Counts displayed in list views
- Timestamp of last activity (e.g., `last_borrowed_at`)

---

## 3. API Design Patterns

### Pattern: Pagination on All List Endpoints

**✅ FOLLOW THIS PATTERN:**

Every endpoint returning a list MUST support pagination.

```python
# ✅ GOOD - Pagination parameters with sensible defaults
@router.get("", response_model=List[ClassResponse])
def list_classes(
    grade_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """List classes with pagination."""
    return class_service.list_classes(
        db=db,
        grade_level=grade_level,
        limit=limit,
        offset=offset
    )
```

**Pagination Rules:**
- Default limit: 100 items
- Maximum limit: 500 items
- Always accept `offset` parameter
- Document pagination in OpenAPI description

**Why**: School may have 5,000+ catalog records or 500+ students. Pagination prevents memory issues and keeps UI responsive.

### Pattern: Pydantic Schema Validation

**✅ FOLLOW THIS PATTERN:**

Define schemas for all request/response models.

```python
# src/bcd_api/schemas/borrower.py

class BorrowerBase(BaseModel):
    """Shared fields for borrower schemas."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(student|teacher|staff)$")

class BorrowerCreate(BorrowerBase):
    """Schema for creating a new borrower."""
    borrower_id: str = Field(..., min_length=1, max_length=20)
    class_id: Optional[int] = None

class BorrowerResponse(BorrowerBase):
    """Schema for borrower in API responses."""
    id: int
    borrower_id: str
    barcode: str
    active: bool
    current_loans_count: int
    created_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy ORM compatibility
```

**Schema Organization:**
- `*Base`: Shared fields
- `*Create`: Request body for POST
- `*Update`: Request body for PATCH/PUT
- `*Response`: Response model with all fields (including computed)

### Pattern: Consistent Error Responses

**✅ FOLLOW THIS PATTERN:**

Use custom exceptions that map to HTTP status codes.

```python
# src/bcd_api/core/exceptions.py
class NotFoundError(Exception):
    """Raised when resource not found (HTTP 404)."""
    pass

class ValidationError(Exception):
    """Raised when validation fails (HTTP 400)."""
    pass

class DuplicateError(Exception):
    """Raised when duplicate resource (HTTP 409)."""
    pass

# Service raises exception
if not borrower:
    raise NotFoundError(f"Borrower {borrower_id} not found")

# API layer catches and converts
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )
```

**Why**: Separates business logic (services) from HTTP concerns (API layer).

---

## 4. CLI Design Patterns

### Pattern: Consistent Flag Naming

**✅ FOLLOW THIS PATTERN:**

Use consistent flag patterns across all commands.

```python
@click.command()
@click.option("--api-url", default="http://localhost:8000",
              help="API server URL", envvar="BCD_API_URL")  # ✅ Consistent
@click.option("--format", type=click.Choice(["table", "json"]),
              default="table", help="Output format")         # ✅ Consistent
def command(api_url: str, format: str):
    pass
```

**Standard Flags:**
- `--api-url`: API server URL (all commands)
- `--format`: Output format choice (all query commands)
- `--verbose` / `-v`: Verbose output
- `--help` / `-h`: Help text (automatic)

**Environment Variables:**
- `BCD_API_URL`: Default API URL (set in shell profile)

### Pattern: Rich Table Output

**✅ FOLLOW THIS PATTERN:**

Use Rich library for table displays with consistent styling.

```python
from rich.table import Table
from ..utils.display import console

# ✅ Consistent table styling
table = Table(title="Borrowers", show_header=True, header_style="bold cyan")
table.add_column("ID", style="cyan")
table.add_column("Name", style="white")
table.add_column("Status", style="green")

for borrower in borrowers:
    status_style = "green" if borrower.active else "red"
    table.add_row(
        borrower.borrower_id,
        borrower.full_name,
        f"[{status_style}]{borrower.status}[/{status_style}]"
    )

console.print(table)
```

**Styling Standards:**
- Table title: descriptive noun
- Header style: `bold cyan`
- ID columns: `cyan`
- Status columns: `green` (active/available), `red` (inactive/unavailable)
- Count columns: `magenta`, right-aligned

---

## 5. Vue 3 Web UI Patterns

### Pattern: Composition API Components

**✅ FOLLOW THIS PATTERN:**

Use Vue 3 Composition API for all components.

```javascript
// ✅ GOOD - Composition API with reactive state
export default {
    name: 'BorrowerList',
    setup() {
        const borrowers = ref([]);
        const loading = ref(false);
        const error = ref(null);

        const loadBorrowers = async () => {
            loading.value = true;
            try {
                const response = await api.get('/api/v1/borrowers');
                borrowers.value = response.data;
            } catch (err) {
                error.value = err.message;
            } finally {
                loading.value = false;
            }
        };

        onMounted(() => {
            loadBorrowers();
        });

        return { borrowers, loading, error, loadBorrowers };
    }
};
```

**Component Structure:**
```
src/bcd_web_vue/js/components/
├── borrowers/
│   ├── BorrowerList.js
│   ├── BorrowerDetail.js
│   └── BorrowerActions.js
├── catalog/
│   ├── SearchBar.js
│   └── CatalogImport.js
├── circulation/
│   ├── CheckoutPage.js
│   ├── BorrowerScanner.js
│   └── ItemScanner.js
└── ui/
    ├── Toast.js
    ├── Modal.js
    └── Pagination.js
```

**Organization Rules:**
- One component per file
- Group by domain (borrowers, catalog, circulation)
- Shared UI components in `ui/` directory
- Component names in PascalCase

### Pattern: Barcode Scanner Support

**✅ FOLLOW THIS PATTERN:**

All input fields must support Enter key submission (barcode scanners emit Enter).

```javascript
// ✅ GOOD - Submit on Enter (@submit.prevent)
<form @submit.prevent="scanItem">
    <input
        ref="barcodeInput"
        v-model="barcode"
        type="text"
        placeholder="Scan or type barcode"
        autofocus
    />
</form>

const scanItem = async () => {
    if (!barcode.value) return;

    await processItem(barcode.value);

    // ✅ Critical: Clear input and refocus for next scan
    barcode.value = '';
    nextTick(() => {
        barcodeInput.value.focus();
    });
};
```

**Barcode Scanner Rules:**
- Use `@submit.prevent` to handle Enter key
- Clear input after processing
- Auto-focus input for next scan
- No mouse clicks required between scans

### Pattern: Bootstrap 5 Consistent Styling

**✅ FOLLOW THIS PATTERN:**

Use Bootstrap 5 utility classes consistently.

```javascript
// ✅ Status badges with consistent colors
const getStatusBadge = (status) => {
    const badges = {
        'available': 'badge bg-success',      // Green
        'on_loan': 'badge bg-warning',        // Amber
        'overdue': 'badge bg-danger',         // Red
        'lost': 'badge bg-secondary'          // Gray
    };
    return badges[status] || 'badge bg-secondary';
};

// ✅ Button sizing
<button class="btn btn-lg btn-primary">Checkout</button>  // Primary actions
<button class="btn btn-primary">Save</button>            // Secondary actions
<button class="btn btn-sm btn-outline-primary">Filter</button> // Tertiary
```

**Color Standards:**
- Primary: `#4A90E2` (warm blue) - navigation, primary buttons
- Success/Available: `#28A745` (green) - availability badges
- Warning/On-Loan: `#FFC107` (amber) - warning alerts
- Danger/Overdue: `#DC3545` (red) - error alerts
- Neutral: `#F8F9FA` (light gray) - card backgrounds

---

## 6. Testing Patterns

### Pattern: AAA Test Structure

**✅ FOLLOW THIS PATTERN:**

All tests must follow Arrange-Act-Assert pattern.

```python
def test_create_borrower_success(db_session):
    """Test successful borrower creation."""

    # ARRANGE - Set up test data
    settings = SystemSettings(
        id=1,
        id_format="numeric",
        id_validation_regex=r"^\d+$"
    )
    db_session.add(settings)
    db_session.commit()

    # ACT - Execute the function under test
    borrower = borrower_service.create_borrower(
        db=db_session,
        borrower_id="101",
        first_name="Amira",
        last_name="BENALI",
        role="student"
    )

    # ASSERT - Verify expected outcomes
    assert borrower.borrower_id == "101"
    assert borrower.first_name == "Amira"
    assert borrower.last_name == "BENALI"
    assert borrower.full_name == "Amira BENALI"
    assert borrower.active is True
```

**Test Naming Convention:**

```python
def test_<action>_<condition>_<expected_result>():
    """Test description in plain English."""
    pass

# Examples:
test_create_borrower_success()
test_create_borrower_duplicate_id()
test_checkout_item_when_borrower_at_limit()
test_return_item_calculates_overdue_days()
```

### Pattern: Service-Layer Integration Tests

**✅ FOLLOW THIS PATTERN:**

Test business logic at the service layer, not through HTTP.

```python
# ✅ GOOD - Service-layer test
def test_checkout_respects_loan_limit(db_session):
    """Test that checkout enforces max items per borrower."""
    # Setup: borrower with 2/2 items checked out
    borrower = create_test_borrower(db_session, borrower_id="101")
    checkout_items(db_session, borrower_id="101", item_ids=["ITEM1", "ITEM2"])

    # Act: attempt to checkout 3rd item
    with pytest.raises(ValidationError) as exc:
        checkout_items(db_session, borrower_id="101", item_ids=["ITEM3"])

    # Assert: error message is clear
    assert "loan limit" in str(exc.value).lower()
```

**Why Service-Layer Tests:**
- Faster (no HTTP overhead)
- Easier to set up (direct database access)
- Test business logic, not HTTP serialization
- Achieve 80%+ coverage efficiently

### Pattern: Test Organization

```
tests/
├── unit/                      # Fast, isolated tests
│   ├── test_models.py
│   └── services/
│       ├── test_borrower_service_unit.py
│       └── test_circulation_service_unit.py
├── integration/               # Database tests
│   ├── services/
│   │   ├── test_catalog_service.py
│   │   └── test_circulation_service.py
│   └── test_catalog_api.py
├── api/                       # API endpoint tests
│   └── test_admin_backup_endpoints.py
├── cli/                       # CLI command tests
│   └── test_admin_backup_commands.py
└── e2e/                       # End-to-end (slow, excluded from git hooks)
    └── test_complete_workflows.py
```

**Test Execution Order** (pre-commit hook):
1. Unit tests (fastest)
2. Integration tests
3. API tests
4. CLI tests (excluding E2E)

E2E tests excluded from git hooks for speed - run manually before releases.

---

## 7. Error Handling Patterns

### Pattern: Structured Exception Hierarchy with Error Codes

**✅ FOLLOW THIS PATTERN:**

The BCD codebase uses a sophisticated exception system with structured error codes and context data for i18n support.

**Exception Architecture:**

```python
# src/bcd_api/core/exceptions.py

class BCDException(HTTPException):
    """Base exception with error_code and context support."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or "UNKNOWN_ERROR"  # ✅ Structured error code
        self.context = context or {}  # ✅ Structured data for frontend


# Base exception categories
class NotFoundException(BCDException):
    """Resource not found (HTTP 404)."""
    pass

class ValidationError(BCDException):
    """Validation failed (HTTP 422)."""
    pass

class ConflictError(BCDException):
    """Conflict/duplicate (HTTP 409)."""
    pass

class BusinessRuleViolation(BCDException):
    """Business rule violated (HTTP 400)."""
    pass
```

**Specific Domain Exceptions (17+ specialized exceptions):**

```python
# ✅ EXCELLENT - Specific exception with error_code and context
class LoanLimitExceededException(BusinessRuleViolation):
    """Borrower has exceeded loan limit."""

    def __init__(self, borrower_id: str, current_count: int, limit: int, additional: int = 1):
        detail = f"Borrower has {current_count} items checked out. Limit is {limit}. Cannot check out {additional} more items."
        context = {
            "borrower_id": borrower_id,
            "current": current_count,
            "limit": limit,
            "additional": additional
        }
        super().__init__(detail)
        self.error_code = "LOAN_LIMIT_EXCEEDED"  # ✅ For frontend i18n
        self.context = context  # ✅ Variables for translation


class BorrowerBlockedException(BusinessRuleViolation):
    """Borrower is blocked."""

    def __init__(self, borrower_id: str, reason: str):
        detail = f"Borrower {borrower_id} is blocked: {reason}"
        context = {"borrower_id": borrower_id, "reason": reason}
        super().__init__(detail)
        self.error_code = "BORROWER_BLOCKED"
        self.context = context


class ItemAlreadyOnLoanException(ConflictError):
    """Item is already checked out."""

    def __init__(self, item_id: str, borrower_name: str, due_date: str):
        detail = f"Item {item_id} is already on loan to {borrower_name} (due {due_date})"
        context = {
            "item_id": item_id,
            "borrower_name": borrower_name,
            "due_date": str(due_date)
        }
        super().__init__(detail)
        self.error_code = "ITEM_ALREADY_ON_LOAN"
        self.context = context
```

**Usage in Services:**

```python
# ✅ GOOD - Raise specific exception with structured data
def checkout_items(db: Session, borrower_id: str, item_ids: list[str]):
    borrower = get_borrower_by_id(db, borrower_id)

    if borrower.current_loans_count >= settings.max_items_per_borrower:
        raise LoanLimitExceededException(
            borrower_id=borrower_id,
            current_count=borrower.current_loans_count,
            limit=settings.max_items_per_borrower,
            additional=len(item_ids)
        )

    if borrower.blocked:
        raise BorrowerBlockedException(
            borrower_id=borrower_id,
            reason=borrower.blocking_reason
        )
```

**Complete Exception List (from exceptions.py):**

| Exception | Error Code | HTTP Status | Use Case |
|-----------|------------|-------------|----------|
| `BorrowerNotFoundException` | BORROWER_NOT_FOUND | 404 | Borrower ID not found |
| `BorrowerBlockedException` | BORROWER_BLOCKED | 400 | Borrower is blocked |
| `BorrowerHasOverdueItemsException` | BORROWER_HAS_OVERDUE | 400 | Has overdue items |
| `ItemNotFoundException` | ITEM_NOT_FOUND | 404 | Item barcode not found |
| `ItemNotAvailableException` | ITEM_NOT_AVAILABLE | 400 | Item status prevents checkout |
| `ItemNotLoanableException` | ITEM_NOT_LOANABLE | 400 | Item marked as reference |
| `ItemAlreadyOnLoanException` | ITEM_ALREADY_ON_LOAN | 409 | Item checked out to someone |
| `ItemNotOnLoanException` | ITEM_NOT_ON_LOAN | 400 | Cannot return available item |
| `LoanLimitExceededException` | LOAN_LIMIT_EXCEEDED | 400 | Over max items limit |
| `RenewalLimitExceededException` | RENEWAL_LIMIT_EXCEEDED | 400 | Over max renewals limit |
| `NoRenewableItemsException` | NO_RENEWABLE_ITEMS | 400 | No items eligible for renewal |
| `ItemHasHoldsException` | ITEM_HAS_HOLDS | 400 | Item has pending holds |
| `DuplicateISBNException` | DUPLICATE_ISBN | 409 | ISBN already exists |
| `DuplicateBorrowerIDException` | DUPLICATE_BORROWER_ID | 409 | Borrower ID exists |
| `DuplicateItemIDException` | DUPLICATE_ITEM_ID | 409 | Item barcode exists |
| `InvalidIDFormatException` | INVALID_ID_FORMAT | 422 | ID format validation failed |
| `BiblographicRecordNotFoundException` | RECORD_NOT_FOUND | 404 | Catalog record not found |

**Why This Pattern:**
- **Structured error codes**: Enable frontend i18n (errors translated to French)
- **Context data**: Provides variables for translation interpolation
- **Type safety**: Specific exceptions document possible failures
- **Actionable messages**: Include all info librarian needs (counts, limits, names)

---

## 8. Internationalization Patterns

### Pattern: Complete i18n Coverage with Error Code Translation

**✅ FOLLOW THIS PATTERN:**

The BCD codebase uses a sophisticated i18n pattern with parameterized error messages.

**Backend → Frontend Flow:**

1. **Backend** raises exception with `error_code` and `context`
2. **API** returns JSON with `error_code` and `context` fields
3. **Frontend** maps `error_code` to i18n translation key
4. **Frontend** interpolates `context` variables into translated message

**Frontend Error Model:**

```javascript
// src/bcd_web_vue/js/models/error.js

export const ERROR_CODES = {
    // Borrower errors
    BORROWER_NOT_FOUND: 'borrower_not_found',
    BORROWER_BLOCKED: 'borrower_blocked',
    BORROWER_HAS_OVERDUE: 'borrower_has_overdue',

    // Circulation errors
    LOAN_LIMIT_EXCEEDED: 'loan_limit_exceeded',
    RENEWAL_LIMIT_EXCEEDED: 'renewal_limit_exceeded',
    // ... 20+ error codes
};

export class ApiError extends Error {
    constructor(code, message, details = {}, statusCode = 500) {
        super(message);
        this.code = code;  // e.g., "LOAN_LIMIT_EXCEEDED"
        this.details = details;  // e.g., {current: 2, limit: 2, additional: 1}
        this.statusCode = statusCode;
    }

    /**
     * Get translated error message with variable interpolation
     */
    getTranslatedMessage(t) {
        const key = `errors.${this.code}`;  // e.g., "errors.loan_limit_exceeded"
        const translated = t(key, this.details);  // ✅ Vue-i18n with variables

        // Fallback if translation missing
        if (translated === key) {
            return this.message || t('errors.unknown_error');
        }

        return translated;
    }

    /**
     * Parse API response into ApiError
     */
    static async fromResponse(response) {
        const data = await response.json();
        const errorCode = data.error_code
            ? data.error_code.toLowerCase()
            : ERROR_CODES.UNKNOWN_ERROR;

        return new ApiError(
            errorCode,
            data.detail,
            data.context || {},  // ✅ Backend context becomes translation variables
            response.status
        );
    }
}
```

**Locale Files with Parameterized Messages:**

```json
// locales/en.json
{
    "circulation": {
        "checkout": "Checkout",
        "return": "Return",
        "borrower_id": "Borrower ID",
        "item_barcode": "Item Barcode"
    },
    "errors": {
        "loan_limit_exceeded": "Borrower has {current} items checked out. Limit is {limit}. Cannot check out {additional} more item(s).",
        "borrower_blocked": "Borrower {borrower_id} is blocked: {reason}",
        "borrower_has_overdue": "Borrower has {count} overdue item(s). Cannot checkout until overdue items are returned.",
        "item_already_on_loan": "Item {item_id} is already on loan to {borrower_name} (due {due_date})",
        "renewal_limit_exceeded": "Item {item_id} has reached renewal limit ({current_renewals}/{limit})",
        "item_not_available": "Item {item_id} is not available (status: {status})"
    }
}

// locales/fr.json
{
    "circulation": {
        "checkout": "Emprunter",
        "return": "Retourner",
        "borrower_id": "ID Emprunteur",
        "item_barcode": "Code-barres"
    },
    "errors": {
        "loan_limit_exceeded": "L'emprunteur a {current} articles empruntés. La limite est de {limit}. Impossible d'emprunter {additional} article(s) supplémentaire(s).",
        "borrower_blocked": "L'emprunteur {borrower_id} est bloqué: {reason}",
        "borrower_has_overdue": "L'emprunteur a {count} article(s) en retard. Impossible d'emprunter jusqu'au retour des articles en retard.",
        "item_already_on_loan": "L'article {item_id} est déjà emprunté par {borrower_name} (échéance {due_date})",
        "renewal_limit_exceeded": "L'article {item_id} a atteint la limite de renouvellement ({current_renewals}/{limit})",
        "item_not_available": "L'article {item_id} n'est pas disponible (statut: {status})"
    }
}
```

**Usage in Components:**

```javascript
// ❌ BAD - Hard-coded string
<button>Checkout</button>
<div class="error">Item is not available</div>

// ✅ GOOD - i18n with error code translation
<button>{{ t('circulation.checkout') }}</button>

// Handle API error with translation
try {
    await api.post('/circulation/checkout', { borrower_id, item_ids });
} catch (err) {
    if (err instanceof ApiError) {
        // ✅ Translates error code + interpolates variables
        const message = err.getTranslatedMessage(t);
        // Example output (EN): "Borrower has 2 items checked out. Limit is 2. Cannot check out 1 more item(s)."
        // Example output (FR): "L'emprunteur a 2 articles empruntés. La limite est de 2. Impossible d'emprunter 1 article(s) supplémentaire(s)."
        showError(message);
    }
}
```

**i18n Rules:**
- **Backend**: All exceptions include `error_code` and `context` (never hard-code user messages)
- **Frontend**: Map `error_code` to translation key (`errors.{code}`)
- **Locale files**: Use variable placeholders `{variable_name}` for interpolation
- **Hierarchical keys**: Use dot notation (e.g., `circulation.checkout`, `errors.loan_limit_exceeded`)
- **100% parity**: Both en/fr must have identical key structure
- **No hard-coded strings**: All user-facing text externalized

**Current Status:**
- ✅ Web UI: Complete i18n with parameterized error messages (593/594 lines, 16 top-level keys)
- ✅ API: Structured exceptions with error codes and context
- ⚠️ CLI: **Needs i18n** (currently has hard-coded English strings in table columns)

**Why This Pattern:**
- **Backend stays language-agnostic**: Only returns structured data (error_code + context)
- **Frontend controls language**: User selects language, all messages translated
- **Dynamic error messages**: Context variables provide specific details (counts, dates, names)
- **Type-safe error codes**: ERROR_CODES constant prevents typos
- **Librarian-friendly**: Error messages actionable in their native language

---

## 9. Cross-Platform Patterns

### Pattern: Platform-Agnostic Path Handling

**✅ FOLLOW THIS PATTERN:**

Always use `pathlib.Path` for file paths.

```python
# ❌ BAD - Hard-coded path separator
import os
backup_dir = "backups/db"
file_path = backup_dir + "/" + filename  # ❌ Fails on Windows

# ✅ GOOD - pathlib
from pathlib import Path

backup_dir = Path("backups") / "db"
file_path = backup_dir / filename  # ✅ Works on Linux & Windows
```

**Real Example from Backup Service:**

```python
from pathlib import Path

def create_backup(db_path: str, output_dir: str) -> Path:
    """Create database backup."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)  # ✅ Cross-platform

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = output_path / f"bcd_backup_{timestamp}.db"  # ✅ Cross-platform

    shutil.copy2(db_path, backup_file)
    return backup_file
```

**Cross-Platform Checklist:**
- ✅ Use `pathlib.Path` for all file operations
- ✅ Use `Path.mkdir(parents=True, exist_ok=True)` to create directories
- ✅ Use `/` operator for path joining
- ✅ Never hard-code "/" or "\\" in paths
- ✅ Use `Path.home()` for user directory

---

## 10. Performance Patterns

### Pattern: Batch Operations for Imports

**✅ FOLLOW THIS PATTERN (TODO - see F-001):**

Use bulk operations for large dataset imports.

```python
# ❌ BAD - Individual commits (current import_service.py issue)
for row in csv_rows:
    biblio = create_bibliographic_record(db, **row)  # Commits individually
    item = create_item(db, bibliographic_record_id=biblio.id, ...)  # Commits individually
# Result: 5,800 commits for 4,700 rows = 3-5 minutes

# ✅ GOOD - Batch operations (recommended fix)
# Phase 1: Parse and validate
biblio_dicts = []
item_dicts = []
for row in csv_rows:
    biblio_dicts.append(parse_biblio_data(row))
    item_dicts.append(parse_item_data(row))

# Phase 2: Bulk insert
db.bulk_insert_mappings(BiblographicRecord, biblio_dicts)
db.bulk_insert_mappings(Item, item_dicts)
db.commit()  # Single commit
# Result: ~3-5 seconds for 4,700 rows
```

**Batch Operation Rules:**
- Use for CSV imports, data migrations, bulk updates
- Validate all data before bulk insert
- Single transaction for entire batch
- Provide progress feedback for large batches

**Performance Targets (Constitution Principle VI):**
- Common operations: <100ms
- Search queries (5,000 records): <2 seconds
- CSV import (5,000 rows): <5 seconds
- Report generation: <3 seconds

### Pattern: Denormalized Counters

**✅ FOLLOW THIS PATTERN:**

Store frequently accessed counts to avoid expensive COUNT queries.

```python
class Borrower(Base):
    # ✅ Denormalized counter - updated by circulation_service
    current_loans_count = Column(Integer, nullable=False, default=0)

    # Fast limit check (no JOIN or COUNT needed)
    if borrower.current_loans_count >= settings.max_items_per_borrower:
        raise ValidationError("Loan limit reached")
```

**Update Pattern:**

```python
def checkout_items(db: Session, borrower_id: str, item_ids: list[str]):
    # ... checkout logic

    # ✅ Update denormalized counter
    borrower.current_loans_count += len(item_ids)
    db.commit()

def return_items(db: Session, item_ids: list[str]):
    # ... return logic

    # ✅ Decrement denormalized counter
    borrower.current_loans_count -= len(returned_items)
    db.commit()
```

**Why**: Critical for legacy hardware performance. Counting loans with JOINs would be too slow.

---

## Enforcement in `/speckit.review`

This document is **automatically checked** during `/speckit.review`. New code will be validated against these patterns:

### Automated Checks:

1. **Service Layer**: No business logic in API routes
2. **Database**: All foreign keys have indexes
3. **Timestamps**: Use timezone-aware UTC
4. **Pagination**: List endpoints have limit/offset
5. **Paths**: Use pathlib, not hard-coded separators
6. **i18n**: No hard-coded strings in UI/CLI
7. **Tests**: Follow AAA pattern
8. **Errors**: Use specific exception types

### Manual Review Prompts:

- Does new service follow single-responsibility pattern?
- Are barcode scanner workflows keyboard-only?
- Is performance acceptable on legacy hardware?
- Are error messages user-friendly for librarians?

---

## Conclusion

These patterns represent **proven architectural decisions** from the BCD codebase. Following them ensures:

- ✅ Consistency across all features
- ✅ Constitution compliance (all 11 principles)
- ✅ Performance on legacy hardware
- ✅ Maintainability for future developers
- ✅ Quality that passes `/speckit.review` gates

**When in doubt**: Look at existing code in the same domain and follow its pattern.

---

**Document Status**: Active
**Authority**: Complements Project Constitution v1.2.0
**Review**: Update when new patterns emerge from code reviews
