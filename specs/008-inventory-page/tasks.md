# Tasks: Collection Inventory Page

**Feature Branch**: `008-inventory-page`  
**Input**: Design documents from `/specs/008-inventory-page/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md

**Tests**: Integration tests for service layer included. E2E tests for critical user workflows included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization (already complete - existing BCD codebase)

✅ Project structure already exists  
✅ FastAPI, SQLAlchemy, Vue 3 dependencies already configured  
✅ Testing framework already set up

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Migration

- [X] T001 Create Alembic migration file for `item.last_inventoried_at` column in migrations/versions/
- [X] T002 Write upgrade() function: add `last_inventoried_at DateTime nullable` with index `ix_item_last_inventoried_at`
- [X] T003 Write downgrade() function: drop index and column
- [X] T004 Apply migration with `alembic upgrade head` and verify schema

### Backend — Pydantic Schemas (All User Stories Depend On This)

- [X] T005 [P] Create `src/bcd_api/schemas/inventory.py` with all 12 Pydantic schemas from contracts/api-endpoints.md
- [X] T006 [P] Add `ItemInventoryResponse`, `BulkInventoryRequest`, `BulkInventoryResponse` schemas
- [X] T007 [P] Add `InventoryItemResult`, `InventorySearchResponse` schemas
- [X] T008 [P] Add `ItemUpdates`, `RecordUpdates`, `BulkUpdateRequest`, `BulkUpdateResponse` schemas
- [X] T009 [P] Add `BulkDeleteRequest`, `BulkDeleteResponse` schemas
- [X] T010 [P] Add `ExportCSVRequest`, `OrphanRecord`, `OrphanRecordsResponse`, `OrphanDeleteResponse` schemas

### Backend — Service Layer Foundation

- [X] T011 Create `src/bcd_api/services/inventory_service.py` with module docstring and imports

### Frontend — Composable (Working Table Persistence)

- [X] T012 Create `src/bcd_web_vue/js/composables/useInventoryTable.js` with localStorage persistence for working table (items array, addItem, removeItems, clearAll)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Barcode Scanning Inventory (Priority: P1) 🎯 MVP

**Goal**: Librarian scans barcodes one by one; each item appears in working table with inventory date updated

**Independent Test**: Scan several barcodes in sequence, verify items appear in table with `last_inventoried_at` set, handle unknown barcodes, duplicate scans, and scanning while different tab is visible

### Backend — Service Layer for US1

- [X] T013 [US1] Implement `mark_item_inventoried(db, item_id)` in inventory_service.py — fetch item by item_id, set `last_inventoried_at = datetime.now(timezone.utc)`, commit, return item

### Backend — API Route for US1

- [X] T014 [US1] Create `src/bcd_api/api/v1/inventory.py` router with `/inventory` prefix and `inventory` tag
- [X] T015 [US1] Implement `PATCH /inventory/items/{item_id}` endpoint — calls `mark_item_inventoried`, returns `ItemInventoryResponse`, raises `ItemNotFoundException` on 404
- [X] T016 [US1] Add inventory router to `src/bcd_api/api/v1/router.py` via `api_router.include_router(inventory.router)`

### Frontend — Scanner Tab Component for US1

- [X] T017 [P] [US1] Create `src/bcd_web_vue/js/components/inventory/ScanTab.js` with autofocus input, @submit.prevent, clear+refocus after scan
- [X] T018 [US1] Implement barcode scan handler — calls `PATCH /inventory/items/{item_id}`, adds item to working table via `useInventoryTable`, handles ItemNotFoundException with error notification

### Frontend — Working Table Component for US1

- [X] T019 [P] [US1] Create `src/bcd_web_vue/js/components/inventory/WorkingTable.js` with checkbox column, sequential number, barcode, truncated title, condition columns
- [X] T020 [US1] Implement header checkbox (select all/deselect all/indeterminate states) via `useSelection` composable
- [X] T021 [US1] Implement row highlight + move-to-top when duplicate barcode scanned

### Frontend — Main Inventory Page for US1

- [X] T022 [US1] Create `src/bcd_web_vue/js/pages/InventoryPage.js` with 3-tab structure (Scanner/File/Search), import all composables (useI18n, useRoute, useAppState, useNotification, useErrorHandler, useSelection, useInventoryTable)
- [X] T023 [US1] Implement tab state management (activeTab ref), working table rendering, scanner tab integration

### i18n for US1

- [X] T024 [P] [US1] Add `inventory.*` keys to `src/bcd_web_vue/locales/en.json` — title, tabs.scan, tabs.file, tabs.search, working_table.*, errors.*
- [X] T025 [P] [US1] Add `inventory.*` keys to `src/bcd_web_vue/locales/fr.json` with French translations (maintain 100% parity with en.json)

### Routing for US1

- [X] T026 [US1] Add `/inventory` route to `src/bcd_web_vue/js/router.js` pointing to InventoryPage component
- [X] T027 [US1] Add inventory navigation link to NavigationMenu.js with `bi-box-seam` icon

### Tests for US1

- [X] T028 [P] [US1] Integration test `test_mark_item_inventoried_success` in tests/integration/services/test_inventory_service.py — verify `last_inventoried_at` is set
- [X] T029 [P] [US1] Integration test `test_mark_item_inventoried_not_found` — verify `ItemNotFoundException` raised for unknown item_id
- [ ] T030 [P] [US1] E2E test `test_scan_barcode_adds_to_table` in tests/e2e/test_inventory_page.py — scan barcode, verify row appears in working table

**Checkpoint**: User Story 1 complete — barcode scanning workflow fully functional and testable independently

---

## Phase 4: User Story 2 - Search-Based Item Discovery (Priority: P2)

**Goal**: Librarian filters items by status, condition, inventory history, rotation, category, genre, etc., then adds selection to working table

**Independent Test**: Apply various filter combinations, select results, add to working table, verify no duplicates and inventory dates updated

### Backend — Service Layer for US2

- [X] T031 [US2] Implement `search_items(db, q, status, condition, shelf_location, never_inventoried, inventoried_before, medium_type, target_audience, category, genre, level, publication_year_min, publication_year_max, max_borrows, since_date)` in inventory_service.py
- [X] T032 [US2] Build query with LEFT JOIN subquery for rotation filter (GROUP BY item_id, COUNT circulation_transaction WHERE checkout_date >= since_date)
- [X] T033 [US2] Apply all filters (item-level + record-level via JOIN), LIMIT 200, return `InventorySearchResponse` with items, total_count, displayed_count, capped flag
- [X] T034 [US2] Compute `archive_cutoff_date = MIN(checkout_date) FROM circulation_transaction` and include in response

### Backend — API Route for US2

- [X] T035 [US2] Implement `GET /inventory/items/search` endpoint with 15 optional query parameters (q, status, condition, shelf_location, never_inventoried, inventoried_before, medium_type, target_audience, category, genre, level, publication_year_min/max, max_borrows, since_date)

### Frontend — Search Tab Component for US2

- [X] T036 [P] [US2] Create `src/bcd_web_vue/js/components/inventory/SearchTab.js` with text search input, item filters (status, condition, location), record filters (support, public, category, genre, niveau, année pub)
- [X] T037 [US2] Implement inventory filters section: radio buttons for "tous/jamais/avant date", rotation filter with radio + max borrows int + since date picker
- [X] T038 [US2] Implement search results list (scrollable, capped at 200) with checkboxes, barcode, truncated title, period_loan_count column (if rotation filter active)
- [X] T039 [US2] Implement "Add selection" button — calls `POST /inventory/items/bulk-mark` with selected item_ids, adds to working table, switches to working table tab
- [X] T040 [US2] Display archive cutoff warning when `since_date < archive_cutoff_date` returned by API

### Backend — Bulk Mark Service for US2

- [X] T041 [US2] Implement `bulk_mark_inventoried(db, item_ids)` in inventory_service.py — batch update `last_inventoried_at` for all item_ids in list, return `BulkInventoryResponse` with items_updated, items_not_found, timestamp

### Backend — API Route for Bulk Mark

- [X] T042 [US2] Implement `POST /inventory/items/bulk-mark` endpoint accepting `BulkInventoryRequest` (item_ids array), returns `BulkInventoryResponse`

### i18n for US2

- [X] T043 [P] [US2] Add search filter keys to en.json — `inventory.search.*` (never_inventoried, rotation_filter, results_capped, archive_warning, etc.)
- [X] T044 [P] [US2] Add search filter keys to fr.json with French translations

### Tests for US2

- [X] T045 [P] [US2] Integration test `test_search_with_never_inventoried_filter` — verify only items with `last_inventoried_at IS NULL` returned
- [X] T046 [P] [US2] Integration test `test_search_with_rotation_filter` — verify period_loan_count calculated correctly, items with count <= max_borrows returned
- [X] T047 [P] [US2] Integration test `test_search_results_capped_at_200` — create 300 items, verify only 200 returned with capped=true
- [X] T048 [P] [US2] Integration test `test_bulk_mark_inventoried` — verify all valid item_ids get `last_inventoried_at` updated, items_not_found listed in response

**Checkpoint**: User Story 2 complete — search and filter workflow fully functional, integrates with US1 working table

---

## Phase 5: User Story 3 - Bulk Edit of Items and Records (Priority: P3)

**Goal**: Librarian selects items in working table, applies same changes to all (item fields + record fields), with confirmation modal showing counts and warnings

**Independent Test**: Select items with shared/distinct titles, apply changes, verify items updated correctly, each unique title's record updated exactly once, on-loan items excluded from status changes

### Backend — Service Layer for US3

- [X] T049 [US3] Implement `bulk_update_items(db, item_ids, item_updates, record_updates)` in inventory_service.py
- [X] T050 [US3] Fetch all items by item_id.in_(item_ids), apply item_updates to each (skip status changes for `on_loan` items)
- [X] T051 [US3] Deduplicate bibliographic_record_ids from fetched items
- [X] T052 [US3] Apply record_updates to each unique record
- [X] T053 [US3] Count other_copies_affected = SUM(record.total_items) - len(items) for affected records
- [X] T054 [US3] Atomic transaction (commit all or rollback), return `BulkUpdateResponse` with items_updated, items_skipped_on_loan, records_updated, other_copies_affected

### Backend — API Route for US3

- [X] T055 [US3] Implement `POST /inventory/items/bulk-update` endpoint accepting `BulkUpdateRequest` (item_ids, item_updates optional, record_updates optional), returns `BulkUpdateResponse`

### Frontend — Bulk Edit Panel Component for US3

- [X] T056 [P] [US3] Create `src/bcd_web_vue/js/components/inventory/BulkEditPanel.js` with item fields section (condition dropdown, status dropdown, loanable radio, location input) — all "— inchangé —" by default
- [X] T057 [US3] Add record fields section (category input, genre input, niveau input, public dropdown) — all "— inchangé —" or empty by default
- [X] T058 [US3] Implement "Appliquer" button — opens confirmation modal before submitting
- [X] T059 [US3] Implement confirmation modal showing: items count, records count, other_copies_affected count, warnings (on_loan items excluded, items on hold)
- [X] T060 [US3] On confirm, call `POST /inventory/items/bulk-update`, refresh working table, show success notification

### i18n for US3

- [ ] T061 [P] [US3] Add bulk edit keys to en.json — `inventory.bulk_edit.*` (apply, item_section, record_section, unchanged, confirmation modal text)
- [ ] T062 [P] [US3] Add bulk edit keys to fr.json with French translations

### Tests for US3

- [ ] T063 [P] [US3] Integration test `test_bulk_update_excludes_on_loan_from_status_changes` — create 3 items (2 available, 1 on_loan), bulk update status to withdrawn, verify 2 updated, 1 skipped
- [ ] T064 [P] [US3] Integration test `test_bulk_update_records_deduplicated` — create 42 items sharing 7 unique records, bulk update category, verify 7 records updated exactly once
- [ ] T065 [P] [US3] Integration test `test_bulk_update_counts_other_copies` — create items with shared record + other copies not in selection, verify other_copies_affected count correct

**Checkpoint**: User Story 3 complete — bulk edit workflow fully functional with proper deduplication and warnings

---

## Phase 6: User Story 4 - File Import of Inventory IDs (Priority: P4)

**Goal**: Librarian uploads .txt file with item IDs (one per line), system parses, shows valid/unknown count, imports valid IDs to mark as inventoried

**Independent Test**: Import valid file, file with some unknown IDs, file with all unknown IDs, verify table state and error reporting

### Frontend — File Tab Component for US4

- [X] T066 [P] [US4] Create `src/bcd_web_vue/js/components/inventory/FileTab.js` with file input, parse-on-change logic
- [X] T067 [US4] Implement file parsing: split by newline, filter blank lines and `#` comments, strip barcode prefix, deduplicate
- [X] T068 [US4] Call `POST /inventory/items/bulk-mark` with parsed item_ids, show parse results (X IDs found, Y valid, Z unknown)
- [X] T069 [US4] Display unknown IDs list in expandable section or popover
- [X] T070 [US4] Disable Import button when no valid IDs found
- [X] T071 [US4] On import confirm, add valid items to working table (unselected), show success notification

