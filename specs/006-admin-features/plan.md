# Implementation Plan: Admin Features Panel

**Branch**: `006-admin-features` | **Date**: 2026-02-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-admin-features/spec.md`

## Summary

Add comprehensive administrative features to the BCD web interface:
- Replace individual Import/Export buttons with a red "Admin" dropdown menu on Borrower & Catalog pages
- Create new Classes management page (CRUD operations)
- Add bulk operations for borrowers (change class, change role, delete multiple)
- Add single borrower editing (name, ID, role, class)
- Add bulk catalog operations (delete records, edit common fields)
- Add single catalog/item editing

**Primary goal**: Group dangerous administrative actions in a protected menu to prevent misclicks while maintaining accessibility for librarians. Keep implementation simple (CASCADE deletes, no soft deletes, no merge features).

## Technical Context

**Language/Version**: Python 3.11+ (matches existing BCD codebase)
**Primary Dependencies**: FastAPI 0.104+, Vue 3.4.21 (CDN), SQLAlchemy 2.0+, Bootstrap 5.3.3
**Storage**: SQLite (development), PostgreSQL-ready (production) - existing database
**Testing**: pytest (service-layer integration tests), AAA pattern
**Target Platform**: Linux (primary), Windows (compatibility required)
**Project Type**: Web application (FastAPI backend + Vue 3 SPA frontend)
**Performance Goals**:
- Single-record operations: <500ms
- Bulk operations (≤100 records): <10 seconds
- Bulk operations (100+ records): Progress indicator required
**Constraints**:
- Must work on 5+ year old hardware (dual-core, 4GB RAM, HDD)
- Localhost-only deployment (no network latency concerns)
- No build tools for frontend (CDN-based Vue 3)
**Scale/Scope**:
- ~500 students, ~10 classes, ~5,000 catalog records
- 7 user stories (P1-P7), 47 functional requirements
- Estimated ~15 new API endpoints, 5 new Vue components, 3 new service methods

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Code Quality & DRY
- ✅ **PASS**: Bulk operations will extract reusable validation/error handling
- ✅ **PASS**: Admin dropdown component will be reused across Borrower/Catalog pages
- ⚠️ **REVIEW**: Ensure bulk edit logic doesn't duplicate single edit logic

### Principle II: Library-First Approach
- ✅ **PASS**: Uses existing Bootstrap 5 dropdowns, modals, progress bars
- ✅ **PASS**: Uses existing Vue 3 Composition API patterns
- ✅ **PASS**: No custom implementations needed

### Principle III: Comprehensive Testing Standards
- ✅ **PASS**: Service-layer integration tests required for all CRUD operations
- ✅ **PASS**: Target 80%+ coverage for new service methods
- ✅ **PASS**: AAA pattern for all tests
- ⚠️ **REVIEW**: Bulk operations need transaction rollback tests

### Principle IV: User Experience Consistency
- ✅ **PASS**: Admin dropdown uses consistent Bootstrap styling (`btn-danger`)
- ✅ **PASS**: Confirmation dialogs follow existing modal patterns
- ✅ **PASS**: Error messages use existing i18n infrastructure

### Principle V: Click Minimization
- ✅ **PASS**: Admin operations accessible in ≤2 clicks (Admin menu → operation)
- ✅ **PASS**: Bulk operations reduce clicks significantly (30 students in one action vs. 30 individual actions)
- ✅ **PASS**: Smart defaults (disabled buttons when prerequisites not met)

### Principle VI: Performance for Legacy Hardware
- ✅ **PASS**: Progress indicators for 100+ record operations
- ✅ **PASS**: Bulk operations use single database transaction (no N+1 queries)
- ✅ **PASS**: Target <10 seconds for 100 records on legacy hardware
- ⚠️ **REVIEW**: May need to batch large operations (e.g., 500+ borrowers)

### Principle VII: Database Schema Versioning & Migrations
- ✅ **PASS**: No new tables required (Class, Borrower, BiblographicRecord, Item exist)
- ✅ **PASS**: May need migration to add `deleted_at` index if soft deletes chosen (NOT APPLICABLE - using CASCADE)
- ✅ **PASS**: Class deletion migration to ensure SET NULL on borrower.class_id works correctly

### Principle VIII: Research-First Feature Design
- ✅ **PASS**: Researched Koha, PMB, BiblioNet, Alma, Sierra for best practices
- ✅ **PASS**: Decided against complex features (merge, soft deletes) for simplicity
- ✅ **PASS**: Documented in research.md (Phase 0)

### Principle IX: Design-First Implementation
- ⚠️ **ACTION REQUIRED**: Create wireframes/mockups for:
  - Admin dropdown menu (placement, styling, menu items)
  - Bulk edit modal (multi-step form for change class/role/delete)
  - Classes management page (table + create/edit forms)
  - Confirmation dialogs (count, names/titles display)
  - Progress indicator (percentage, progress bar)

### Principle X: Internationalization (i18n)
- ✅ **PASS**: All UI text externalized to en/fr locale files
- ✅ **PASS**: Error messages use error_code + context pattern from architecture-patterns.md
- ✅ **PASS**: Confirmation dialogs, form labels, button text all i18n

### Principle XI: Quality Gate Process
- ✅ **PASS**: Pre-implementation gate: Run `/speckit.analyze` before `/speckit.implement`
- ✅ **PASS**: Post-implementation gate: Run `/speckit.review` before merge
- ✅ **PASS**: All tests must pass, zero TODOs in production code

**Gate Result**: ✅ **PASS** (with design artifacts required in Phase 1)

## Project Structure

### Documentation (this feature)

```text
specs/006-admin-features/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (already exists)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-endpoints.yaml       # OpenAPI definitions for new endpoints
│   └── error-codes.md           # New error codes for admin operations
├── checklists/
│   └── requirements.md  # Spec quality checklist (already exists)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure (existing)
src/bcd_api/
├── api/
│   ├── admin.py                 # NEW: Admin operations endpoints (bulk edit, delete)
│   ├── classes.py               # NEW: Class CRUD endpoints
│   ├── borrowers.py             # MODIFY: Add bulk/single edit endpoints
│   └── catalog.py               # MODIFY: Add bulk/single edit endpoints
├── services/
│   ├── class_service.py         # EXISTS: Add delete with unassign logic
│   ├── borrower_service.py      # MODIFY: Add bulk operations, single edit
│   └── catalog_service.py       # MODIFY: Add bulk operations, single edit
├── schemas/
│   ├── admin.py                 # NEW: Bulk operation request/response schemas
│   ├── class_schema.py          # NEW: Class CRUD schemas
│   ├── borrower.py              # MODIFY: Add BorrowerBulkEdit, BorrowerUpdate schemas
│   └── catalog.py               # MODIFY: Add BulkEditFields, BulkDelete schemas
└── core/
    └── exceptions.py            # MODIFY: Add admin-specific exceptions

