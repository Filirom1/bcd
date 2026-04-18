# Research: Admin Features Panel

**Feature**: 006-admin-features
**Date**: 2026-02-07
**Status**: Complete

## Executive Summary

This research addresses the 5 critical tasks required for implementing the Admin Features Panel:

1. **Existing Import/Export UI Review**: Documented current button placement on Borrowers and Catalog pages to guide replacement with admin dropdown
2. **Bulk Operation UX Patterns**: Analyzed professional library systems (Koha batch modification tools documented in previous research) for multi-select and confirmation patterns
3. **CASCADE Delete Verification**: Confirmed database schema supports desired CASCADE delete behavior for all admin operations
4. **Progress Indicator Patterns**: Identified reusable progress UI from existing import workflows
5. **Error Codes for Admin Operations**: Defined new error codes following established architecture patterns

**Key Decision**: Use Bootstrap 5 dropdown menu with red `btn-danger` styling for admin menu. Implement atomic transactions for bulk operations with comprehensive rollback on failure. Reuse existing import modal progress indicators.

---

## Research Task 1: Existing Import/Export UI Review

**Objective**: Document current button placement to guide replacement with admin dropdown

### Borrowers Page Current Implementation

**File**: `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/pages/BorrowersPage.js`

**Current Button Locations** (lines 54-77):
```javascript
<!-- Export CSV Button -->
<button
    class="btn btn-outline-secondary me-2"
    @click="handleExport"
    :disabled="exportLoading"
>
    <i class="bi bi-download"></i>
    <span v-if="!exportLoading">{{ t('borrowers.export_button') }}</span>
    <span v-else>
        <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
        {{ t('common.downloading') }}
    </span>
</button>

<!-- Import CSV Button -->
<button
    class="btn btn-primary"
    data-bs-toggle="modal"
    data-bs-target="#borrowerImportModal"
>
    <i class="bi bi-upload"></i>
    {{ t('borrowers.import_csv') }}
</button>
```

**Placement**: Top-right corner of page, next to page title (lines 44-78)

**Styling**:
- Export: `btn btn-outline-secondary` (gray outline)
- Import: `btn btn-primary` (blue solid)
- Icons: Bootstrap Icons (`bi-download`, `bi-upload`)
- Spacing: `me-2` (margin-end 2 units between buttons)

**Event Handlers**:
- Export: `@click="handleExport"` (lines 270-317) - Calls `/api/v1/borrowers/export`, triggers file download
- Import: Opens Bootstrap modal `#borrowerImportModal` (lines 126-130)

### Catalog Page Current Implementation

**File**: `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/pages/CatalogPage.js`

**Current Button Locations** (lines 414-430):
```javascript
<button
    class="btn btn-outline-secondary me-2"
    @click="handleExportCatalog"
    :disabled="exportLoading"
>
    <span v-if="exportLoading" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
    <i v-else class="bi bi-download me-1"></i>
    {{ exportLoading ? t('catalog.downloading') : t('catalog.export') }}
</button>
<button
    class="btn btn-outline-primary me-2"
    data-bs-toggle="modal"
    data-bs-target="#catalogImportModal"
>
    <i class="bi bi-upload me-1"></i>
    {{ t('catalog.import_dc') }}
</button>
```

**Placement**: Top-right corner, in flex container with page title (lines 408-436)

**Styling**:
- Export: `btn btn-outline-secondary` (gray outline)
- Import: `btn btn-outline-primary` (blue outline)
- Add Record: `btn btn-success` (green solid)
- Icons: Bootstrap Icons (`bi-download`, `bi-upload`, `bi-plus-circle`)

**Event Handlers**:
- Export: `@click="handleExportCatalog"` (lines 322-371) - Calls `/api/v1/catalog/export`, triggers file download
- Import: Opens Bootstrap modal `#catalogImportModal` (lines 486-490)

### Decision: Admin Dropdown Component Design

**Replacement Strategy**:

1. **Remove individual buttons**: Export and Import buttons will be removed from both pages
2. **Add admin dropdown**: Single red `btn-danger` dropdown button labeled "Admin"
3. **Menu structure** (Borrowers page):
   - Import Borrowers
   - Export Borrowers
   - ─────────────── (divider)
   - Bulk Edit (enabled when items selected)
   - Edit Selected (enabled when exactly 1 item selected)

4. **Menu structure** (Catalog page):
   - Import Catalog (Dublin Core)
   - Export Catalog
   - ─────────────── (divider)
   - Bulk Edit (enabled when items selected)
   - Edit Selected (enabled when exactly 1 item selected)