### i18n for US4

- [ ] T072 [P] [US4] Add file import keys to en.json — `inventory.file.*` (choose_file, ids_found, valid_count, unknown_count, view_errors, import_button)
- [ ] T073 [P] [US4] Add file import keys to fr.json with French translations

### Tests for US4

- [ ] T074 [P] [US4] Integration test `test_bulk_mark_handles_duplicates` — pass item_ids with duplicates, verify each item marked only once
- [ ] T075 [P] [US4] E2E test `test_import_file_with_unknown_ids` — upload file with mixed valid/unknown IDs, verify parse preview, verify import only processes valid IDs

**Checkpoint**: User Story 4 complete — file import workflow fully functional

---

## Phase 7: User Story 5 - Bulk Deaccessioning and Deletion (Priority: P5)

**Goal**: Librarian selects items, permanently deletes them from system, on-loan items excluded, holds cancelled

**Independent Test**: Select items including some on-loan, attempt deletion, verify on-loan items excluded, remaining items deleted, holds cancelled

### Backend — Service Layer for US5

- [X] T076 [US5] Implement `delete_items_bulk(db, item_ids)` in inventory_service.py
- [X] T077 [US5] Fetch items by item_id.in_(item_ids), separate into deletable (not on_loan) and on_loan
- [X] T078 [US5] Cancel holds: `db.query(Hold).filter(Hold.item_id.in_([deletable item IDs])).delete()`
- [X] T079 [US5] Delete deletable items, update parent record.total_items counters
- [X] T080 [US5] Count orphan_records_created (records where total_items became 0), atomic transaction, return `BulkDeleteResponse`

