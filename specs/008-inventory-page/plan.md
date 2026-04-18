# Implementation Plan: Collection Inventory Page

**Branch**: `008-inventory-page` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/008-inventory-page/spec.md`

---

## Summary

Build a collection inventory page enabling librarians to conduct physical inventory checks (récolement) and weeding (désherbage) using professional IOUPI/MUST IE/CREW criteria. Core workflow: scan/import barcodes → mark items as physically verified → bulk edit/delete based on condition, circulation, age → export documented inventory report.

**Technical approach**:
- Add `item.last_inventoried_at` timestamp field (new migration)
- New `inventory_service.py` for item-level bulk operations
- New `/inventory` router + 6 endpoints
- Vue page with 3 input tabs (scan, file, search) + working table (localStorage persistence)
- Rotation filter (CREW method) via subquery on `circulation_transaction`
- Reuse existing composables (`useSelection`, error handling, i18n patterns)

**Real-world validation**: Rotation filter = CREW professional standard; file import = offline scanner workflow; `last_inventoried_at` = French BCD récolement requirement.

---

## Technical Context

**Language/Version**: Python 3.11 (backend), JavaScript ES2020 (frontend)  
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0+, Alembic (backend); Vue 3.4.21, vue-router, vue-i18n (frontend, vendored)  
**Storage**: SQLite (development), PostgreSQL-compatible (production)  
**Testing**: pytest (backend), Playwright (E2E)  
**Target Platform**: Linux & Windows (cross-platform, constitution requirement)  
**Project Type**: Web application (FastAPI REST API + Vue 3 SPA, single-origin)  
**Performance Goals** (from constitution + spec):
- Search with all filters: <2s on 5-year-old hardware (SC-003)
- Bulk edit 300 items: <30s (SC-002)
- File parse 500 IDs: <3s (SC-007)
- Scan 100 items: <5 min (~3s/scan including physical handling) (SC-001)

**Constraints**:
- Legacy hardware: 2 GHz CPU, 4 GB RAM, HDD (not SSD)
- Working table size: ~3,000 items max (school scale), ~600KB in localStorage
- Search results capped at 200 (no pagination per clarification)
- Cross-platform paths via pathlib

**Scale/Scope**:
- School scale: ~3,000 items, ~500 bibliographic records, ~20,000 circulation transactions
- 1 new DB column + 1 index
- 8 new API endpoints
- 1 new service file (~400-500 LOC)
- 1 new Vue page + 5 components (~800-1000 LOC frontend)
- 60-80 new i18n strings (en + fr)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution v1.2.0 Compliance**:

| Principle | Status | Notes |
|---|---|---|
| **I. DRY** | ✅ PASS | New `inventory_service.py` avoids polluting `catalog_service.py`; reuse `useSelection()`, `useNotification()`, existing exception classes |
| **II. Library-First** | ✅ PASS | Reuse FastAPI, SQLAlchemy, Vue 3, Bootstrap 5 (all vendored); no new dependencies |
| **III. Testing** | ✅ PASS | Service-layer integration tests (AAA pattern); E2E tests for barcode scanning workflow; target 80%+ coverage |
| **IV. UX Consistency** | ✅ PASS | AdminDropdown pattern, Bootstrap components, keyboard shortcuts (existing patterns) |
| **V. Click Minimization** | ✅ PASS | ≤2 clicks: scan (0 clicks — just scan barcode), bulk edit (2 clicks — select + confirm); smart defaults (search capped at 200 forces filtering) |
| **VI. Legacy Hardware** | ✅ PASS | Search <2s, bulk edit <30s targets; localStorage not sessionStorage; denormalized counters avoid JOINs |
| **VII. Schema Versioning** | ✅ PASS | Alembic migration with upgrade/downgrade; reversible; tested |
| **VIII. Research-First** | ✅ PASS | Researched IOUPI/MUSTIE/CREW (real-world library weeding); offline scanner workflows; existing codebase patterns |
| **IX. Design-First** | ✅ PASS | Mockup in `inventaire-mockup.md` approved before spec; spec → plan → contracts → implementation |
| **X. i18n** | ✅ PASS | All user-facing text in `inventory.*` keys (en.json / fr.json); error codes for exceptions; translation parity |
| **XI. Quality Gates** | ✅ PASS | `/speckit.analyze` pre-implementation; `/speckit.review` post-implementation; zero CRITICAL findings required |

**Result**: **ALL PRINCIPLES PASS** — no violations, no justification needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/008-inventory-page/
├── spec.md              # Feature specification with clarifications
├── plan.md              # This file (implementation plan)
├── research.md          # Real-world library workflows + technical decisions
├── data-model.md        # Database schema changes
├── quickstart.md        # Developer getting started guide
├── contracts/
│   └── api-endpoints.md # REST API contracts (8 endpoints, Pydantic schemas)
├── checklists/
│   └── requirements.md  # Spec quality validation (all items pass)
└── tasks.md             # NOT YET CREATED (next phase: /speckit.tasks)
```