5. **Bootstrap 5 dropdown markup** (to be implemented):
```html
<div class="dropdown">
  <button class="btn btn-danger dropdown-toggle" type="button" id="adminDropdown" data-bs-toggle="dropdown">
    <i class="bi bi-shield-exclamation"></i> Admin
  </button>
  <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="adminDropdown">
    <li><a class="dropdown-item" href="#"><i class="bi bi-upload"></i> Import</a></li>
    <li><a class="dropdown-item" href="#"><i class="bi bi-download"></i> Export</a></li>
    <li><hr class="dropdown-divider"></li>
    <li><a class="dropdown-item disabled" href="#"><i class="bi bi-pencil-square"></i> Bulk Edit</a></li>
    <li><a class="dropdown-item disabled" href="#"><i class="bi bi-pencil"></i> Edit Selected</a></li>
  </ul>
</div>
```

**Conditional enabling logic**:
- Bulk Edit: Enabled when `selectedCount >= 2`
- Edit Selected: Enabled when `selectedCount === 1`
- Import/Export: Always enabled

---

## Research Task 2: Bulk Operation UX Patterns

**Objective**: Study professional library systems for bulk edit patterns

### Research Sources

**Previous Research**: `/home/nixos/src/local/bcd4/specs/004-import-export/research.md` documents Koha batch modification tool patterns.

**Key Findings from Koha** (from 004-import-export research):
- **Multi-select pattern**: Checkboxes for row selection
- **Confirmation dialogs**: Show count + scrollable list (max 10 visible items)
- **Progress indicators**: For operations affecting 100+ records
- **Atomic transactions**: All succeed or all fail (no partial success)
- **Row-level validation**: Show which records failed and why

### UX Pattern Decisions for BCD Admin Features

**1. Multi-Select Checkboxes**

**Pattern**:
- Add checkbox column as first column in Borrower/Catalog tables
- "Select All" checkbox in table header
- Selection persists across pagination (session storage)
- Clear selection button visible when items selected

**Implementation** (to be added to BorrowerList.js and SearchResults.js):
```javascript
// Track selected IDs across pagination
const selectedIds = ref(new Set());

// Select all visible items
function selectAllVisible() {
  items.value.forEach(item => selectedIds.value.add(item.id));
}

// Toggle single item
function toggleSelection(id) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id);
  } else {
    selectedIds.value.add(id);
  }
}
```

**2. Confirmation Dialog Pattern**

**Pattern** (for bulk delete operations):
- Modal dialog with warning icon
- Display count: "You are about to delete **30 borrowers**"
- Display first 10 items in scrollable list
- If more than 10: "...and 20 more"
- Two buttons: "Cancel" (secondary) and "Delete [count] Borrowers" (danger)

**Implementation** (Bootstrap modal):
```html
<div class="modal fade" id="confirmBulkDeleteModal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header bg-danger text-white">
        <h5 class="modal-title">
          <i class="bi bi-exclamation-triangle"></i> Confirm Deletion
        </h5>
      </div>
      <div class="modal-body">
        <p>You are about to permanently delete <strong>{{ selectedCount }}</strong> borrowers.</p>
        <ul class="list-group" style="max-height: 200px; overflow-y: auto;">
          <li v-for="borrower in selectedBorrowers.slice(0, 10)" class="list-group-item">
            {{ borrower.full_name }} ({{ borrower.borrower_id }})
          </li>
        </ul>
        <p v-if="selectedCount > 10" class="text-muted mt-2">
          ...and {{ selectedCount - 10 }} more
        </p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" @click="confirmDelete">
          Delete {{ selectedCount }} Borrowers
        </button>
      </div>
    </div>
  </div>
</div>
```

**3. Bulk Edit Modal Flow**

**Pattern** (multi-step form):
- Step 1: Select operation (Change Class / Change Role / Delete)
- Step 2: Configure operation (select target class/role)
- Step 3: Confirm with preview of affected records
- Progress indicator for 100+ records

