# Implementation Tasks: School Library Management System

**Feature**: School Library Management System (BCD)
**Date**: 2026-01-30
**Status**: ✅ **PARTIALLY COMPLETE** (Core system implemented - 64% complete)
**Total Phases**: 9

## Implementation Status (Updated: 2026-02-05)

| Phase | Description | Tasks | Status | Completion Date |
|-------|-------------|-------|--------|-----------------|
| 1: Setup | Project initialization | T001-T020 (20 tasks) | ✅ COMPLETE | 2026-01-30 |
| 2: Foundational | Database, models, API | T021-T055 (35 tasks) | ✅ COMPLETE | 2026-01-30 |
| 3: US1 Circulation | Checkout/return | T056-T085 (30 tasks) | ✅ COMPLETE | 2026-01-30 |
| 4: US2 Cataloging | BNF API, records | T092-T116 (25 tasks) | ✅ COMPLETE | 2026-01-30 |
| 5: US3 Borrowers | Management, import | T117-T137 (21 tasks) | ✅ COMPLETE | 2026-01-30 |
| 6: US4 Search | Catalog search | T138-T151 (14 tasks) | ✅ COMPLETE | 2026-01-30 |
| 7: US5 Reports | Statistics, overdue | T152-T172 (21 tasks) | ✅ COMPLETE | 2026-02-03 |
| 8: US6 Barcodes | Barcode generation | T173-T186 (14 tasks) | ✅ COMPLETE | 2026-01-30 |
| 9: Polish & Admin | Backup, archive | T191-T205 (15 tasks) | 🟡 PARTIAL (8/15) | In Progress |

**Total Progress**: ~120/186 tasks complete (64.5%)

**Test Results** (2026-02-05):
- ✅ Unit tests: 199 passing
- ✅ Integration tests: 110 passing (30 skipped)
- ✅ E2E tests: 48/48 passing
- ✅ Coverage: 90%+ on services, 85%+ overall

**Recent Additions** (2026-02):
- ✅ Database backup system (T191-T198) - API + CLI + tests complete
- ✅ Block/unblock borrowers with standardized reasons (FR-030-BLOCK-1 to FR-030-BLOCK-6)
- ✅ Renew all items for borrower (FR-020-RENEW-1 to FR-020-RENEW-6, FR-058-RENEW-1 to FR-058-RENEW-4)
- ⏳ Archive old data system (T199-T205) - NOT STARTED

## Task Summary

**Total Tasks**: ~186 tasks across 9 phases
- **Phase 1**: Setup (20 tasks) - Project initialization, dependencies, structure
- **Phase 2**: Foundational (20 tasks) - Database, core models, API foundation
- **Phase 3**: User Story 1 [US1-P1] (25 tasks) - Circulation operations
- **Phase 4**: User Story 2 [US2-P2] (20 tasks) - Cataloging with BNF API
- **Phase 5**: User Story 3 [US3-P3] (20 tasks) - Borrower management
- **Phase 6**: User Story 4 [US4-P4] (15 tasks) - Catalog search
- **Phase 7**: User Story 5 [US5-P5] (15 tasks) - Reports
- **Phase 8**: User Story 6 [US6-P6] (10 tasks) - Barcode printing
- **Phase 9**: Polish (25 tasks) - i18n, performance, documentation, database hardening

**Markers**:
- `[P]` - Parallelizable (can be done independently)
- `[US1]` - Maps to User Story 1 (Circulation), etc.
- `[BLOCKING]` - Must complete before dependent tasks

---

## Phase 1: Setup and Project Initialization

**Goal**: Initialize project structure, dependencies, and development environment

**Duration Estimate**: 2-3 hours

**Prerequisites**: Python 3.11+, git, virtual environment

### Environment Setup

- [x] [T001] [P] [BLOCKING] Create project root directory structure at `/home/nixos/src/local/bcd3/`
- [x] [T002] [P] Initialize Python virtual environment with `python3.11 -m venv venv`
- [x] [T003] [P] Create `.gitignore` with Python, SQLite, __pycache__, .env patterns
- [x] [T004] [P] Create `README.md` with project overview and setup instructions
- [x] [T005] [P] Create `pyproject.toml` with project metadata and build configuration

### Dependency Management

- [x] [T006] [P] Create `requirements.txt` with core dependencies: fastapi[all]==0.109.0, sqlalchemy==2.0.25, alembic==1.13.1
- [x] [T007] [P] Add CLI dependencies to `requirements.txt`: click==8.1.7, httpx==0.26.0, rich==13.7.0
- [x] [T008] [P] Add integration dependencies: python-barcode==0.15.1, pymarc==5.1.0, reportlab==4.0.7
- [x] [T009] [P] Create `requirements-dev.txt` with pytest==7.4.3, pytest-asyncio==0.23.2, pytest-cov==4.1.0
- [x] [T010] Install all dependencies with `pip install -r requirements.txt -r requirements-dev.txt`

### Project Structure

- [x] [T011] [BLOCKING] Create `src/bcd_api/` directory with `__init__.py`
- [x] [T012] [BLOCKING] Create `src/bcd_cli/` directory with `__init__.py`
- [x] [T013] [BLOCKING] Create `src/shared/` directory with `__init__.py`
- [x] [T014] [P] Create `migrations/` directory for Alembic
- [x] [T015] [P] Create `tests/` with subdirs: `tests/api/`, `tests/cli/`, `tests/integration/`
- [x] [T016] [P] Create `data/` with subdirs: `data/fixtures/`, `data/sample_imports/`
- [x] [T017] [P] Create `locale/` with subdirs: `locale/fr/LC_MESSAGES/`, `locale/en/LC_MESSAGES/`

### Configuration Files

- [x] [T018] [P] Create `.env.example` with DATABASE_URL, API_HOST, API_PORT, LOG_LEVEL
- [x] [T019] [P] Create `pytest.ini` with test configuration and coverage settings
- [x] [T020] [P] Create `alembic.ini` with migration configuration

**Parallel Execution Example**:
```bash
# Run these tasks in parallel (T001-T005, T006-T009, T018-T020)
# All are independent and don't depend on each other
```