### Backend — API Route for US5

- [X] T081 [US5] Implement `DELETE /inventory/items/bulk` endpoint accepting `BulkDeleteRequest` (item_ids array), returns `BulkDeleteResponse`

### Frontend — Delete Button for US5

- [X] T082 [US5] Add "Supprimer" button to BulkEditPanel.js with `bi-trash` icon
- [X] T083 [US5] Implement delete confirmation modal showing: items count, on_loan exclusion warning, "irréversible" warning, final delete count
- [X] T084 [US5] On confirm, call `DELETE /inventory/items/bulk`, remove deleted items from working table, show success notification with deletion count

### i18n for US5

- [ ] T085 [P] [US5] Add delete keys to en.json — `inventory.bulk_delete.*` (delete_button, confirmation modal text, irreversible warning)
- [ ] T086 [P] [US5] Add delete keys to fr.json with French translations

### Tests for US5

- [ ] T087 [P] [US5] Integration test `test_delete_items_excludes_on_loan` — create 5 items (3 available, 2 on_loan), bulk delete all, verify 3 deleted, 2 skipped
- [ ] T088 [P] [US5] Integration test `test_delete_items_cancels_holds` — create item with active hold, delete item, verify hold cancelled
- [ ] T089 [P] [US5] Integration test `test_delete_items_updates_record_counters` — delete items, verify parent record.total_items decremented correctly, orphan records counted