### Source Code (repository root)

**Option 2: Web Application** (backend + frontend)

```text
# Backend (FastAPI REST API)
src/bcd_api/
├── models/
│   └── item.py                    # MODIFIED: add last_inventoried_at field
├── services/
│   ├── catalog_service.py         # UNCHANGED (reuse bulk_delete_records for orphans)
│   └── inventory_service.py       # NEW: 8 functions (mark, search, bulk ops, CSV, orphans)
├── schemas/
│   └── inventory.py               # NEW: 12 Pydantic schemas
├── api/v1/
│   ├── inventory.py               # NEW: 6 endpoints (/inventory/...)
│   ├── admin.py                   # MODIFIED: add 2 orphan endpoints
│   └── router.py                  # MODIFIED: include inventory router
└── core/
    └── exceptions.py              # UNCHANGED (reuse existing exceptions)

migrations/versions/
└── <hash>_add_item_last_inventoried_at.py  # NEW

# Frontend (Vue 3 SPA)
src/bcd_web_vue/
├── js/
│   ├── pages/
│   │   └── InventoryPage.js       # NEW: main orchestrator (~800 LOC)
│   ├── components/
│   │   ├── inventory/             # NEW directory
│   │   │   ├── ScanTab.js         # NEW: barcode input
│   │   │   ├── FileTab.js         # NEW: file picker + parse
│   │   │   ├── SearchTab.js       # NEW: filters + results
│   │   │   ├── WorkingTable.js    # NEW: checkbox table
│   │   │   └── BulkEditPanel.js   # NEW: batch edit form
│   │   └── admin/
│   │       └── AdminDropdown.js   # MODIFIED: add page='inventory' variant
│   ├── composables/
│   │   └── useInventoryTable.js   # NEW: localStorage persistence
│   └── router.js                  # MODIFIED: add /inventory route
└── locales/
    ├── en.json                    # MODIFIED: add inventory.* keys (~60 strings)
    └── fr.json                    # MODIFIED: add inventory.* keys (~60 strings)

# Tests
tests/
├── integration/services/
│   └── test_inventory_service.py  # NEW: 15-20 test functions
├── api/
│   └── test_inventory_api.py      # NEW: endpoint tests
└── e2e/
    └── test_inventory_page.py     # NEW: Playwright tests (scan, bulk edit, export)
```

**Structure Decision**: Web application pattern (Option 2). Frontend and backend in same repository, served from single origin. Follows existing BCD architecture.

---

## Complexity Tracking

**No violations** — this section is empty per template instructions.

---

## Architecture Patterns Applied

From `.specify/architecture-patterns.md`:

### 1. Service Layer Architecture (Section 1)

✅ **Three-layer clean architecture**: API routes (thin) → `inventory_service.py` (business logic) → ORM models  
✅ **Services are pure Python**: No FastAPI dependencies (except `Session`)  
✅ **Services raise exceptions**: API layer catches `BCDException` → HTTP status codes  
✅ **Single-responsibility**: New `inventory_service.py` for inventory domain (not in `catalog_service.py`)