src/bcd_web_vue/
├── js/
│   ├── components/
│   │   ├── admin/
│   │   │   ├── AdminDropdown.js     # NEW: Reusable admin dropdown button
│   │   │   ├── BulkEditModal.js     # NEW: Modal for bulk operations
│   │   │   ├── ConfirmDialog.js     # NEW: Confirmation dialog with details
│   │   │   └── ProgressIndicator.js # NEW: Progress bar for bulk ops
│   │   ├── borrowers/
│   │   │   ├── BorrowerList.js      # MODIFY: Add checkboxes, admin dropdown
│   │   │   ├── BorrowerEditForm.js  # NEW: Single borrower edit modal
│   │   │   └── BorrowerImport.js    # MODIFY: Move to admin dropdown
│   │   ├── catalog/
│   │   │   ├── SearchResults.js     # MODIFY: Add checkboxes, admin dropdown
│   │   │   ├── RecordEditForm.js    # NEW: Single record edit modal
│   │   │   ├── ItemEditForm.js      # NEW: Single item edit modal
│   │   │   └── CatalogImport.js     # MODIFY: Move to admin dropdown
│   │   └── classes/
│   │       ├── ClassList.js         # NEW: Classes table with actions
│   │       ├── ClassForm.js         # NEW: Create/edit class modal
│   │       └── ClassDeleteDialog.js # NEW: Delete confirmation with student count
│   ├── pages/
│   │   ├── BorrowersPage.js         # MODIFY: Integrate AdminDropdown
│   │   ├── CatalogPage.js           # MODIFY: Integrate AdminDropdown
│   │   └── ClassesPage.js           # NEW: Classes management page
│   ├── composables/
│   │   ├── useBulkOperations.js     # NEW: Bulk edit/delete logic
│   │   └── useSelection.js          # NEW: Multi-select checkbox logic
│   └── router.js                    # MODIFY: Add /classes route
└── locales/
    ├── en.json                      # MODIFY: Add admin UI strings
    └── fr.json                      # MODIFY: Add admin UI strings

tests/
├── integration/
│   ├── services/
│   │   ├── test_class_service_admin.py      # NEW: Class CRUD tests
│   │   ├── test_borrower_service_bulk.py    # NEW: Bulk borrower ops tests
│   │   └── test_catalog_service_bulk.py     # NEW: Bulk catalog ops tests
│   └── api/
│       ├── test_admin_endpoints.py          # NEW: Admin API endpoint tests
│       ├── test_classes_endpoints.py        # NEW: Class CRUD API tests
│       └── test_bulk_operations.py          # NEW: Bulk operation API tests
└── unit/
    └── test_admin_exceptions.py             # NEW: Exception handling tests