---

## Phase 2: Foundational Layer

**Goal**: Database schema, core models, API skeleton, shared utilities

**Duration Estimate**: 6-8 hours

**Prerequisites**: Phase 1 complete

### Database Schema

- [x] [T021] [BLOCKING] Initialize Alembic with `alembic init migrations` in project root
- [x] [T022] [BLOCKING] Create `migrations/env.py` with SQLAlchemy target_metadata configuration
- [x] [T023] [BLOCKING] Create migration `001_initial_schema.py` for Class table in `migrations/versions/`
- [x] [T024] [BLOCKING] Create migration for Borrower table with blocked_reason field
- [x] [T025] [BLOCKING] Create migration for BiblographicRecord table with BNF fields (language, page_count, target_audience, etc.)
- [x] [T026] [BLOCKING] Create migration for Item table
- [x] [T027] [BLOCKING] Create migration for CirculationTransaction table with computed fields
- [x] [T028] [BLOCKING] Create migration for Hold table
- [x] [T029] [BLOCKING] Create migration for SystemSettings table (singleton)
- [x] [T030] Create triggers in migration: update_biblio_item_count, update_circulation_counts, reorder_hold_queue

### SQLAlchemy ORM Models

- [x] [T031] [BLOCKING] Create `src/bcd_api/core/database.py` with SQLAlchemy engine, SessionLocal, Base
- [x] [T032] [P] [BLOCKING] Create `src/bcd_api/models/class_model.py` with Class ORM model
- [x] [T033] [P] [BLOCKING] Create `src/bcd_api/models/borrower.py` with Borrower ORM model and relationships
- [x] [T034] [P] [BLOCKING] Create `src/bcd_api/models/bibliographic_record.py` with BiblographicRecord model
- [x] [T035] [P] [BLOCKING] Create `src/bcd_api/models/item.py` with Item ORM model
- [x] [T036] [P] [BLOCKING] Create `src/bcd_api/models/circulation.py` with CirculationTransaction model
- [x] [T037] [P] [BLOCKING] Create `src/bcd_api/models/hold.py` with Hold ORM model
- [x] [T038] [P] [BLOCKING] Create `src/bcd_api/models/system_settings.py` with SystemSettings model
- [x] [T039] Create `src/bcd_api/models/__init__.py` with all model imports

### API Foundation

- [x] [T040] [BLOCKING] Create `src/bcd_api/main.py` with FastAPI app initialization, CORS, API versioning (/api/v1)
- [x] [T041] [BLOCKING] Create `src/bcd_api/core/config.py` with Settings class using Pydantic BaseSettings
- [x] [T042] [P] Create `src/bcd_api/core/deps.py` with get_db dependency for database sessions
- [x] [T043] [P] Create `src/bcd_api/api/__init__.py` and `src/bcd_api/api/v1/__init__.py`
- [x] [T044] Create `src/bcd_api/api/v1/router.py` to aggregate all endpoint routers

### Shared Utilities

- [x] [T045] [P] Create `src/shared/constants.py` with enums: BorrowerRole, ItemStatus, ItemCondition, MediumType
- [x] [T046] [P] Create `src/shared/validators.py` with ISBN validation, ID format validation functions
- [x] [T047] [P] Create `src/bcd_api/core/exceptions.py` with custom exceptions: ValidationError, NotFoundError, ConflictError

### CLI Foundation

- [x] [T048] [BLOCKING] Create `src/bcd_cli/main.py` with Click group and version command
- [x] [T049] [BLOCKING] Create `src/bcd_cli/client.py` with httpx client wrapper for API communication
- [x] [T050] [P] Create `src/bcd_cli/utils/display.py` with Rich console, table formatting utilities
- [x] [T051] [P] Create `src/bcd_cli/utils/config.py` for CLI config management (~/.bcd/config.json)

**Dependencies**:
- T031 (database.py) blocks T032-T038 (all models need Base)
- T040 (FastAPI app) blocks T044 (router aggregation)
- T023-T030 (migrations) must complete before running `alembic upgrade head`

**Parallel Execution Example**:
```bash
# After T031 completes, run T032-T038 in parallel (all models)
# After T040 completes, T042-T043 can run in parallel
```

---

## Phase 3: User Story 1 - Circulation Operations [US1-P1]

**Goal**: Implement checkout, return, renew operations (highest priority)

**Duration Estimate**: 12-16 hours

**User Story**: As a librarian, I can check out items to borrowers, process returns, and renew items using barcode scanners.

**Acceptance Criteria**:
- Checkout: Scan borrower ID → scan item barcodes → confirm → print receipt (2 items in <30s)
- Return: Scan item barcodes → system shows borrower info and overdue status → confirm
- Renew: Show borrower's current loans → select items to renew → extend due dates

**Prerequisites**: Phase 2 complete (models, database, API skeleton)

### Pydantic Schemas

- [x] [T052] [P] [US1] Create `src/bcd_api/schemas/borrower.py` with BorrowerBase, BorrowerSummary, BorrowerDetailed schemas
- [x] [T053] [P] [US1] Create `src/bcd_api/schemas/item.py` with ItemBase, ItemSummary schemas
- [x] [T054] [P] [US1] Create `src/bcd_api/schemas/circulation.py` with CheckoutRequest, CheckoutResponse, ReturnRequest, RenewRequest schemas
- [x] [T055] [P] [US1] Create `src/bcd_api/schemas/bibliographic_record.py` with BiblographicRecordSummary schema

### Service Layer (Business Logic)

- [x] [T056] [BLOCKING] [US1] Create `src/bcd_api/services/circulation_service.py` with checkout_items() function
- [x] [T057] [US1] Implement return_items() in circulation_service.py with overdue calculation
- [x] [T058] [US1] Implement renew_items() in circulation_service.py with renewal limit validation
- [x] [T059] [US1] Implement get_borrower_current_loans() in circulation_service.py
- [x] [T060] [US1] Implement get_item_circulation_history() in circulation_service.py
- [x] [T061] [US1] Add validation in checkout_items(): borrower active, not over limit, item available
- [x] [T062] [US1] Add auto-blocking logic in return_items(): block borrower if item overdue