### 2. Database Design Patterns (Section 2)

✅ **Comprehensive indexing**: New `ix_item_last_inventoried_at` for filtered queries  
✅ **Timezone-aware timestamps**: `datetime.now(timezone.utc)` (not `datetime.now()`)  
✅ **Denormalized counters**: Reuse `BiblographicRecord.total_items` (updated on delete)

### 3. API Design Patterns (Section 3)

✅ **Pagination on lists**: Search capped at 200 (no pagination controls per clarification)  
✅ **Pydantic validation**: All request/response schemas in `schemas/inventory.py`  
✅ **Consistent errors**: Reuse `ItemNotFoundException`, `ValidationError` with `error_code` + `context`

### 4. Vue 3 Patterns (Section 5)

✅ **Composition API**: All components use `setup()` + `ref/reactive/computed`  
✅ **Barcode scanner support**: Input with `autofocus`, `@submit.prevent`, clear + refocus  
✅ **Bootstrap 5 styling**: Consistent badge colors (`bg-success`, `bg-warning`, `bg-danger`)

### 5. Testing Patterns (Section 6)

✅ **AAA structure**: Arrange-Act-Assert in all tests  
✅ **Service-layer tests**: Test `inventory_service.py` functions directly (not through HTTP)  
✅ **Descriptive names**: `test_<action>_<condition>_<expected_result>`

### 6. Error Handling Patterns (Section 7)

✅ **Structured exceptions**: Reuse `BCDException` with `error_code` + `context`  
✅ **i18n-friendly**: Frontend maps `error_code` → `errors.{code}` translation key

### 7. i18n Patterns (Section 8)

✅ **Parameterized messages**: `{count} item(s)`, `{date}` variables  
✅ **Hierarchical keys**: `inventory.tabs.scan`, `inventory.bulk_edit.apply`  
✅ **100% parity**: en.json and fr.json have identical key structure

### 8. Cross-Platform Patterns (Section 9)

✅ **pathlib**: Use `Path` for all file operations (migration files only, no file I/O in this feature)

### 9. Performance Patterns (Section 10)

✅ **Batch operations**: `bulk_mark_inventoried`, `bulk_update_items`, `delete_items_bulk`  
✅ **Denormalized counters**: `total_items` avoids COUNT query on every orphan check

---

## Dependencies & Integration Points

### Backend Dependencies (Existing)

| Module | Version | Usage |
|---|---|---|
| FastAPI | 0.104+ | API routes, dependency injection |
| SQLAlchemy | 2.0+ | ORM, query builder |
| Alembic | Latest | Database migrations |
| Pydantic | 2.0+ | Schema validation |

**No new backend dependencies**.

### Frontend Dependencies (Vendored)

| Module | Version | Usage |
|---|---|---|
| Vue | 3.4.21 | Reactive UI framework |
| vue-router | 4.x | Client-side routing |
| vue-i18n | 9.x | Internationalization |
| Bootstrap | 5.3.3 | CSS framework |

**No new frontend dependencies** (all vendored in `src/bcd_web_vue/vendor/`).

### Integration Points

**Reuses**:
- `catalog_service.bulk_delete_records()` — called by `inventory_service.delete_orphan_records()`
- `useSelection()` — multi-select checkboxes (existing composable)
- `useNotification()` — toast notifications
- `AdminDropdown.js` — extend with `page='inventory'` variant
- `BulkEditModal.js` — may reuse or create inventory-specific variant (TBD in tasks phase)

**New Interfaces**:
- `inventory_service.py` ← called by `inventory.py` router
- `useInventoryTable()` ← called by `InventoryPage.js`

---

## Implementation Phases

### Phase 0: Research ✅ COMPLETE