```

**Structure Decision**: Existing web application structure is sufficient. New admin features integrate into existing `src/bcd_api/` and `src/bcd_web_vue/` directories. No new top-level directories needed.

## Complexity Tracking

> **This feature does not violate the constitution.** No entries needed.

## Phase 0: Research

**Objective**: Resolve all NEEDS CLARIFICATION items and document design decisions.

### Research Tasks

1. **Review existing import/export UI** → Document current button placement for replacement
2. **Analyze bulk operation patterns** → Study Koha batch modification tool for UX patterns
3. **CASCADE delete implications** → Verify database schema supports desired behavior
4. **Progress indicator patterns** → Review existing import workflow for reusable progress UI
5. **Error handling for bulk operations** → Define error codes and context for partial failures

### Research Questions

- ✅ How do existing library systems handle duplicate borrowers? **Answer**: Merge feature (skipped for simplicity)
- ✅ What's the standard pattern for bulk edit modals? **Answer**: Multi-step wizard or single form with operation selector
- ✅ How to display confirmation dialogs with 50+ names? **Answer**: Scrollable list with count, max 10 visible
- ✅ What error codes are needed for admin operations? **Answer**: `CLASS_HAS_BORROWERS`, `BORROWER_ID_NOT_AVAILABLE`, `DUPLICATE_BARCODE`, `BULK_OPERATION_FAILED`

**Output**: `research.md` (generated next)

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete

### Architecture Patterns to Follow

From `.specify/architecture-patterns.md`:

1. **Service Layer Architecture** (Section 1):
   - All business logic in `services/` (NOT in API routes)
   - Thin API routes call service methods
   - Services raise exceptions, API layer catches and converts to HTTP status

2. **Database Design Patterns** (Section 2):
   - Comprehensive indexing on all FK, lookup, filter fields
   - Timezone-aware timestamps (UTC)
   - Denormalized counters where needed (e.g., Class.student_count)

3. **API Design Patterns** (Section 3):
   - Pagination on all list endpoints (limit=100, offset=0)
   - Pydantic schemas for request/response validation
   - Consistent error responses via custom exceptions

4. **Error Handling Patterns** (Section 7):
   - Use `BCDException` base class with `error_code` and `context`
   - Specific exceptions: `ClassHasBorrowersException`, `DuplicateBorrowerIDException`, `DuplicateBarcodeException`
   - Frontend maps `error_code` to i18n translation key

5. **Internationalization Patterns** (Section 8):
   - Backend: error_code + context (no hard-coded strings)
   - Frontend: `errors.{error_code}` translation key with variable interpolation
   - Complete en/fr parity

6. **Vue 3 Web UI Patterns** (Section 5):
   - Composition API for all components
   - Bootstrap 5 utility classes (`btn-danger`, `modal`, `progress`)
   - Barcode scanner support (Enter key submission)

7. **Testing Patterns** (Section 6):
   - Service-layer integration tests (AAA pattern)
   - Test naming: `test_<action>_<condition>_<expected_result>`
   - Mock external APIs, use transaction rollback for cleanup

### Design Artifacts to Generate

1. **data-model.md**: Entity definitions (Class, Borrower, BiblographicRecord, Item) with CASCADE delete rules
2. **contracts/api-endpoints.yaml**: OpenAPI spec for new endpoints
3. **contracts/error-codes.md**: New error codes for admin operations
4. **quickstart.md**: Developer guide for testing admin features locally

### Key Design Decisions

1. **Admin Dropdown Component**:
   - Reusable Vue component (`AdminDropdown.js`)
   - Props: `selectedCount`, `page` (borrowers/catalog)
   - Emits: `import`, `export`, `bulkEdit`, `editSelected`

2. **Bulk Operations Flow**:
   - Select items via checkboxes → Admin dropdown enables "Bulk Edit"
   - Click "Bulk Edit" → Modal opens with operation selector (Change Class/Role/Delete)
   - Select operation + parameters → Confirmation dialog (count + list)
   - Confirm → API call with progress indicator (100+ records only)

3. **Classes Page**:
   - Table with columns: Name, Grade Level, Student Count, Actions
   - Actions: Edit (modal), Delete (confirmation)
   - Delete checks student_count → If >0, unassign all → Delete class

4. **Error Handling**:
   - Bulk operations: Atomic transaction (all succeed or all fail)
   - Validation errors: Clear message with field name + reason
   - Duplicate ID/barcode: "ID not available" / "Barcode already exists"

**Output**: `data-model.md`, `contracts/`, `quickstart.md`

## Phase 2: Task Generation

**Prerequisites**: Phase 1 complete

This phase is handled by `/speckit.tasks` command (NOT by `/speckit.plan`).

Tasks will be generated based on:
- User stories (P1-P7)
- Functional requirements (FR-001 through FR-047)
- Architecture patterns adherence
- Testing requirements (80%+ coverage)

**Output**: `tasks.md` (generated by `/speckit.tasks`)

## Next Steps

1. ✅ **Phase 0**: Generate `research.md` (resolve all NEEDS CLARIFICATION)
2. ⏭️ **Phase 1**: Generate `data-model.md`, `contracts/`, `quickstart.md`
3. ⏭️ **Update agent context**: Run `.specify/scripts/bash/update-agent-context.sh claude`
4. ⏭️ **Re-validate Constitution Check** after Phase 1 design
5. ⏭️ **Run `/speckit.tasks`** to generate implementation tasks

---

**Plan Status**: Phase 0 (Research) in progress
**Branch**: `006-admin-features`
**Spec File**: `/home/nixos/src/local/bcd4/specs/006-admin-features/spec.md`
**Plan File**: `/home/nixos/src/local/bcd4/specs/006-admin-features/plan.md`