### API Endpoints

- [x] [T063] [BLOCKING] [US1] Create `src/bcd_api/api/v1/circulation.py` with POST /circulation/checkout endpoint
- [x] [T064] [US1] Implement POST /circulation/return endpoint in circulation.py
- [x] [T065] [US1] Implement POST /circulation/renew endpoint in circulation.py
- [x] [T066] [US1] Implement GET /circulation/borrower/{borrower_id}/items endpoint
- [x] [T067] [US1] Implement GET /circulation/item/{item_id}/history endpoint
- [x] [T068] [US1] Implement GET /circulation/borrower/{borrower_id}/history endpoint
- [x] [T069] [US1] Register circulation router in `src/bcd_api/api/v1/router.py`

### CLI Commands (Interactive Scanner Mode)

- [x] [T070] [BLOCKING] [US1] Create `src/bcd_cli/commands/checkout.py` with interactive checkout workflow
- [x] [T071] [US1] Implement barcode scanner input handling in `src/bcd_cli/utils/scanner.py` with timeout
- [x] [T072] [US1] Add borrower lookup by ID in checkout.py (API call to GET /borrowers/{id})
- [x] [T073] [US1] Add multi-item scanning loop in checkout.py (scan until Enter pressed)
- [x] [T074] [US1] Add checkout confirmation table with Rich in checkout.py
- [x] [T075] [US1] Create `src/bcd_cli/commands/return_cmd.py` with interactive return workflow
- [x] [T076] [US1] Add overdue status display in return workflow with warning colors

### CLI Commands (Direct Mode)

- [x] [T077] [P] [US1] Add direct checkout mode: `bcd checkout <borrower_id> <item_id1> <item_id2>` in checkout.py
- [x] [T078] [P] [US1] Add direct return mode: `bcd return <item_id1> <item_id2>` in return_cmd.py
- [x] [T079] [P] [US1] Create `src/bcd_cli/commands/renew.py` with interactive renewal (show loans, select items)
- [x] [T080] [US1] Add direct renew mode: `bcd renew <borrower_id> --all` in renew.py

### Error Handling

- [x] [T081] [P] [US1] Add error handling in checkout.py: borrower not found, item not found, borrower blocked
- [x] [T082] [P] [US1] Add error handling in return.py: item not on loan, item already returned
- [x] [T083] [P] [US1] Add user-friendly error messages with bilingual support in CLI

### Integration

- [x] [T084] [US1] Register checkout, return, renew commands in `src/bcd_cli/main.py`
- [x] [T085] [US1] Test end-to-end workflow: start API server, run CLI checkout, verify database

**Dependencies**:
- T056 (checkout service) blocks T063 (checkout endpoint)
- T063 (checkout endpoint) blocks T070 (CLI checkout command)
- T071 (scanner input handling) blocks T070, T075 (interactive workflows)

**Parallel Execution Example**:
```bash
# After T056-T060 complete (all services), run T063-T068 in parallel (all endpoints)
# After T063-T068 complete, run T070-T080 in parallel (all CLI commands)
```

---

## Phase 4: User Story 2 - Cataloging with BNF API [US2-P2]

**Goal**: Add bibliographic records via ISBN lookup or manual entry

**Duration Estimate**: 10-14 hours

**User Story**: As a librarian, I can add new books to the catalog by scanning ISBN (auto-filled from BNF) or manual entry.

**Acceptance Criteria**:
- ISBN lookup: Scan ISBN → system calls BNF API → display metadata → confirm or override → create record + item
- Manual entry: Interactive form with all fields → validation → create record + item
- CSV import: Upload CSV file → validate → create records + items → report (100 records in <30s)

**Prerequisites**: Phase 2 complete

### BNF API Integration

- [x] [T086] [BLOCKING] [US2] Create `src/bcd_api/services/bnf_service.py` with search_by_isbn() function
- [x] [T087] [US2] Implement UNIMARC XML parsing in bnf_service.py using pymarc library
- [x] [T088] [US2] Add field mapping in bnf_service.py: UNIMARC tag 010→isbn, 200→title, 101→language, 215→page_count
- [x] [T089] [US2] Add BNF API error handling: ISBN not found (0 records), timeout, server error
- [x] [T090] [US2] Implement response caching in `src/bcd_api/core/cache.py` with 7-day TTL (optional)
- [x] [T091] [US2] Add rate limiting (1 req/sec) in bnf_service.py

### Service Layer

- [x] [T092] [BLOCKING] [US2] Create `src/bcd_api/services/catalog_service.py` with create_bibliographic_record() function
- [x] [T093] [US2] Implement create_item() in catalog_service.py
- [x] [T094] [US2] Implement search_bibliographic_records() in catalog_service.py with filters (title, author, ISBN, language)
- [x] [T095] [US2] Add duplicate ISBN validation in create_bibliographic_record()
- [x] [T096] [US2] Add duplicate item_id validation in create_item()

### API Endpoints

- [x] [T097] [BLOCKING] [US2] Create `src/bcd_api/api/v1/catalog.py` with POST /catalog/bibliographic endpoint
- [x] [T098] [US2] Add ISBN lookup mode in POST /catalog/bibliographic (check BNF if ISBN provided)
- [x] [T099] [US2] Implement GET /catalog/bibliographic/{id} endpoint
- [x] [T100] [US2] Implement GET /catalog/bibliographic/search endpoint with query parameters
- [x] [T101] [US2] Implement POST /catalog/items endpoint for creating items
- [x] [T102] [US2] Register catalog router in `src/bcd_api/api/v1/router.py`

### CLI Commands

- [x] [T103] [BLOCKING] [US2] Create `src/bcd_cli/commands/catalog.py` with `bcd catalog add` command
- [x] [T104] [US2] Implement ISBN lookup workflow in catalog.py: scan ISBN → show BNF data → confirm/override
- [x] [T105] [US2] Implement manual entry workflow with interactive form (all bibliographic fields)
- [x] [T106] [US2] Add item creation prompt after bibliographic record creation
- [x] [T107] [US2] Implement `bcd catalog search` command with filters (--title, --author, --isbn, --language)
- [x] [T108] [US2] Add search results display with Rich tables