**Checkpoint**: User Story 5 complete — bulk deletion workflow fully functional with proper exclusions and hold cancellation

---

## Phase 8: User Story 6 - Working Table Management and Export (Priority: P6)

**Goal**: Librarian manages working table (select, clear, shift-click range selection), exports to CSV

**Independent Test**: Populate table, use header checkbox and shift-click, clear with/without selection, verify CSV contents match table

### Backend — Service Layer for US6

- [X] T090 [US6] Implement `get_items_csv(db, item_ids)` in inventory_service.py — fetch items with joined bibliographic_record, format as CSV string with 9 columns (barcode with prefix, title, authors[0], call_number, shelf_location, status, condition, last_borrowed_at date, last_inventoried_at date)

### Backend — API Route for US6

- [X] T091 [US6] Implement `POST /inventory/export-csv` endpoint accepting `ExportCSVRequest` (item_ids array), returns CSV file with Content-Type: text/csv and Content-Disposition: attachment filename=inventory_YYYY-MM-DD.csv

### Frontend — Working Table Enhancements for US6

- [ ] T092 [US6] Implement shift-click range selection in WorkingTable.js — track lastSelectedIndex, on shift+click select range from lastSelectedIndex to current
- [X] T093 [US6] Implement "Vider" button with confirmation modal: "Vider les {count} exemplaires sélectionnés?" or "Vider tous les {total} exemplaires?" depending on selection
- [X] T094 [US6] On clear confirm, remove selected items from working table (localStorage updated automatically), clear selection
- [X] T095 [US6] Implement CSV export via AdminDropdown — collect item_ids from working table, call `POST /inventory/export-csv`, trigger download