**Implementation** (single modal with step tracker):
```html
<div class="modal-body">
  <!-- Step Indicator -->
  <div class="progress mb-3" style="height: 3px;">
    <div class="progress-bar" :style="{width: (currentStep / 3 * 100) + '%'}"></div>
  </div>

  <!-- Step 1: Select Operation -->
  <div v-if="currentStep === 1">
    <h6>Select operation</h6>
    <div class="form-check">
      <input type="radio" v-model="operation" value="change_class">
      <label>Change Class</label>
    </div>
    <div class="form-check">
      <input type="radio" v-model="operation" value="change_role">
      <label>Change Role</label>
    </div>
    <div class="form-check">
      <input type="radio" v-model="operation" value="delete">
      <label>Delete Borrowers</label>
    </div>
  </div>

  <!-- Step 2: Configure (if not delete) -->
  <div v-if="currentStep === 2 && operation !== 'delete'">
    <h6>Configure operation</h6>
    <select v-if="operation === 'change_class'" v-model="targetClass">
      <option v-for="cls in classes" :value="cls.id">{{ cls.name }}</option>
    </select>
    <select v-if="operation === 'change_role'" v-model="targetRole">
      <option value="student">Student</option>
      <option value="teacher">Teacher</option>
      <option value="staff">Staff</option>
    </select>
  </div>

  <!-- Step 3: Confirm -->
  <div v-if="currentStep === 3">
    <h6>Confirm operation</h6>
    <p>{{ confirmationMessage }}</p>
    <!-- Preview list (first 10) -->
  </div>
</div>
```

**4. Progress Indicator Pattern**

**Pattern** (for 100+ record operations):
- Display percentage complete
- Show progress bar
- Display current operation (e.g., "Processing 45 of 150...")
- Disable cancel button once started (atomic transaction)

**Reuse from existing import modal** (BorrowerImport.js lines 65-70):
```html
<div v-if="importing" class="text-center py-4">
  <div class="spinner-border text-primary mb-3" role="status">
    <span class="visually-hidden">{{ $t('common.loading') }}</span>
  </div>
  <p class="text-muted">{{ $t('borrowers.import.importing') }}...</p>
</div>
```

**Enhanced for bulk operations** (with percentage):
```html
<div v-if="bulkOperationInProgress" class="text-center py-4">
  <div class="progress mb-3" style="height: 20px;">
    <div class="progress-bar progress-bar-striped progress-bar-animated"
         :style="{width: progressPercent + '%'}">
      {{ progressPercent }}%
    </div>
  </div>
  <p class="text-muted">Processing {{ processedCount }} of {{ totalCount }}...</p>
</div>
```

### Alternatives Considered

**Alternative 1: Single-step modal for each operation**
- Rejected: Requires 3 separate modals (change class, change role, delete)
- Rationale: Unified workflow is clearer and reuses confirmation step

**Alternative 2: Inline editing (editable table cells)**
- Rejected: Confusing for bulk operations affecting 30+ records
- Rationale: Modal workflow provides clear visual separation from normal operations

**Alternative 3: Spreadsheet-style bulk editor (external app)**
- Rejected: Adds complexity, breaks single-page workflow
- Rationale: BCD targets simplicity for elementary school librarians

---

## Research Task 3: CASCADE Delete Verification

**Objective**: Verify database schema supports CASCADE delete behavior

### Database Models Review

**Files examined**:
- `/home/nixos/src/local/bcd4/src/bcd_api/models/borrower.py`
- `/home/nixos/src/local/bcd4/src/bcd_api/models/class_model.py`
- `/home/nixos/src/local/bcd4/src/bcd_api/models/bibliographic_record.py`
- `/home/nixos/src/local/bcd4/src/bcd_api/models/item.py`

### Borrower Model CASCADE Relationships

**File**: `src/bcd_api/models/borrower.py`

**Foreign Key Constraints**:

1. **borrower.class_id → class.id** (line 23):
```python
class_id = Column(Integer, ForeignKey("class.id", ondelete="SET NULL"), nullable=True, index=True)
```
- **Behavior**: When a class is deleted, borrower.class_id is set to NULL
- **Correct**: ✅ Students are unassigned but not deleted

2. **Borrower → CirculationTransaction** (lines 48-52):
```python
circulation_transactions = relationship(
    "CirculationTransaction",
    back_populates="borrower",
    cascade="all, delete-orphan"
)
```
- **Behavior**: When a borrower is deleted, all circulation transactions are deleted
- **Correct**: ✅ CASCADE delete for historical data

3. **Borrower → Hold** (line 53):
```python
holds = relationship("Hold", back_populates="borrower", cascade="all, delete-orphan")
```
- **Behavior**: When a borrower is deleted, all holds are deleted
- **Correct**: ✅ CASCADE delete for pending holds

### Class Model CASCADE Relationships

**File**: `src/bcd_api/models/class_model.py`