### CSV Import

- [x] [T109] [BLOCKING] [US2] Create `src/bcd_api/services/import_service.py` with import_catalog_csv() function
- [x] [T110] [US2] Implement CSV parsing with pandas in import_service.py (21 fields)
- [x] [T111] [US2] Add row validation: required fields (Titre, Inventaire), ISBN format, Empruntable values
- [x] [T112] [US2] Implement grouping by ISBN/Titre: one BiblographicRecord per unique title
- [x] [T113] [US2] Add duplicate handling: skip duplicate item IDs, append items to existing records
- [x] [T114] [US2] Implement POST /catalog/import endpoint with multipart/form-data
- [x] [T115] [US2] Create `bcd catalog import <file.csv>` CLI command with progress bar
- [x] [T116] [US2] Add import summary report: records created, items created, skipped, errors

**Dependencies**:
- T086 (BNF service) blocks T097-T098 (catalog endpoints with ISBN lookup)
- T092 (catalog service) blocks T097 (catalog endpoint)
- T109 (import service) blocks T114 (import endpoint)

**Parallel Execution Example**:
```bash
# After T086-T091 complete, run T092-T096 in parallel (catalog service functions)
# After T092 completes, run T097-T101 in parallel (all catalog endpoints)
```

---

## Phase 5: User Story 3 - Borrower and Class Management [US3-P3]

**Goal**: Manage borrowers (students, teachers, staff) and class groupings

**Duration Estimate**: 8-10 hours

**User Story**: As a librarian, I can add borrowers, organize them by class, import from CSV, and view their status.

**Acceptance Criteria**:
- Add borrower: Interactive form or direct command → generate barcode → save
- List borrowers: Filter by class, role, active/blocked status
- CSV import: Upload student CSV → validate → create borrowers → report (217 students in <10s)
- View borrower details: Current loans, history, statistics

**Prerequisites**: Phase 2 complete

### Service Layer

- [x] [T117] [BLOCKING] [US3] Create `src/bcd_api/services/borrower_service.py` with create_borrower() function
- [x] [T118] [US3] Implement list_borrowers() in borrower_service.py with filters (class_id, role, active)
- [x] [T119] [US3] Implement get_borrower_details() with current loans and statistics
- [x] [T120] [US3] Add borrower_id uniqueness validation in create_borrower()
- [x] [T121] [US3] Add ID format validation (regex from SystemSettings) in borrower_service.py
- [x] [T122] [BLOCKING] [US3] Create `src/bcd_api/services/class_service.py` with create_class(), list_classes() functions
- [x] [T123] [US3] Implement barcode generation in `src/shared/barcode_utils.py` using python-barcode (Code 39)

### API Endpoints

- [x] [T124] [BLOCKING] [US3] Create `src/bcd_api/api/v1/borrowers.py` with GET /borrowers and POST /borrowers endpoints
- [x] [T125] [US3] Implement GET /borrowers/{borrower_id} endpoint
- [x] [T126] [US3] Create `src/bcd_api/api/v1/classes.py` with GET /classes and POST /classes endpoints
- [x] [T127] [US3] Register borrowers and classes routers in `src/bcd_api/api/v1/router.py`

### CLI Commands

- [x] [T128] [BLOCKING] [US3] Create `src/bcd_cli/commands/borrower.py` with `bcd borrower add` command (interactive and direct)
- [x] [T129] [US3] Implement `bcd borrower list` command with filters (--class, --role, --active, --blocked)
- [x] [T130] [US3] Implement `bcd borrower show <id>` command with current loans and history display
- [x] [T131] [US3] Add Rich table display for borrower list with status indicators

### CSV Import

- [x] [T132] [BLOCKING] [US3] Implement import_borrowers_csv() in `src/bcd_api/services/import_service.py`
- [x] [T133] [US3] Add CSV parsing for borrower format: StudentID, FirstName, LastName, Class, BlockReason
- [x] [T134] [US3] Implement class auto-creation or lookup by name during import
- [x] [T135] [US3] Add duplicate StudentID handling: skip with warning
- [x] [T136] [US3] Implement POST /borrowers/import endpoint
- [x] [T137] [US3] Create `bcd borrower import <file.csv>` CLI command with progress bar and summary

**Dependencies**:
- T122 (class service) may be needed by T117 (borrower service) for class validation
- T117 (borrower service) blocks T124 (borrowers endpoints)
- T123 (barcode utils) needed by T117 (create_borrower)

**Parallel Execution Example**:
```bash
# After T117, T122, T123 complete, run T124-T126 in parallel (all endpoints)
# After T124 completes, run T128-T131 in parallel (all CLI commands)
```

---

## Phase 6: User Story 4 - Catalog Search [US4-P4]

**Goal**: Search bibliographic records with filters and view item availability

**Duration Estimate**: 6-8 hours

**User Story**: As a librarian, I can search the catalog by title, author, ISBN, category, language, and see which items are available.

**Acceptance Criteria**:
- Search: Multiple filters → display results with availability → select item to view details
- Performance: Search 5000 records in <2s

**Prerequisites**: Phase 4 complete (catalog endpoints exist), Phase 2 complete

### Service Layer Enhancements

- [x] [T138] [US4] Enhance search_bibliographic_records() in catalog_service.py with full-text search (PostgreSQL tsvector)
- [x] [T139] [US4] Add pagination support (limit, offset) in search function
- [x] [T140] [US4] Implement get_items_for_bibliographic_record() in catalog_service.py with availability status

### API Endpoint Enhancements

- [x] [T141] [US4] Enhance GET /catalog/bibliographic/search with all filter parameters (q, title, author, ISBN, category, genre, language, target_audience)
- [x] [T142] [US4] Add pagination to search endpoint response (total, limit, offset)
- [x] [T143] [US4] Implement GET /catalog/bibliographic/{id}/items endpoint showing all copies with status

### CLI Commands