### Frontend — Admin Dropdown Integration for US6

- [X] T096 [US6] Modify `src/bcd_web_vue/js/components/admin/AdminDropdown.js` to accept `page='inventory'` in validator
- [X] T097 [US6] Add inventory-specific menu items: "Exporter CSV" (emits 'export'), "Supprimer notices sans exemplaires" (emits 'delete-orphans')

### i18n for US6

- [ ] T098 [P] [US6] Add working table keys to en.json — `inventory.working_table.*` (clear, clear_selected_confirm, clear_all_confirm, export_csv)
- [ ] T099 [P] [US6] Add working table keys to fr.json with French translations

### Tests for US6

- [ ] T100 [P] [US6] Integration test `test_export_csv_includes_all_columns` — create items, call get_items_csv, verify CSV has 9 columns with correct headers and data
- [ ] T101 [P] [US6] E2E test `test_shift_click_range_selection` — populate table, shift+click two rows, verify all rows between them selected

**Checkpoint**: User Story 6 complete — working table management and CSV export fully functional

---

## Phase 9: User Story 7 - Orphan Record Cleanup (Priority: P7)

**Goal**: Administrator removes bibliographic records with no remaining items (total_items = 0)

**Independent Test**: Create orphan record scenario, trigger cleanup from admin menu, verify record removed

### Backend — Service Layer for US7

- [X] T102 [US7] Implement `get_orphan_records(db)` in inventory_service.py — query BiblographicRecord.filter_by(total_items=0), return `OrphanRecordsResponse` with count and records list (id, title, isbn)
- [X] T103 [US7] Implement `delete_orphan_records(db)` in inventory_service.py — get orphan record IDs, call `catalog_service.bulk_delete_records(db, record_ids)`, return `OrphanDeleteResponse` with records_deleted count

### Backend — API Routes for US7 (in admin.py)