**No CASCADE constraints** - Class deletion logic:
1. When class is deleted, borrower.class_id is set to NULL (via Borrower model's `ondelete="SET NULL"`)
2. No other tables reference Class

**Verification**: ✅ Class deletion behavior is correct (unassigns students, deletes class)

### BiblographicRecord Model CASCADE Relationships

**File**: `src/bcd_api/models/bibliographic_record.py`

**Relationships** (lines 85-91):

1. **BiblographicRecord → Item** (line 85):
```python
items = relationship("Item", back_populates="bibliographic_record", cascade="all, delete-orphan")
```
- **Behavior**: When a bibliographic record is deleted, all associated items are deleted
- **Correct**: ✅ CASCADE delete for physical copies

2. **BiblographicRecord → CirculationTransaction** (lines 86-90):
```python
circulation_transactions = relationship(
    "CirculationTransaction",
    back_populates="bibliographic_record",
    cascade="all, delete-orphan"
)
```
- **Behavior**: When a bibliographic record is deleted, all circulation history is deleted
- **Correct**: ✅ CASCADE delete for historical data

3. **BiblographicRecord → Hold** (line 91):
```python
holds = relationship("Hold", back_populates="bibliographic_record", cascade="all, delete-orphan")
```
- **Behavior**: When a bibliographic record is deleted, all holds are deleted
- **Correct**: ✅ CASCADE delete for pending holds

### Item Model CASCADE Relationships

**File**: `src/bcd_api/models/item.py`

**Foreign Key Constraints**:

1. **item.bibliographic_record_id → bibliographic_record.id** (lines 18-23):
```python
bibliographic_record_id = Column(
    Integer,
    ForeignKey("bibliographic_record.id", ondelete="CASCADE"),
    nullable=False,
    index=True
)
```
- **Behavior**: When a bibliographic record is deleted, all items are deleted
- **Correct**: ✅ CASCADE delete enforced at database level

2. **Item → CirculationTransaction** (lines 63-67):
```python
circulation_transactions = relationship(
    "CirculationTransaction",
    back_populates="item",
    cascade="all, delete-orphan"
)
```
- **Behavior**: When an item is deleted, all circulation history is deleted
- **Correct**: ✅ CASCADE delete for historical data

### CASCADE Delete Summary

| Operation | Cascade Behavior | Database Support | Status |
|-----------|------------------|------------------|--------|
| Delete Borrower | CirculationTransactions deleted, Holds deleted | ✅ SQLAlchemy ORM cascade | ✅ Correct |
| Delete Class | Borrowers unassigned (class_id = NULL) | ✅ `ondelete="SET NULL"` | ✅ Correct |
| Delete BiblographicRecord | Items deleted, CirculationTransactions deleted, Holds deleted | ✅ SQLAlchemy ORM cascade | ✅ Correct |
| Delete Item | CirculationTransactions deleted | ✅ SQLAlchemy ORM cascade | ✅ Correct |

**Verification Result**: ✅ **All CASCADE delete behaviors are correctly configured**

**No schema changes needed** - Existing foreign key constraints and relationship cascades support all admin operations.

---

## Research Task 4: Progress Indicator Patterns

**Objective**: Find existing progress indicator implementation to reuse

### Existing Progress Indicators

**File**: `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/borrowers/BorrowerImport.js`

**Import Progress Indicator** (lines 65-70):
```html
<div v-if="importing" class="text-center py-4">
  <div class="spinner-border text-primary mb-3" role="status">
    <span class="visually-hidden">{{ $t('common.loading') }}</span>
  </div>
  <p class="text-muted">{{ $t('borrowers.import.importing') }}...</p>
</div>
```

**Components used**:
- Bootstrap 5 `spinner-border` (rotating circle)
- `text-primary` (blue color)
- `visually-hidden` span for accessibility
- Text message below spinner

**File**: `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/catalog/CatalogImport.js`

**Catalog Import Progress** (lines 66-72):
```html
<div v-if="importing" class="text-center py-4">
  <div class="spinner-border text-primary mb-3" role="status">
    <span class="visually-hidden">{{ $t('common.loading') }}</span>
  </div>
  <p class="text-muted">{{ $t('common.importing') }}...</p>
  <p class="small text-muted">{{ $t('cataloging.import_instructions') }}</p>
</div>
```

**Same pattern** with additional instruction text.

### Progress Indicator for Bulk Operations

**Decision**: Reuse existing spinner pattern for operations <100 records, add progress bar for 100+ records

**Implementation**:

**Simple Spinner** (for <100 records):
```html
<div v-if="bulkOperationInProgress && totalCount < 100" class="text-center py-4">
  <div class="spinner-border text-primary mb-3" role="status">
    <span class="visually-hidden">Processing...</span>
  </div>
  <p class="text-muted">{{ operationMessage }}...</p>
</div>
```

**Progress Bar** (for 100+ records):
```html
<div v-if="bulkOperationInProgress && totalCount >= 100" class="text-center py-4">
  <!-- Progress Bar -->
  <div class="progress mb-3" style="height: 25px;">
    <div
      class="progress-bar progress-bar-striped progress-bar-animated bg-primary"
      role="progressbar"
      :style="{width: progressPercent + '%'}"
      :aria-valuenow="progressPercent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      {{ progressPercent }}%
    </div>
  </div>

  <!-- Status Text -->
  <p class="text-muted">
    Processing {{ processedCount }} of {{ totalCount }} {{ entityType }}...
  </p>

  <!-- Estimated Time Remaining (optional) -->
  <p class="small text-muted" v-if="estimatedTimeRemaining">
    Estimated time remaining: {{ estimatedTimeRemaining }}
  </p>
</div>
```

**Backend API Response** (for progress tracking):
```json
{
  "total": 150,
  "processed": 45,
  "percent": 30,
  "status": "processing",
  "message": "Updating borrowers..."
}
```

**Frontend polling logic** (for long operations):
```javascript
async function pollBulkOperationProgress(operationId) {
  const interval = setInterval(async () => {
    const status = await apiClient.get(`/admin/bulk-operation/${operationId}/status`);

    processedCount.value = status.processed;
    totalCount.value = status.total;
    progressPercent.value = status.percent;

    if (status.status === 'completed' || status.status === 'failed') {
      clearInterval(interval);
      // Show result
    }
  }, 1000); // Poll every 1 second
}
```

**Decision**: For MVP, use **synchronous operations with simple spinner** for <100 records. Progress bar will be added if performance testing shows operations >10 seconds on legacy hardware.

---

## Research Task 5: Error Codes for Admin Operations

**Objective**: Define new error codes following architecture patterns

### Existing Error Code Patterns

**File**: `/home/nixos/src/local/bcd4/src/bcd_api/core/exceptions.py`

**Base Exception Class** (lines 7-21):
```python
class BCDException(HTTPException):
    """Base exception for BCD application with error code and context support."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.context = context or {}
```

**Key Pattern**: All exceptions provide:
- `error_code`: Machine-readable string (e.g., `BORROWER_NOT_FOUND`)
- `context`: Dictionary with relevant data (e.g., `{"borrower_id": "101"}`)
- `detail`: Human-readable message (for logging, not i18n)

### Existing Error Codes

**Borrower-related**:
- `BORROWER_NOT_FOUND` (line 70)
- `BORROWER_HAS_OVERDUE` (line 81)
- `BORROWER_BLOCKED` (line 92)

**Item/Catalog-related**:
- `ITEM_NOT_FOUND` (line 101)
- `ITEM_NOT_AVAILABLE` (line 112)
- `ITEM_NOT_LOANABLE` (line 123)

**Duplicate/Conflict-related**:
- `DuplicateISBNException` (line 207)
- `DuplicateBorrowerIDException` (line 217)
- `DuplicateItemIDException` (line 227)

**CSV Import/Export-related**:
- `CSV_VALIDATION_ERROR` (line 285)
- `CSV_ENCODING_ERROR` (line 301)
- `CSV_ROW_LIMIT_EXCEEDED` (line 315)
- `EXPORT_TOO_LARGE` (line 254)
- `EXPORT_FAILED` (line 268)

### New Error Codes for Admin Operations

**Required Error Codes** (from plan.md research questions):

1. **BORROWER_ID_NOT_AVAILABLE** - For duplicate borrower ID during single edit
2. **DUPLICATE_BARCODE** - For duplicate item barcode during edit
3. **BULK_OPERATION_FAILED** - For atomic transaction rollback in bulk operations
4. **CLASS_HAS_BORROWERS** - ~~NOT NEEDED~~ (per spec, classes can be deleted with students assigned - students are just unassigned)

### Error Code Definitions

**File**: `src/bcd_api/core/exceptions.py` (to be modified)

```python
# Admin-specific exceptions

class BorrowerIDNotAvailableException(ConflictError):
    """Borrower ID is already in use by another borrower."""

    def __init__(self, borrower_id: str, existing_borrower_name: str):
        detail = f"Borrower ID '{borrower_id}' is already assigned to {existing_borrower_name}"
        context = {
            "borrower_id": borrower_id,
            "existing_borrower_name": existing_borrower_name,
            "suggestion": "Choose a different ID or update the existing borrower"
        }
        super().__init__(detail)
        self.error_code = "BORROWER_ID_NOT_AVAILABLE"
        self.context = context


class DuplicateBarcodeException(ConflictError):
    """Item barcode is already in use."""

    def __init__(self, barcode: str, existing_item_id: str):
        detail = f"Barcode '{barcode}' is already assigned to item {existing_item_id}"
        context = {
            "barcode": barcode,
            "existing_item_id": existing_item_id,
            "suggestion": "Use a different barcode or update the existing item"
        }
        super().__init__(detail)
        self.error_code = "DUPLICATE_BARCODE"
        self.context = context


class BulkOperationFailedException(BCDException):
    """Bulk operation failed and was rolled back."""

    def __init__(self, operation: str, total_count: int, failed_count: int, errors: list[dict]):
        detail = f"Bulk {operation} failed: {failed_count} of {total_count} records could not be processed"
        context = {
            "operation": operation,
            "total_count": total_count,
            "failed_count": failed_count,
            "successful_count": total_count - failed_count,
            "errors": errors  # List of {"record_id": ..., "error": ...}
        }
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
        self.error_code = "BULK_OPERATION_FAILED"
        self.context = context


class ValidationFailedException(ValidationError):
    """Validation failed for one or more fields."""

    def __init__(self, field_errors: dict[str, str]):
        detail = f"Validation failed for {len(field_errors)} field(s)"
        context = {
            "field_errors": field_errors  # {"field_name": "error message"}
        }
        super().__init__(detail)
        self.error_code = "VALIDATION_FAILED"
        self.context = context


class ClassNotFoundException(NotFoundException):
    """Class not found."""

    def __init__(self, class_id: int):
        super().__init__("Class", class_id)
        self.error_code = "CLASS_NOT_FOUND"
        self.context = {"class_id": class_id}


class DuplicateClassNameException(ConflictError):
    """Class name already exists for the academic year."""

    def __init__(self, class_name: str, academic_year: str):
        detail = f"Class '{class_name}' already exists for academic year {academic_year}"
        context = {
            "class_name": class_name,
            "academic_year": academic_year,
            "suggestion": "Use a different class name or update the existing class"
        }
        super().__init__(detail)
        self.error_code = "DUPLICATE_CLASS_NAME"
        self.context = context
```

### Error Code Summary Table

| Error Code | HTTP Status | Context Fields | Used In |
|------------|-------------|----------------|---------|
| `BORROWER_ID_NOT_AVAILABLE` | 409 Conflict | `borrower_id`, `existing_borrower_name`, `suggestion` | Single borrower edit |
| `DUPLICATE_BARCODE` | 409 Conflict | `barcode`, `existing_item_id`, `suggestion` | Single item edit |
| `BULK_OPERATION_FAILED` | 400 Bad Request | `operation`, `total_count`, `failed_count`, `successful_count`, `errors[]` | Bulk operations (rollback) |
| `VALIDATION_FAILED` | 422 Unprocessable Entity | `field_errors{}` | Form validation |
| `CLASS_NOT_FOUND` | 404 Not Found | `class_id` | Class CRUD |
| `DUPLICATE_CLASS_NAME` | 409 Conflict | `class_name`, `academic_year`, `suggestion` | Class creation |

### Frontend Error Message Mapping

**File**: `src/bcd_web_vue/locales/en.json` (to be updated)

```json
{
  "errors": {
    "BORROWER_ID_NOT_AVAILABLE": "Borrower ID '{{borrower_id}}' is already assigned to {{existing_borrower_name}}. Please choose a different ID.",
    "DUPLICATE_BARCODE": "Barcode '{{barcode}}' is already assigned to item {{existing_item_id}}. Please use a different barcode.",
    "BULK_OPERATION_FAILED": "Bulk {{operation}} failed: {{failed_count}} of {{total_count}} records could not be processed. All changes have been rolled back.",
    "VALIDATION_FAILED": "Validation failed. Please correct the errors and try again.",
    "CLASS_NOT_FOUND": "Class not found (ID: {{class_id}}).",
    "DUPLICATE_CLASS_NAME": "Class '{{class_name}}' already exists for academic year {{academic_year}}. Please choose a different name."
  }
}
```

**File**: `src/bcd_web_vue/locales/fr.json` (to be updated)

```json
{
  "errors": {
    "BORROWER_ID_NOT_AVAILABLE": "L'identifiant emprunteur '{{borrower_id}}' est déjà attribué à {{existing_borrower_name}}. Veuillez choisir un autre identifiant.",
    "DUPLICATE_BARCODE": "Le code-barres '{{barcode}}' est déjà attribué à l'exemplaire {{existing_item_id}}. Veuillez utiliser un autre code-barres.",
    "BULK_OPERATION_FAILED": "L'opération groupée {{operation}} a échoué : {{failed_count}} sur {{total_count}} enregistrements n'ont pas pu être traités. Toutes les modifications ont été annulées.",
    "VALIDATION_FAILED": "La validation a échoué. Veuillez corriger les erreurs et réessayer.",
    "CLASS_NOT_FOUND": "Classe introuvable (ID : {{class_id}}).",
    "DUPLICATE_CLASS_NAME": "La classe '{{class_name}}' existe déjà pour l'année scolaire {{academic_year}}. Veuillez choisir un autre nom."
  }
}
```

---

## Design Decisions

### Admin Dropdown Component Design

**Bootstrap 5 Dropdown Structure**:
```javascript
// AdminDropdown.js (new component)
export default {
  name: 'AdminDropdown',

  props: {
    page: {
      type: String,
      required: true,
      validator: (value) => ['borrowers', 'catalog'].includes(value)
    },
    selectedCount: {
      type: Number,
      default: 0
    }
  },

  emits: ['import', 'export', 'bulk-edit', 'edit-selected'],

  template: `
    <div class="dropdown">
      <button
        class="btn btn-danger dropdown-toggle"
        type="button"
        id="adminDropdown"
        data-bs-toggle="dropdown"
        aria-expanded="false"
      >
        <i class="bi bi-shield-exclamation"></i>
        {{ $t('admin.menu_title') }}
      </button>
      <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="adminDropdown">
        <!-- Import -->
        <li>
          <a class="dropdown-item" href="#" @click.prevent="$emit('import')">
            <i class="bi bi-upload me-2"></i>
            {{ $t('admin.import_' + page) }}
          </a>
        </li>

        <!-- Export -->
        <li>
          <a class="dropdown-item" href="#" @click.prevent="$emit('export')">
            <i class="bi bi-download me-2"></i>
            {{ $t('admin.export_' + page) }}
          </a>
        </li>

        <li><hr class="dropdown-divider"></li>

        <!-- Bulk Edit (enabled when 2+ selected) -->
        <li>
          <a
            class="dropdown-item"
            :class="{ disabled: selectedCount < 2 }"
            href="#"
            @click.prevent="selectedCount >= 2 && $emit('bulk-edit')"
          >
            <i class="bi bi-pencil-square me-2"></i>
            {{ $t('admin.bulk_edit') }}
            <span v-if="selectedCount >= 2" class="badge bg-primary ms-2">
              {{ selectedCount }}
            </span>
          </a>
        </li>

        <!-- Edit Selected (enabled when exactly 1 selected) -->
        <li>
          <a
            class="dropdown-item"
            :class="{ disabled: selectedCount !== 1 }"
            href="#"
            @click.prevent="selectedCount === 1 && $emit('edit-selected')"
          >
            <i class="bi bi-pencil me-2"></i>
            {{ $t('admin.edit_selected') }}
          </a>
        </li>
      </ul>
    </div>
  `
}
```

**Styling decisions**:
- Red `btn-danger` for admin button (visual warning)
- `dropdown-menu-end` for right alignment (matches current button placement)
- Disabled state uses `.disabled` class (gray text, no pointer)
- Badge shows selected count when bulk edit enabled
- Bootstrap Icons for visual consistency

### Bulk Edit Modal Flow

**Multi-step wizard** with progress indicator:

1. **Step 1: Select Operation**
   - Radio buttons: Change Class / Change Role / Delete
   - Next button enabled when operation selected

2. **Step 2: Configure Operation** (skip for delete)
   - Change Class: Dropdown of available classes
   - Change Role: Radio buttons (student/teacher/staff)
   - Next button enabled when target selected

3. **Step 3: Confirm**
   - Display operation summary: "You are about to change class for **30 borrowers**"
   - Show first 10 affected records in scrollable list
   - "...and 20 more" if count > 10
   - Two buttons: Back (secondary) / Confirm (danger)

4. **Step 4: Processing**
   - Show spinner (<100 records) or progress bar (100+ records)
   - Disable all buttons during processing

5. **Step 5: Result**
   - Success: "Successfully updated 30 borrowers"
   - Partial failure: "Updated 25 of 30 borrowers. 5 failed (see details)"
   - Complete failure: "Operation failed and was rolled back. No changes were made."
   - Close button to return to list

### Confirmation Dialog Pattern

**For delete operations** (borrowers, classes, catalog records):

```html
<div class="modal-header bg-danger text-white">
  <h5 class="modal-title">
    <i class="bi bi-exclamation-triangle"></i>
    {{ $t('admin.confirm_delete_title') }}
  </h5>
</div>

<div class="modal-body">
  <div class="alert alert-danger">
    <p class="mb-2">
      <strong>{{ $t('admin.warning') }}:</strong>
      {{ $t('admin.delete_warning_message') }}
    </p>
  </div>

  <p>{{ $t('admin.delete_count_message', { count: selectedCount, type: entityType }) }}</p>

  <!-- Scrollable list (max 10 visible) -->
  <ul class="list-group mb-3" style="max-height: 200px; overflow-y: auto;">
    <li v-for="item in selectedItems.slice(0, 10)" class="list-group-item">
      {{ item.displayName }}
    </li>
  </ul>

  <p v-if="selectedCount > 10" class="text-muted">
    {{ $t('admin.and_n_more', { count: selectedCount - 10 }) }}
  </p>
</div>

<div class="modal-footer">
  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
    {{ $t('common.cancel') }}
  </button>
  <button type="button" class="btn btn-danger" @click="confirmDelete">
    {{ $t('admin.delete_n_items', { count: selectedCount, type: entityType }) }}
  </button>
</div>
```

**Visual warning elements**:
- Red header background (`bg-danger text-white`)
- Alert box with warning icon
- Clear count display
- Scrollable list prevents modal from growing too large
- Confirm button uses danger styling and repeats count

---

## Alternatives Considered

### Alternative 1: Merge Duplicate Borrowers Feature

**Considered**: Allow librarians to merge two borrower records (combining circulation history)

**Rejected**: Adds significant complexity for minimal benefit at elementary school scale

**Rationale**:
- Duplicate borrowers are rare (unique ID validation)
- Merging circulation history is complex (which borrower ID to keep?)
- Simpler to delete duplicate and manually reassign if needed
- Not mentioned in user request

### Alternative 2: Soft Deletes (deleted_at Column)

**Considered**: Add `deleted_at` timestamp column instead of hard deletes (allows recovery)

**Rejected**: CASCADE delete chosen for simplicity per user preference

**Rationale**:
- No audit trail requirement for elementary school
- Soft deletes add complexity to all queries (`WHERE deleted_at IS NULL`)
- Database backups provide recovery mechanism
- User requested "delete" not "archive"
- Keep software simple per constitution

### Alternative 3: Undo/Redo for Bulk Operations

**Considered**: Add undo button to revert bulk operations within 5 minutes

**Rejected**: Atomic transactions with confirmation dialogs are sufficient

**Rationale**:
- Confirmation dialog with preview prevents accidental operations
- Atomic rollback on error ensures consistency
- Undo adds significant complexity (need to track changes)
- Database backups provide recovery for major mistakes

### Alternative 4: Batch Size Limits for Bulk Operations

**Considered**: Limit bulk operations to 100 records at a time

**Rejected**: Allow unlimited (with progress indicator for 100+)

**Rationale**:
- Elementary school scale: ~500 students, unlikely to select 100+ at once
- Progress indicator provides feedback for large operations
- Atomic transaction ensures all-or-nothing (no partial corruption)
- Artificial limit frustrates users

---

## Conclusion

All NEEDS CLARIFICATION items from plan.md have been resolved:

1. ✅ **Existing Import/Export UI documented**: Current button locations, styling, and event handlers identified for replacement with admin dropdown
2. ✅ **Bulk operation UX patterns defined**: Multi-select checkboxes, confirmation dialogs, multi-step modal flow, progress indicators
3. ✅ **CASCADE delete verified**: Database schema correctly supports all admin operations (borrower delete, class delete, catalog delete)
4. ✅ **Progress indicator patterns identified**: Reuse existing import modal spinner for <100 records, add progress bar for 100+ records
5. ✅ **Error codes defined**: 6 new error codes following BCDException pattern with error_code + context structure

**Ready for Phase 1 (Design & Contracts)**: Next steps are to create data-model.md, contracts/api-endpoints.yaml, contracts/error-codes.md, and quickstart.md.

**Key architectural decisions made**:
- Bootstrap 5 dropdown with `btn-danger` styling for admin menu
- Atomic transactions for bulk operations (all succeed or all fail with rollback)
- Multi-step modal wizard for bulk edit operations
- Confirmation dialogs with scrollable lists (max 10 visible items)
- Reuse existing progress indicator components from import modals
- 6 new exception classes following BCDException pattern
- Complete en/fr i18n coverage for all error messages

**No schema changes required**: Existing CASCADE delete relationships fully support all admin features.