- [x] [T144] [BLOCKING] [US4] Enhance `bcd catalog search` in catalog.py with all filter options
- [x] [T145] [US4] Add pagination in CLI search results (show 20 results, "Show more?" prompt)
- [x] [T146] [US4] Implement item availability display in search results (X/Y available)
- [x] [T147] [US4] Add `bcd item status <item_id>` command in new `src/bcd_cli/commands/item.py`
- [x] [T148] [US4] Implement `bcd item history <item_id>` command showing circulation history

### Database Optimization

- [x] [T149] [P] [US4] Create full-text search index on bibliographic_record (title + authors) in migration
- [x] [T150] [P] [US4] Add composite index on (category, genre, language) in migration
- [x] [T151] [P] [US4] Verify all foreign key indexes exist for join performance

**Dependencies**:
- T138-T140 (service enhancements) block T141-T143 (endpoint enhancements)
- T141-T143 (endpoints) block T144-T148 (CLI commands)

**Parallel Execution Example**:
```bash
# Run T138-T140 in parallel (independent service functions)
# Run T149-T151 in parallel (all database optimizations)
```

---

## Phase 7: User Story 5 - Reports and Statistics [US5-P5]

**Goal**: Generate overdue reports, circulation statistics, and never-borrowed reports

**Duration Estimate**: 8-10 hours

**User Story**: As a librarian, I can generate reports for overdue items (by class), never-borrowed titles, and most borrowed titles.

**Acceptance Criteria**:
- Overdue report: Generate by class → display in table → export to PDF for distribution
- Never-borrowed: Show titles with 0 circulations this academic year
- Most borrowed: Top 20 titles by circulation count (configurable period)
- Performance: Generate report for 15 classes in <10s

**Prerequisites**: Phase 3 complete (circulation data exists), Phase 2 complete

### Service Layer

- [x] [T152] [BLOCKING] [US5] Create `src/bcd_api/services/report_service.py` with generate_overdue_report() function
- [x] [T153] [US5] Implement generate_never_borrowed_report() in report_service.py
- [x] [T154] [US5] Implement generate_most_borrowed_report() with period filter (week, month, year, all-time)
- [x] [T155] [US5] Add report caching for expensive queries (academic year reports)
- [x] [T156] [US5] Implement academic year calculation in `src/shared/date_utils.py` (Sept-Aug)

### API Endpoints

- [x] [T157] [BLOCKING] [US5] Create `src/bcd_api/api/v1/reports.py` with GET /reports/overdue endpoint
- [x] [T158] [US5] Implement GET /reports/never-borrowed endpoint
- [x] [T159] [US5] Implement GET /reports/most-borrowed endpoint with query params (limit, period)
- [x] [T160] [US5] Add format parameter to overdue endpoint (json or pdf)
- [x] [T161] [US5] Register reports router in `src/bcd_api/api/v1/router.py`

### PDF Generation

- [x] [T162] [BLOCKING] [US5] Create `src/bcd_api/utils/pdf_generator.py` with generate_overdue_pdf() using ReportLab
- [x] [T163] [US5] Implement PDF layout: one page per class, table with columns (Borrower, Item ID, Title, Due Date, Days Overdue)
- [x] [T164] [US5] Add bilingual headers (French/English) in PDF

### CLI Commands

- [x] [T165] [BLOCKING] [US5] Create `src/bcd_cli/commands/report.py` with `bcd report overdue` command
- [x] [T166] [US5] Add class filter option to overdue command (--class "CP-A")
- [x] [T167] [US5] Add PDF output option: `bcd report overdue --format pdf --output overdue.pdf`
- [x] [T168] [US5] Implement `bcd report never-borrowed` command with Rich table display
- [x] [T169] [US5] Implement `bcd report most-borrowed` command with period option (--period month)

### Database Views

- [x] [T170] [P] [US5] Create database view `active_loans` in migration for performance
- [x] [T171] [P] [US5] Create database view `overdue_items` in migration
- [x] [T172] [P] [US5] Create database view `available_items` in migration

**Dependencies**:
- T152-T154 (report services) block T157-T159 (report endpoints)
- T162 (PDF generator) blocks T160 (PDF format in endpoint) and T167 (PDF in CLI)
- T157-T161 (endpoints) block T165-T169 (CLI commands)

**Parallel Execution Example**:
```bash
# After T152-T156 complete, run T157-T161 and T162-T164 in parallel
# Run T170-T172 in parallel (all database views)
```

---

## Phase 8: User Story 6 - Barcode Printing [US6-P6]

**Goal**: Generate printable barcode labels for borrowers and items

**Duration Estimate**: 4-6 hours

**User Story**: As a librarian, I can generate PDF sheets of barcode labels for borrowers and items using standard label formats.

**Acceptance Criteria**:
- Generate barcode labels: Select borrower IDs or item IDs → generate PDF → print on Avery 5160 label sheets
- Support Code 39 and Code 128 (configurable)

**Prerequisites**: Phase 5 complete (borrowers and items exist), Phase 2 complete

### Barcode Utilities

- [x] [T173] [BLOCKING] [US6] Enhance `src/shared/barcode_utils.py` with generate_barcode_image() for both Code 39 and Code 128
- [x] [T174] [US6] Add barcode type configuration reading from SystemSettings in barcode_utils.py
- [x] [T175] [US6] Implement barcode validation (valid characters for Code 39/128)

### PDF Generation

- [x] [T176] [BLOCKING] [US6] Create `src/bcd_api/utils/barcode_pdf.py` with generate_barcode_sheet() function
- [x] [T177] [US6] Implement Avery 5160 layout (30 labels per page, 3 columns, 10 rows) in barcode_pdf.py
- [x] [T178] [US6] Add borrower label format: barcode + name + ID text below
- [x] [T179] [US6] Add item label format: barcode + title (truncated) + call number

### API Endpoint

- [x] [T180] [BLOCKING] [US6] Create `src/bcd_api/api/v1/admin.py` with POST /admin/barcodes/generate endpoint
- [x] [T181] [US6] Add request schema: borrower_ids or item_ids array
- [x] [T182] [US6] Implement PDF generation in endpoint, return binary PDF
- [x] [T183] [US6] Register admin router in `src/bcd_api/api/v1/router.py`

### CLI Command