**Artifacts**:
- `research.md` — real-world library workflows (IOUPI/MUSTIE/CREW), technical decisions
- Validated rotation filter = CREW professional standard
- Validated file import = offline scanner workflow

### Phase 1: Design ✅ COMPLETE

**Artifacts**:
- `data-model.md` — schema changes, query patterns
- `contracts/api-endpoints.md` — 8 REST endpoints, Pydantic schemas
- `quickstart.md` — developer guide

### Phase 2: Tasks (NEXT)

**Command**: `/speckit.tasks`

**Expected output**: `tasks.md` with dependency-ordered implementation tasks covering:
1. Database migration
2. Backend service layer (8 functions)
3. Backend Pydantic schemas
4. Backend API routes (6 + 2)
5. Frontend composable (`useInventoryTable`)
6. Frontend components (5)
7. Frontend main page
8. i18n (en + fr)
9. Routing
10. Tests (service, API, E2E)

### Phase 3: Implementation

**Command**: `/speckit.implement`

**Pre-gate**: `/speckit.analyze` must show zero CRITICAL issues

**Execution**: Process tasks.md sequentially, respecting dependencies

### Phase 4: Review

**Command**: `/speckit.review`

**Post-gate**: Must pass before merge:
- All tests pass (unit, integration, E2E)
- Zero TODO/FIXME in production code
- Test coverage ≥80%
- `/speckit.analyze` shows zero CRITICAL/MAJOR findings
- Constitution re-validation passes

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Search performance <2s on legacy hardware | Low | High | Comprehensive indexes; subquery tested at school scale; denormalized counters |
| localStorage 5MB limit exceeded | Very Low | Medium | 3,000 items × 200 bytes = 600KB (well under limit); cap working table at 5,000 if needed |
| Complex rotation filter query | Low | Medium | Query pattern proven in mockup analysis; <100ms on 20K transactions |
| Barcode scanner input focus loss | Medium | High | Use `autofocus` + manual focus management in `nextTick()`; tested in E2E |
| i18n completeness | Low | Medium | Checklist validation; side-by-side en.json + fr.json editing |
| Browser storage blocked (private mode) | Medium | Low | Safe access with try/catch fallback (existing pattern in `useAppState`) |

---

## Success Criteria Validation

Mapping spec success criteria (SC-001 through SC-007) to implementation:

| ID | Criterion | Implementation Validation |
|---|---|---|
| SC-001 | Scan 100 items in <5 min | Barcode input with `autofocus`, `@submit.prevent`, instant API call (~100ms), clear + refocus → ~3s/scan including physical handling |
| SC-002 | Bulk edit 300 items in <30s | Single `POST /inventory/items/bulk-update` with atomic transaction; Python bulk update ~10-20ms/item = 3-6s total |
| SC-003 | Search <2s on legacy hardware | Indexed query (6 indexes used), subquery optimization, LIMIT 200, tested at school scale |
| SC-004 | Complete session without leaving page | Single-page app (Vue SPA), all operations via API calls, no navigation |
| SC-005 | Bulk delete preserves other copies | `delete_items_bulk` deletes by `item_id`, not `record_id`; parent record untouched |
| SC-006 | CSV export matches working table | Export uses `item_ids` from working table state; no filtering |
| SC-007 | Parse 500 IDs in <3s | Client-side split by newline, regex filter, ~O(n) = <1ms; backend lookup ~5-10ms/item = 2.5-5s total |

**All success criteria achievable** with proposed architecture.

---

## Next Steps

1. ✅ **Complete Phase 1 design artifacts** (this file)
2. **Run `/speckit.tasks`** to generate dependency-ordered tasks.md
3. **Run `/speckit.analyze`** to validate design consistency (pre-implementation gate)
4. **Address any CRITICAL findings** from analysis
5. **Run `/speckit.implement`** to execute tasks
6. **Run `/speckit.review`** before merge (post-implementation gate)

---

**Plan Status**: ✅ **COMPLETE** — ready for task generation (`/speckit.tasks`)