- [X] T104 [US7] Implement `GET /admin/catalog/orphan-records` endpoint in `src/bcd_api/api/v1/admin.py`, returns `OrphanRecordsResponse`
- [X] T105 [US7] Implement `DELETE /admin/catalog/orphan-records` endpoint in admin.py, returns `OrphanDeleteResponse`

### Frontend — Admin Dropdown Handler for US7

- [X] T106 [US7] In InventoryPage.js, implement `handleDeleteOrphans` — calls `GET /admin/catalog/orphan-records`, opens confirmation modal
- [X] T107 [US7] Implement orphan deletion confirmation modal: shows count, "irréversible" warning, on confirm calls `DELETE /admin/catalog/orphan-records`
- [X] T108 [US7] Handle edge case: if count=0, show modal "Aucune notice à supprimer" instead of delete confirmation

### i18n for US7

- [ ] T109 [P] [US7] Add orphan cleanup keys to en.json — `inventory.admin.*` (delete_orphans, orphan_count_modal, no_orphans_modal, irreversible warning)
- [ ] T110 [P] [US7] Add orphan cleanup keys to fr.json with French translations

### Tests for US7

- [ ] T111 [P] [US7] Integration test `test_get_orphan_records` — create records with total_items=0 and total_items>0, verify only orphans returned
- [ ] T112 [P] [US7] Integration test `test_delete_orphan_records` — create orphan records, call delete_orphan_records, verify records deleted from database

**Checkpoint**: User Story 7 complete — orphan record cleanup fully functional

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Help Documentation

- [X] T113 [P] Create `docs/help/en/inventory.md` with English help content (structure from inventaire-mockup.md)
- [X] T114 [P] Create `docs/help/fr/inventaire.md` with French help content (structure from inventaire-mockup.md)
- [X] T115 Verify `src/bcd_web_vue/help` symlink points to `../../docs/help/`
- [X] T116 Add `inventory: { fr: 'inventaire.md', en: 'inventory.md' }` to SECTION_FILES in HelpPanel.js
- [X] T117 Add 'inventory' to section validator in HelpPanel.js props

### Final Integration & Testing

- [ ] T118 [P] Run full test suite: `pytest tests/integration tests/unit -v`
- [ ] T119 [P] Manual test: Complete end-to-end inventory workflow (scan → search → bulk edit → export → orphan cleanup)
- [ ] T120 [P] Verify i18n completeness: check all en.json keys have fr.json equivalents, no hard-coded strings in components
- [ ] T121 Code cleanup: remove TODO/FIXME comments, ensure consistent formatting (black, ruff)
- [ ] T122 Run `/speckit.review` to validate implementation against spec and constitution

### Performance Validation

- [ ] T123 Verify search performance: test with 3,000 items, all filters active, confirm <2s response time on legacy hardware
- [ ] T124 Verify bulk edit performance: test with 300 items, confirm <30s completion time
- [ ] T125 Verify file parse performance: test with 500 IDs, confirm <3s parse time

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Complete (existing codebase)
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5 → P6 → P7)
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational — Integrates with US1 working table but independently testable
- **User Story 3 (P3)**: Can start after Foundational — Uses US1 working table selection but independently testable
- **User Story 4 (P4)**: Can start after Foundational — Uses US2 bulk-mark endpoint, integrates with US1 working table
- **User Story 5 (P5)**: Can start after Foundational — Uses US3 bulk edit panel, independently testable
- **User Story 6 (P6)**: Can start after Foundational — Enhances US1 working table, independently testable
- **User Story 7 (P7)**: Can start after Foundational — Admin feature, completely independent

### Within Each User Story

- Backend service functions before API routes
- Pydantic schemas (from Foundational) before API routes
- Frontend composables before page components
- Components before page integration
- Tests can be written in parallel with implementation (TDD encouraged)

### Parallel Opportunities

**Foundational Phase** (after migration complete):
- T005-T010: All Pydantic schemas in parallel (different classes in same file)
- T011-T012: Service file creation + composable creation in parallel