- [x] [T184] [BLOCKING] [US6] Create `src/bcd_cli/commands/admin.py` with `bcd admin barcode-generate` command
- [x] [T185] [US6] Add options: --borrowers <id1,id2>, --items <id1,id2>, --class "CP-A", --output file.pdf
- [x] [T186] [US6] Implement class-based generation: fetch all borrower IDs in class, generate PDF

**Dependencies**:
- T173-T175 (barcode utils) block T176-T179 (PDF generation)
- T176-T179 (PDF) block T180 (endpoint)
- T180-T183 (endpoint) block T184-T186 (CLI)

**Parallel Execution Example**:
```bash
# After T173-T175 complete, run T176-T179 in parallel
# After T180 completes, run T184-T186 in parallel
```

---

## Phase 9: Polish and Cross-Cutting Concerns

**Goal**: Internationalization, configuration, performance tuning, documentation, database hardening

**Duration Estimate**: 12-16 hours

**Prerequisites**: All user story phases complete

**Priority**: Database tasks (backup, archive, indexes) are CRITICAL for production readiness

### System Settings Management

- [ ] [T187] [BLOCKING] Create `src/bcd_api/services/settings_service.py` with get_settings(), update_settings() functions
- [ ] [T188] Implement GET /admin/settings and PUT /admin/settings endpoints in admin.py
- [ ] [T189] Create `bcd admin settings` CLI command to view settings
- [ ] [T190] Add `bcd admin settings --set <key>=<value>` option for updates

### Database Backup (CRITICAL - Spec FR-048)

**Requirement**: System MUST support backup and restore (spec.md FR-048)

- [x] [T191] [BLOCKING] Create `src/bcd_api/services/backup_service.py` with comprehensive backup functions:
  - `create_backup(output_path=None)` - Copy SQLite file with timestamp (bcd_backup_YYYYMMDD_HHMMSS.db)
  - `restore_backup(backup_file)` - Restore from backup file with validation
  - `list_backups(backup_dir='./backups')` - List available backups with metadata (size, date)
  - `cleanup_old_backups(keep_days=30)` - Remove backups older than N days
  - `verify_backup(backup_file)` - Integrity check using SQLite PRAGMA integrity_check
- [x] [T192] Implement POST /admin/backup endpoint in `src/bcd_api/api/v1/admin.py`:
  - Returns backup file as binary download (application/x-sqlite3)
  - Optional query param: ?auto=true (saves to ./backups/ directory)
  - Response headers: Content-Disposition with filename
- [x] [T193] Implement GET /admin/backups endpoint to list available backups with metadata
- [x] [T194] Implement POST /admin/restore endpoint (requires confirmation, dangerous operation)
- [x] [T195] Create `bcd admin backup` CLI command in `src/bcd_cli/commands/admin.py`:
  - Default: `bcd admin backup` (creates ./backups/bcd_backup_YYYYMMDD_HHMMSS.db)
  - Custom path: `bcd admin backup --output /path/to/backup.db`
  - Auto mode: `bcd admin backup --auto` (includes timestamp)
- [x] [T196] Create `bcd admin restore <backup-file>` CLI command with safety confirmation
- [x] [T197] Create `bcd admin list-backups` CLI command showing backup files with size and age
- [x] [T198] [P] Add automated backup documentation to `docs/backup-recovery.md`:
  - Backup procedures (manual and automated)
  - Restore procedures with step-by-step instructions
  - Recommended backup schedule (daily before closing)
  - Offsite backup recommendations
  - Recovery time objective (RTO) estimates

### Database Archive Strategy (HIGH - Spec FR-049)

**Requirement**: System MUST support clearing old data to prevent unbounded growth (spec.md FR-049)

**Problem**: CirculationTransaction grows indefinitely (18k/year × 10 years = 180k rows) causing performance degradation

- [ ] [T199] [BLOCKING] Create migration `migrations/versions/002_add_archive_table.py`:
  - Create `circulation_transaction_archive` table (same schema as circulation_transaction)
  - Add `archived_at` TIMESTAMP column
  - Add indexes on archive table for queries
- [ ] [T200] Create `src/bcd_api/services/archive_service.py` with archive functions:
  - `archive_old_transactions(older_than_years=5, dry_run=False)` - Move transactions to archive
  - `get_archived_transactions(borrower_id=None, item_id=None)` - Query archived data
  - `get_archive_stats()` - Statistics (count, oldest, newest, size saved)
  - Include transaction isolation for atomic archive operations
- [ ] [T201] Implement GET /admin/archive/stats endpoint showing archivable transaction count
- [ ] [T202] Implement POST /admin/archive endpoint with parameters (older_than_years, dry_run)
- [ ] [T203] Create `bcd admin archive` CLI command:
  - `bcd admin archive --older-than 5years` (default: 5 years)
  - `bcd admin archive --dry-run` (show what would be archived without doing it)
  - Display progress bar with Rich for long-running archives
  - Show summary: archived count, active table size reduction
- [ ] [T204] [P] Update borrower history views to include archived transactions with "(archived)" indicator
- [ ] [T205] [P] Add documentation to `docs/data-retention.md`:
  - Archive strategy and schedule recommendations
  - How to query archived data
  - Performance impact of archiving

### Database Performance Optimization (HIGH)

**Goal**: Add missing indexes identified in database architecture review

- [ ] [T206] [BLOCKING] Create migration `migrations/versions/003_add_composite_indexes.py`:
  - Add composite index: `idx_circ_borrower_return_due` on `(borrower_id, return_date, due_date)` for overdue queries
  - Add composite index: `idx_biblio_category_genre_lang` on `(category, genre, language)` for search filters
  - Add partial unique index: `idx_unique_active_loan` on `(item_id)` WHERE `return_date IS NULL` (prevents duplicate active loans)
  - Document rationale for each index in migration comments
- [ ] [T207] [P] Create performance testing script `scripts/benchmark_queries.py`:
  - Test overdue loan query performance (target: <50ms)
  - Test catalog search with filters (target: <100ms)
  - Compare before/after index creation
  - Generate performance report
- [ ] [T208] [P] Add index verification to CI pipeline:
  - Script to check all foreign keys have indexes
  - Fail CI if missing indexes detected on large tables

### Database Integrity Constraints (MEDIUM)

**Goal**: Add database-level enforcement for business rules

- [ ] [T209] Update migration `003_add_composite_indexes.py` to include constraint:
  - Add CHECK constraint on `bibliographic_record.publication_year`: `year >= 1000 AND year <= CURRENT_YEAR + 2`
  - Add CHECK constraint on `bibliographic_record.page_count`: `page_count > 0 OR page_count IS NULL`
  - Update error handling in `circulation_service.py` to catch IntegrityError from duplicate active loans
  - Add test case verifying constraint prevents duplicate active loans

### Database Security Hardening (MEDIUM - Production Only)

**Goal**: Encrypt database file for production deployment

- [ ] [T210] [P] Document database encryption options in `docs/security.md`:
  - Option 1: File-system encryption (LUKS/BitLocker) - Recommended for simple deployment
  - Option 2: SQLCipher - For application-level encryption
  - Option 3: PostgreSQL pgcrypto - For PostgreSQL migration
  - Include key management recommendations
  - Document performance impact of each option
- [ ] [T211] [P] Create encryption setup guide in `docs/production-deployment.md`:
  - SQLCipher installation steps
  - Environment variable configuration for encryption key
  - Key rotation procedure
  - Backup encryption requirements

### Database Technical Debt (LOW)

**Goal**: Fix deprecated Python datetime usage (Python 3.12+ compatibility)

- [ ] [T212] Fix deprecated `datetime.utcnow()` across all models:
  - Update `src/bcd_api/models/item.py:43`
  - Update `src/bcd_api/models/bibliographic_record.py:63-64`
  - Update `src/bcd_api/models/borrower.py:35-36`
  - Update `src/bcd_api/models/circulation.py:52-53`
  - Update `src/bcd_api/models/hold.py:51-52`
  - Update `src/bcd_api/models/class_model.py:26-27`
  - Update `src/bcd_api/models/system_settings.py:60-61`
  - Replace: `default=datetime.utcnow` with `default=lambda: datetime.now(timezone.utc)`
  - Verify no deprecation warnings in Python 3.12+

### Query Performance Monitoring (LOW - Production Nice-to-Have)

**Goal**: Visibility into slow queries in production

- [ ] [T213] [P] Create `src/bcd_api/core/query_monitoring.py`:
  - SQLAlchemy event listeners for before/after query execution
  - Log queries slower than configurable threshold (default: 100ms)
  - Include query text, parameters, execution time
  - Structured logging format (JSON) for log aggregation
- [ ] [T214] [P] Add query monitoring configuration to `src/bcd_api/core/config.py`:
  - `SLOW_QUERY_THRESHOLD_MS: int = 100`
  - `ENABLE_QUERY_LOGGING: bool = False` (enable in production)
  - Enable only for non-SQLite or DEBUG mode
- [ ] [T215] [P] Add query monitoring documentation to `docs/monitoring.md`:
  - How to enable query logging
  - How to analyze slow query logs
  - Common performance issues and solutions

### Internationalization (i18n)

- [ ] [T216] [BLOCKING] Create `src/bcd_cli/utils/i18n.py` with gettext initialization
- [ ] [T217] Extract translatable strings from CLI commands using `xgettext`
- [ ] [T218] Create `locale/fr/LC_MESSAGES/bcd.po` with French translations
- [ ] [T219] Create `locale/en/LC_MESSAGES/bcd.po` with English translations
- [ ] [T220] Add language selection in `bcd config --language fr|en`
- [ ] [T221] Compile translations with `msgfmt` to .mo files

### Configuration Management

- [ ] [T222] [P] Implement `bcd config` command showing current configuration in `src/bcd_cli/commands/config.py`
- [ ] [T223] [P] Add `bcd config --api-url <url>` to set API endpoint
- [ ] [T224] [P] Add `bcd config --timeout <seconds>` for API timeout configuration

### Application Performance Optimization

- [ ] [T225] [P] Add database connection pooling configuration in `src/bcd_api/core/database.py`
- [ ] [T226] [P] Implement query result caching for SystemSettings (read-once, cache in memory)
- [ ] [T227] [P] Add query result pagination validation (enforce max 100 records per page)
- [ ] [T228] [P] Profile and optimize API endpoint response times (target: p95 <200ms)

### Documentation

- [ ] [T229] [P] Create `docs/api.md` from OpenAPI spec (automatic via FastAPI /docs)
- [ ] [T230] [P] Create `docs/installation.md` with setup instructions
- [ ] [T231] [P] Create `docs/user-guide.md` combining quickstart.md content
- [ ] [T232] [P] Add inline code documentation (docstrings) to all public functions

### Error Handling and Logging

- [ ] [T233] [P] Create `src/bcd_api/core/logging.py` with structured logging configuration
- [ ] [T234] [P] Add request/response logging middleware to FastAPI app
- [ ] [T235] [P] Add error logging in all service layer functions
- [ ] [T236] [P] Create `src/bcd_cli/utils/error_handler.py` for pretty CLI error display

**Parallel Execution Examples**:
```bash
# HIGH PRIORITY - Run these database tasks first:
# T191-T198 (backup system) - CRITICAL, sequential
# T199-T205 (archive strategy) - HIGH, sequential (depends on migration)
# T206-T208 (performance indexes) - HIGH, can run in parallel after T199

# MEDIUM PRIORITY - Can run in parallel after database tasks:
# T210-T211 (security docs) - parallel
# T213-T215 (query monitoring) - parallel
# T222-T224 (config commands) - parallel
# T229-T232 (documentation) - parallel

# Run T216-T221 (i18n) sequentially (translations depend on extraction)
# Run T233-T236 (logging) in parallel
```

**Database Task Priority**:
1. **CRITICAL (Week 1)**: T191-T198 (Backup system) - No production deployment without backups
2. **HIGH (Week 2)**: T199-T205 (Archive strategy) - Prevents performance degradation
3. **HIGH (Week 2)**: T206-T208 (Performance indexes) - 4x query speedup
4. **MEDIUM (Week 3)**: T209 (Constraints), T212 (Datetime fixes)
5. **LOW (Later)**: T210-T211 (Security docs), T213-T215 (Query monitoring)