**User Story 1**:
- T017, T019: ScanTab + WorkingTable components in parallel (different files)
- T024, T025: en.json + fr.json in parallel (same keys, different languages)
- T028, T029, T030: All tests in parallel (different test files/functions)

**User Story 2**:
- T036, T037, T038: Search filter UI components can be built in parallel
- T043, T044: en.json + fr.json in parallel
- T045-T048: All tests in parallel

**User Story 3**:
- T061, T062: en.json + fr.json in parallel
- T063-T065: All tests in parallel

**User Story 4**:
- T072, T073: en.json + fr.json in parallel
- T074, T075: Tests in parallel

**User Story 5**:
- T085, T086: en.json + fr.json in parallel
- T087-T089: All tests in parallel

**User Story 6**:
- T098, T099: en.json + fr.json in parallel
- T100, T101: Tests in parallel

**User Story 7**:
- T109, T110: en.json + fr.json in parallel
- T111, T112: Tests in parallel

**Polish Phase**:
- T113, T114: Help documentation in parallel (different languages)
- T118-T121: Testing and cleanup in parallel (different activities)
- T123-T125: Performance validation in parallel (different scenarios)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase complete, launch US1 backend in parallel:
Task T013: "Implement mark_item_inventoried in inventory_service.py"
Task T014: "Create inventory.py router"
Task T015: "Implement PATCH /inventory/items/{item_id}"

# Launch US1 frontend components in parallel:
Task T017: "Create ScanTab.js component"
Task T019: "Create WorkingTable.js component"

# Launch US1 i18n in parallel:
Task T024: "Add inventory.* keys to en.json"
Task T025: "Add inventory.* keys to fr.json"

# Launch US1 tests in parallel (after implementation):
Task T028: "Integration test test_mark_item_inventoried_success"
Task T029: "Integration test test_mark_item_inventoried_not_found"
Task T030: "E2E test test_scan_barcode_adds_to_table"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (CRITICAL)
2. Complete Phase 3: User Story 1 (barcode scanning)
3. **STOP and VALIDATE**: Test US1 independently — can scan barcodes, items appear in table, inventory dates updated
4. Deploy/demo if ready

This gives librarians the core récolement workflow (barcode scanning + inventory date tracking).

### Incremental Delivery

1. Foundation → MVP (US1) → Test → Deploy
2. Add US2 (Search) → Test → Deploy
3. Add US3 (Bulk Edit) → Test → Deploy
4. Add US4 (File Import) → Test → Deploy
5. Add US5 (Bulk Delete) → Test → Deploy
6. Add US6 (Table Management + Export) → Test → Deploy
7. Add US7 (Orphan Cleanup) → Test → Deploy
8. Polish → Final validation → Merge

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Foundational together (T001-T012)
2. Once Foundational is done:
   - Developer A: User Story 1 (T013-T030)
   - Developer B: User Story 2 (T031-T048)
   - Developer C: User Story 3 (T049-T065)
3. Stories complete and integrate independently
4. Continue with remaining stories (US4-US7) based on priority

---

## Notes

- [P] tasks = different files or independent sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- All database changes via Alembic migration in Foundational phase (T001-T004)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All user-facing text must be externalized to en.json + fr.json (constitution requirement)
- Use timezone-aware UTC timestamps (`datetime.now(timezone.utc)`)
- Use `pathlib` for all file operations (cross-platform requirement)
- Follow architecture-patterns.md: service layer for business logic, thin API routes, structured exceptions with error_code + context
- Reuse existing composables: `useSelection`, `useNotification`, `useErrorHandler`, `useBulkOperations`
- Target performance: search <2s, bulk edit <30s, file parse <3s (legacy hardware)

---

**Total Task Count**: 125 tasks across 7 user stories + foundational + polish

**Suggested MVP Scope**: Phase 2 (Foundational) + Phase 3 (User Story 1) = 30 tasks

**Parallel Opportunities**: 40+ tasks marked [P] can run in parallel within their phase