---

## Dependency Graph

### User Story Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
    ├─→ Phase 3 (US1: Circulation) [HIGHEST PRIORITY]
    │       ↓
    │   Phase 7 (US5: Reports) [depends on circulation data]
    │
    ├─→ Phase 4 (US2: Cataloging) [CAN RUN IN PARALLEL with Phase 3]
    │       ↓
    │   Phase 6 (US4: Search) [depends on catalog data]
    │
    ├─→ Phase 5 (US3: Borrowers) [CAN RUN IN PARALLEL with Phase 3, 4]
    │       ↓
    │   Phase 8 (US6: Barcodes) [depends on borrower data]
    │
    └─→ All phases complete
            ↓
        Phase 9 (Polish)
```

### Critical Path

**Longest path** (determines minimum project duration):
```
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 7 (US5) → Phase 9
Estimate: 3h + 8h + 16h + 10h + 8h = 45 hours
```

**Parallel optimization** (if working on US1, US2, US3 simultaneously):
```
Phase 1 → Phase 2 → [Phase 3 + Phase 4 + Phase 5 in parallel] → [Phase 6 + Phase 7 + Phase 8] → Phase 9
Estimate: 3h + 8h + 16h (max of 3,4,5) + 10h (max of 6,7,8) + 8h = 45 hours
```

---

## Testing Strategy

**Note**: Testing is optional per spec.md. If tests are required, add these tasks:

### Unit Tests (Optional)

- [ ] [T-TEST-001] [P] Create pytest fixtures for database session in `tests/conftest.py`
- [ ] [T-TEST-002] [P] Write unit tests for circulation_service.py in `tests/api/services/test_circulation.py`
- [ ] [T-TEST-003] [P] Write unit tests for catalog_service.py
- [ ] [T-TEST-004] [P] Write unit tests for borrower_service.py
- [ ] [T-TEST-005] [P] Write unit tests for bnf_service.py with mocked HTTP responses

### Integration Tests (Optional)

- [ ] [T-TEST-006] Create integration test for checkout workflow in `tests/integration/test_checkout.py`
- [ ] [T-TEST-007] Create integration test for catalog import with sample CSV
- [ ] [T-TEST-008] Create integration test for overdue report generation
- [ ] [T-TEST-009] Create end-to-end test: API server + CLI commands

**If tests are implemented**, add pytest configuration in Phase 1 (T019) and run tests after each phase.

---

## Summary

**Total Estimated Duration**: 50-65 hours (single developer, sequential) or 35-45 hours (with parallelization)

**Database Hardening Duration**: Additional 8-12 hours in Phase 9 for production readiness

**Phases by User Story Priority**:
1. **Phase 3** (US1-P1: Circulation) - CRITICAL, blocks reports
2. **Phase 4** (US2-P2: Cataloging) - HIGH, independent from Phase 3
3. **Phase 5** (US3-P3: Borrowers) - HIGH, independent from Phase 3, 4
4. **Phase 6** (US4-P4: Search) - MEDIUM, depends on Phase 4
5. **Phase 7** (US5-P5: Reports) - MEDIUM, depends on Phase 3
6. **Phase 8** (US6-P6: Barcodes) - LOW, depends on Phase 5

**Recommended Implementation Order**:
1. Complete Phase 1 (Setup) and Phase 2 (Foundational) first [BLOCKING]
2. Start Phase 3 (Circulation) immediately after Phase 2 [PRIORITY 1]
3. Start Phase 4 (Cataloging) in parallel with Phase 3 [PRIORITY 2]
4. Start Phase 5 (Borrowers) in parallel with Phase 3, 4 [PRIORITY 3]
5. Complete Phase 6 (Search) after Phase 4
6. Complete Phase 7 (Reports) after Phase 3
7. Complete Phase 8 (Barcodes) after Phase 5
8. Final Phase 9 (Polish) after all user stories complete

**Parallelization Opportunities**:
- Phase 1: T001-T005, T006-T009, T018-T020 (all setup tasks)
- Phase 2: T032-T038 (all ORM models after T031)
- Phase 3: T052-T055 (schemas), T063-T068 (endpoints after services), T077-T080 (CLI direct modes)
- Phase 4: T086-T091 (BNF integration), T097-T101 (endpoints)
- Phase 5: T124-T126 (endpoints), T128-T131 (CLI commands)
- Phase 9: Database tasks in priority order (T191-T215), then other polish tasks in parallel

---

**Last Updated**: 2026-02-05
**Status**: Ready for implementation - All design artifacts complete

---

## Phase 9 Database Improvements Summary

**Added in 2026-02-05 update**: Comprehensive database hardening tasks based on architecture review

### Critical Production Requirements (Must Complete Before Launch)

1. **Backup System (T191-T198)** - FR-048 compliance
   - Automated backup with restore capability
   - Verification and cleanup procedures
   - Recovery documentation

2. **Archive Strategy (T199-T205)** - FR-049 compliance
   - Prevents unbounded database growth
   - 5-year archival policy
   - Maintains query performance long-term

3. **Performance Indexes (T206-T208)**
   - 4x speedup on overdue loan queries
   - Optimized catalog search
   - Prevents duplicate active loans (data integrity)

### Recommended Production Improvements

4. **Security Hardening (T210-T211)**
   - Database encryption options documented
   - Production deployment guide

5. **Query Monitoring (T213-T215)**
   - Slow query detection
   - Production performance visibility

6. **Technical Debt (T212)**
   - Python 3.12+ compatibility
   - Remove deprecation warnings

### Implementation Priority

**Week 1 (CRITICAL)**:
- T191-T198: Backup system → No production without backups!

**Week 2 (HIGH)**:
- T199-T205: Archive strategy → Prevents 5-10 year performance issues
- T206-T208: Performance indexes → Immediate query speedup

**Week 3+ (MEDIUM/LOW)**:
- T209: Additional constraints
- T210-T215: Security & monitoring docs
- T212: Datetime fixes

**Total Additional Effort**: 8-12 hours for database hardening
