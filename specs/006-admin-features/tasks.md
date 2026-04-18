# Tasks: Admin Features Panel

**Input**: Design documents from `/home/nixos/src/local/bcd4/specs/006-admin-features/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.yaml

**Tests**: No test tasks included (not requested in spec.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**Status**: ✅ Already complete - project structure exists

No tasks needed - all infrastructure already exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T001 [P] Create admin-specific exception classes in src/bcd_api/core/exceptions.py (ClassHasBorrowersException, DuplicateBorrowerIDException, DuplicateBarcodeException, BulkOperationFailedException)
- [X] T002 [P] Add admin i18n strings for English in src/bcd_web_vue/locales/en.json (admin menu labels, bulk operation prompts, confirmation dialogs, error messages)
- [X] T003 [P] Add admin i18n strings for French in src/bcd_web_vue/locales/fr.json (admin menu labels, bulk operation prompts, confirmation dialogs, error messages)
- [X] T004 Create error code mapping documentation in specs/006-admin-features/contracts/error-codes.md (BORROWER_ID_NOT_AVAILABLE, DUPLICATE_BARCODE, DUPLICATE_CLASS_NAME, BULK_OPERATION_FAILED, CLASS_HAS_BORROWERS)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Admin Menu on Borrower & Catalog Pages (Priority: P1) 🎯 MVP

**Goal**: Replace individual Import/Export buttons with a red "Admin" dropdown menu on Borrower & Catalog pages

**Independent Test**: Visit Borrowers and Catalog pages, click admin dropdown, verify all import/export operations are accessible

### Tests for User Story 1 (Service-Layer Integration Tests)

**Note**: Write these tests FIRST per Constitution Principle III, ensure they FAIL before implementation

- [ ] T004a [P] [US1] Integration test for AdminDropdown conditional enabling in tests/integration/test_admin_dropdown.py (test selectedCount=0 disables both, selectedCount=1 enables Edit Selected only, selectedCount=2+ enables Bulk Edit only)
- [ ] T004b [P] [US1] Integration test for import/export menu item functionality in tests/integration/test_admin_menu_operations.py (verify import/export handlers called correctly from admin dropdown)

### Implementation for User Story 1

- [X] T005 [P] [US1] Create AdminDropdown.js Vue component in src/bcd_web_vue/js/components/admin/AdminDropdown.js (reusable dropdown with props: selectedCount, page; conditional logic: "Edit Selected" enabled only when selectedCount===1, "Bulk Edit" enabled when selectedCount>=1; emits: import, export, bulkEdit, editSelected)
- [X] T006 [P] [US1] Create ConfirmDialog.js Vue component in src/bcd_web_vue/js/components/admin/ConfirmDialog.js (confirmation dialog with count, scrollable list showing max 10 items with "and N more" message, i18n support)
- [X] T007 [US1] Integrate AdminDropdown into BorrowersPage.js in src/bcd_web_vue/js/pages/BorrowersPage.js (replace import/export buttons, wire up menu events)
- [X] T008 [US1] Integrate AdminDropdown into CatalogPage.js in src/bcd_web_vue/js/pages/CatalogPage.js (replace import/export buttons, wire up menu events)
- [X] T009 [US1] Move Import/Export button logic from BorrowerList.js to AdminDropdown handlers in src/bcd_web_vue/js/components/borrowers/BorrowerList.js (N/A - logic was in BorrowersPage.js, already moved)
- [X] T010 [US1] Move Import/Export button logic from SearchResults.js to AdminDropdown handlers in src/bcd_web_vue/js/components/catalog/SearchResults.js (N/A - logic was in CatalogPage.js, already moved)
- [X] T011 [US1] Update router.js in src/bcd_web_vue/js/router.js to ensure admin dropdown state is preserved on page navigation (N/A - admin dropdown is stateless, selectedCount managed by parent page)

**Checkpoint**: At this point, User Story 1 should be fully functional - admin menu accessible with import/export operations

---

## Phase 4: User Story 2 - Class Management Page (Priority: P2)

**Goal**: Create a dedicated Classes management page with CRUD operations

**Independent Test**: Create a new class, edit it, delete it, verify database changes

### Tests for User Story 2 (Service-Layer Integration Tests)

**Note**: Write these tests FIRST per Constitution Principle III, ensure they FAIL before implementation

- [X] T011a [P] [US2] Service-layer integration test for delete_class_with_unassignment in tests/integration/services/test_class_service_admin.py (test class deletion unassigns borrowers, verify class_id set to NULL, class deleted)
- [X] T011b [P] [US2] Service-layer integration test for student_count denormalized counter in tests/integration/services/test_class_service_admin.py (test counter increments on borrower class assignment, decrements on unassignment)

### Implementation for User Story 2

- [X] T012 [P] [US2] Verify Class model exists and supports required fields in src/bcd_api/models/class_model.py (student_count already exists - verified)
- [X] T013 [P] [US2] Create ClassCreate schema in src/bcd_api/schemas/class_schema.py (name, grade_level, academic_year, homeroom_teacher, notes) - Already exists
- [X] T014 [P] [US2] Create ClassUpdate schema in src/bcd_api/schemas/class_schema.py (partial update schema) - Already exists
- [X] T015 [P] [US2] Create ClassResponse schema in src/bcd_api/schemas/class_schema.py (response with id, timestamps, student_count field) - Updated to include student_count
- [X] T015a [US2] Implement student_count denormalized counter in Class model - ALREADY EXISTS (line 26 of class_model.py)
- [X] T016 [US2] Add delete_class_with_unassignment method to ClassService in src/bcd_api/services/class_service.py (unassign all borrowers from class by setting class_id=NULL, then delete class) - Already exists
- [X] T017 [US2] Implement DELETE /classes/{class_id} endpoint in src/bcd_api/api/v1/classes.py (calls delete_class_with_unassignment service method) - Updated
- [X] T018 [P] [US2] Create ClassList.js Vue component in src/bcd_web_vue/js/components/classes/ClassList.js (table with columns: Name, Grade Level, Student Count, Actions)
- [X] T019 [P] [US2] Create ClassForm.js Vue component in src/bcd_web_vue/js/components/classes/ClassForm.js (create/edit modal with validation)
- [X] T020 [P] [US2] Create ClassDeleteDialog.js Vue component in src/bcd_web_vue/js/components/classes/ClassDeleteDialog.js (confirmation showing student count, warning that students will be unassigned from class before deletion)
- [X] T021 [US2] Create ClassesPage.js in src/bcd_web_vue/js/pages/ClassesPage.js (integrates ClassList, ClassForm, ClassDeleteDialog)
- [X] T022 [US2] Add /classes route to router.js in src/bcd_web_vue/js/router.js
- [X] T023 [US2] Add "Classes" link to main navigation menu in src/bcd_web_vue/js/components/layout/NavigationMenu.js

**Checkpoint**: At this point, Classes CRUD should be fully functional and testable independently

---

## Phase 5: User Story 3 - Bulk Borrower Operations (Priority: P3)

**Goal**: Enable bulk operations on borrowers (change class, change role, delete multiple)

**Independent Test**: Select multiple borrowers, change their class, verify all updates succeed atomically

### Tests for User Story 3 (Service-Layer Integration Tests)

**Note**: Write these tests FIRST per Constitution Principle III, ensure they FAIL before implementation

- [X] T023a [P] [US3] Service-layer integration test for bulk_change_class in tests/integration/services/test_borrower_service_bulk.py (test atomic transaction: success updates all, failure rollback all, verify CASCADE behavior)
- [X] T023b [P] [US3] Service-layer integration test for bulk_change_role in tests/integration/services/test_borrower_service_bulk.py (test atomic transaction, role enum validation, rollback on invalid role)
- [X] T023c [P] [US3] Service-layer integration test for bulk_delete_borrowers in tests/integration/services/test_borrower_service_bulk.py (test CASCADE delete removes borrowers and circulation history, atomic rollback on error)

### Implementation for User Story 3

- [X] T024 [P] [US3] Create BulkChangeClassRequest schema in src/bcd_api/schemas/admin.py (operation, borrower_ids, target_class_id)
- [X] T025 [P] [US3] Create BulkChangeRoleRequest schema in src/bcd_api/schemas/admin.py (operation, borrower_ids, target_role)
- [X] T026 [P] [US3] Create BulkDeleteRequest schema in src/bcd_api/schemas/admin.py (borrower_ids)
- [X] T027 [P] [US3] Create BulkOperationResult schema in src/bcd_api/schemas/admin.py (total_count, successful_count, failed_count, operation, details)
- [X] T028 [US3] Implement bulk_change_class service method in src/bcd_api/services/borrower_service.py (atomic transaction with full rollback on any error, validate class_id exists, update all borrowers in single transaction or rollback all changes)
- [X] T029 [US3] Implement bulk_change_role service method in src/bcd_api/services/borrower_service.py (atomic transaction with full rollback on any error, validate role enum, update all borrowers or rollback all changes)
- [X] T030 [US3] Implement bulk_delete_borrowers service method in src/bcd_api/services/borrower_service.py (atomic transaction, CASCADE delete circulation history, full rollback on any database error)
- [X] T031 [P] [US3] Implement POST /admin/borrowers/bulk-edit endpoint in src/bcd_api/api/admin.py (handles change_class and change_role operations)
- [X] T032 [P] [US3] Implement POST /admin/borrowers/bulk-delete endpoint in src/bcd_api/api/admin.py (calls bulk_delete_borrowers service method)
- [X] T033 [P] [US3] Create BulkEditModal.js Vue component in src/bcd_web_vue/js/components/admin/BulkEditModal.js (operation selector, change class/role forms, delete confirmation)
- [ ] T034 [P] [US3] Create useSelection.js composable in src/bcd_web_vue/js/composables/useSelection.js (multi-select checkbox logic, selectedCount, clearSelection)
- [ ] T035 [P] [US3] Create useBulkOperations.js composable in src/bcd_web_vue/js/composables/useBulkOperations.js (bulk edit/delete API calls, progress tracking)
- [X] T036 [US3] Add checkboxes to BorrowerList.js in src/bcd_web_vue/js/components/borrowers/BorrowerList.js (integrate useSelection composable)
- [X] T037 [US3] Wire BulkEditModal into AdminDropdown "Bulk Edit" menu item in src/bcd_web_vue/js/components/admin/AdminDropdown.js
- [ ] T038 [US3] Add progress indicator for 100+ record operations in BulkEditModal.js (reuse pattern from import workflow, threshold: show spinner for <100 records, show progress bar with percentage for ≥100 records)

**Checkpoint**: Bulk borrower operations should be fully functional and atomic

---

## Phase 6: User Story 4 - Single Borrower Editing (Priority: P4)

**Goal**: Enable editing individual borrower details (name, ID, role, class)

**Independent Test**: Select one borrower, edit their details, verify changes are saved with validation

### Tests for User Story 4 (Service-Layer Integration Tests)

**Note**: Write these tests FIRST per Constitution Principle III, ensure they FAIL before implementation

- [X] T038a [P] [US4] Service-layer integration test for update_borrower in tests/integration/services/test_borrower_service_edit.py (test borrower_id uniqueness validation, format validation, full_name auto-update, BORROWER_ID_NOT_AVAILABLE error)

### Implementation for User Story 4

- [X] T039 [P] [US4] Create BorrowerUpdate schema in src/bcd_api/schemas/borrower.py (partial update schema: first_name, last_name, borrower_id, role, class_id, email, phone, notes)
- [X] T040 [US4] Implement update_borrower service method in src/bcd_api/services/borrower_service.py (validates borrower_id uniqueness and format, updates full_name automatically)
- [X] T041 [US4] Implement PATCH /borrowers/{borrower_id} endpoint in src/bcd_api/api/borrowers.py (calls update_borrower service method)
- [X] T042 [P] [US4] Create BorrowerEditForm.js Vue component in src/bcd_web_vue/js/components/borrowers/BorrowerEditForm.js (edit modal with fields: first_name, last_name, borrower_id, role, class_id)
- [X] T043 [US4] Wire BorrowerEditForm into AdminDropdown "Edit Selected" menu item in src/bcd_web_vue/js/components/admin/AdminDropdown.js (enabled when selectedCount === 1)
- [X] T044 [US4] Add client-side validation for borrower_id format and uniqueness in BorrowerEditForm.js
- [X] T045 [US4] Add error handling for duplicate borrower_id (BORROWER_ID_NOT_AVAILABLE) with i18n message in BorrowerEditForm.js

**Checkpoint**: Single borrower editing should be fully functional with validation

---

## Phase 7: User Story 5 - Bulk Catalog Operations (Priority: P5)

**Goal**: Enable bulk operations on bibliographic records (delete multiple, edit common fields)

**Independent Test**: Select multiple catalog records, perform bulk edit, verify changes apply atomically

### Tests for User Story 5 (Service-Layer Integration Tests)

**Note**: Write these tests FIRST per Constitution Principle III, ensure they FAIL before implementation

- [ ] T045a [P] [US5] Service-layer integration test for bulk_edit_records in tests/integration/services/test_catalog_service_bulk.py (test atomic transaction updates category, genre, target_audience, language, medium_type for multiple records, null values unchanged, rollback on error)
- [ ] T045b [P] [US5] Service-layer integration test for bulk_delete_records in tests/integration/services/test_catalog_service_bulk.py (test CASCADE delete removes records, items (even if on loan), circulation history, atomic rollback on error)

### Implementation for User Story 5

- [ ] T046 [P] [US5] Create BulkEditRecordsRequest schema in src/bcd_api/schemas/admin.py (record_ids, fields: category, genre, target_audience, language, medium_type)
- [ ] T047 [P] [US5] Create BulkDeleteRecordsRequest schema in src/bcd_api/schemas/admin.py (record_ids)
- [ ] T048 [US5] Implement bulk_edit_records service method in src/bcd_api/services/catalog_service.py (atomic transaction with full rollback on any error, updates common fields: category, genre, target_audience, language, medium_type for multiple records, null values = no change)
- [ ] T049 [US5] Implement bulk_delete_records service method in src/bcd_api/services/catalog_service.py (atomic transaction, CASCADE delete items even if on loan, CASCADE delete circulation history, full rollback on any database error)
- [ ] T050 [P] [US5] Implement POST /admin/catalog/bulk-edit endpoint in src/bcd_api/api/admin.py (calls bulk_edit_records service method)
- [ ] T051 [P] [US5] Implement POST /admin/catalog/bulk-delete endpoint in src/bcd_api/api/admin.py (calls bulk_delete_records service method)
- [ ] T052 [US5] Add checkboxes to SearchResults.js in src/bcd_web_vue/js/components/catalog/SearchResults.js (integrate useSelection composable)
- [ ] T053 [US5] Create catalog-specific BulkEditModal variant for catalog records in src/bcd_web_vue/js/components/admin/BulkEditModal.js (edit common fields: category, genre, target_audience, language, medium_type)
- [ ] T054 [US5] Wire catalog BulkEditModal into AdminDropdown "Bulk Edit" menu item on CatalogPage.js
- [ ] T055 [US5] Add progress indicator for 100+ record operations in catalog BulkEditModal
- [ ] T055a [US5] Add test validation task to verify CASCADE delete behavior when deleting bibliographic records with items on loan (verify items deleted, circulation history preserved, no orphaned items)

**Checkpoint**: Bulk catalog operations should be fully functional and atomic

---

## Phase 8: User Story 6 - Single Catalog Record/Item Editing (Priority: P6)

**Goal**: Enable editing individual bibliographic records and items (correct metadata, update item details)

**Independent Test**: Select one record, edit its metadata, verify changes are saved with validation

### Tests for User Story 6 (Service-Layer Integration Tests)

**Note**: Write these tests FIRST per Constitution Principle III, ensure they FAIL before implementation

- [ ] T055b [P] [US6] Service-layer integration test for update_record in tests/integration/services/test_catalog_service_edit.py (test bibliographic record metadata update, field validation)
- [ ] T055c [P] [US6] Service-layer integration test for update_item in tests/integration/services/test_catalog_service_edit.py (test item barcode uniqueness validation, format validation, DUPLICATE_BARCODE error)

### Implementation for User Story 6

- [ ] T056 [P] [US6] Create BiblographicRecordUpdate schema in src/bcd_api/schemas/catalog.py (partial update schema: title, subtitle, authors, illustrators, publisher, publication_year, category, genre, target_audience, language, medium_type, description)
- [ ] T057 [P] [US6] Create ItemUpdate schema in src/bcd_api/schemas/catalog.py (partial update schema: item_id, call_number, shelf_location, condition, status, loanable, acquisition_date, funding_source)
- [ ] T058 [US6] Implement update_record service method in src/bcd_api/services/catalog_service.py (updates bibliographic record metadata)
- [ ] T059 [US6] Implement update_item service method in src/bcd_api/services/catalog_service.py (validates item_id/barcode uniqueness, updates item fields)
- [ ] T060 [P] [US6] Implement PATCH /catalog/records/{record_id} endpoint in src/bcd_api/api/catalog.py (calls update_record service method)
- [ ] T061 [P] [US6] Implement PATCH /catalog/items/{item_id} endpoint in src/bcd_api/api/catalog.py (calls update_item service method)
- [ ] T062 [P] [US6] Create RecordEditForm.js Vue component in src/bcd_web_vue/js/components/catalog/RecordEditForm.js (edit modal with metadata fields)
- [ ] T063 [P] [US6] Create ItemEditForm.js Vue component in src/bcd_web_vue/js/components/catalog/ItemEditForm.js (edit modal with item fields)
- [ ] T064 [US6] Wire RecordEditForm into AdminDropdown "Edit Selected" menu item on CatalogPage.js (enabled when selectedCount === 1)
- [ ] T065 [US6] Add ItemEditForm to item details view (location TBD - verify existing item UI structure first)
- [ ] T066 [US6] Add client-side validation for item barcode uniqueness in ItemEditForm.js
- [ ] T067 [US6] Add error handling for duplicate barcode (DUPLICATE_BARCODE) with i18n message in ItemEditForm.js

**Checkpoint**: Single catalog/item editing should be fully functional with validation

---

## Phase 9: User Story 7 - Import/Export Relocation (Priority: P7)

**Goal**: Verify import/export buttons removed from Borrower and Catalog pages (work completed in US1)

**Independent Test**: Verify import/export buttons no longer visible in default view, only accessible via admin menu

### Implementation for User Story 7

- [ ] T068 [US7] Verify import/export button removal completed in US1 tasks T009-T010 (check BorrowerList.js and SearchResults.js have no standalone import/export buttons, only AdminDropdown)

**Checkpoint**: Import/Export fully relocated to admin menu, no duplicate UI elements

**Note**: Tasks T068-T071 from original plan were duplicate verification work already covered by US1 tasks T009-T010. Consolidated into single verification task T068.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T069 [P] Add progress indicator component in src/bcd_web_vue/js/components/admin/ProgressIndicator.js (percentage, progress bar, reusable for all bulk operations)
- [ ] T070 Update API documentation in src/bcd_api/main.py to include new admin endpoints (automatic via OpenAPI)
- [ ] T071 [P] Add logging for all admin operations (operation type, user, timestamp, affected record count) in src/bcd_api/services/ (borrower_service.py, catalog_service.py, class_service.py) per FR-047 requirement
- [ ] T072 Validate all i18n strings are complete (en/fr parity) for FR-042 bilingual requirement by reviewing src/bcd_web_vue/locales/en.json and fr.json (all admin menu labels, confirmation dialogs, error messages, form labels must exist in both languages)
- [ ] T073 Verify all confirmation dialogs show count and names/titles with scrollable list (max 10 visible)
- [ ] T074 Verify all bulk operations complete in <10 seconds for 100 records on legacy hardware baseline (dual-core 2.0GHz CPU, 4GB RAM, HDD storage per Constitution Principle VI) using benchmark script with realistic data (bulk change class, bulk delete, bulk edit catalog fields)
- [ ] T075 Verify all admin operations are atomic (all succeed or all fail) via database transaction tests
- [ ] T076 Code cleanup and refactoring (extract common bulk operation patterns, DRY violations)
- [ ] T077 Run quickstart.md validation from specs/006-admin-features/quickstart.md (if exists)
- [ ] T078 Update CLAUDE.md if needed to document new admin features usage patterns

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Already complete - no tasks needed
- **Foundational (Phase 2)**: T001-T004 - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - **Test-First**: Write tests BEFORE implementation per Constitution Principle III
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5 → P6 → P7)
- **Polish (Phase 10)**: T069-T078 - Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Tests T004a-T004b → Implementation T005-T011 - No dependencies on other stories ✅ MVP
- **User Story 2 (P2)**: Tests T011a-T011b → Implementation T012-T023 - Independent
- **User Story 3 (P3)**: Tests T023a-T023c → Implementation T024-T038 - Depends on US2 (Class Management) for class reassignment feature
- **User Story 4 (P4)**: Tests T038a → Implementation T039-T045 - Independent
- **User Story 5 (P5)**: Tests T045a-T045b → Implementation T046-T055a - Independent
- **User Story 6 (P6)**: Tests T055b-T055c → Implementation T056-T067 - Independent
- **User Story 7 (P7)**: T068 verification only - Depends on US1 (Admin Menu) being complete

### Within Each User Story

- **Tests FIRST** (write failing tests before implementation per Constitution Principle III)
- Models/schemas before services
- Services before endpoints
- Backend endpoints before frontend components
- Core components before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Foundational tasks (T001-T004) marked [P] can run in parallel
- Once Foundational phase completes, user stories can start in parallel (if team capacity allows)
- Within each user story, tasks marked [P] can run in parallel (different files, no dependencies)
- US1, US2, US4, US5, US6 can be worked on in parallel by different team members
- US3 should wait for US2 (Class Management) to be complete for best UX
- US7 should wait for US1 to be complete

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T004) ← CRITICAL
2. **Test-First**: Write tests for US1 (T004a-T004b), ensure they FAIL
3. Complete Phase 3: User Story 1 Implementation (T005-T011) ← Admin Menu
4. **STOP and VALIDATE**: Run tests (T004a-T004b should PASS), test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery (Test-First)

1. Complete Foundational (T001-T004) → Foundation ready
2. Write US1 tests (T004a-T004b) → Add US1 implementation (T005-T011) → Validate tests pass → Deploy/Demo (MVP!)
3. Write US2 tests (T011a-T011b) → Add US2 implementation (T012-T023) → Validate tests pass → Deploy/Demo
4. Write US3 tests (T023a-T023c) → Add US3 implementation (T024-T038) → Validate tests pass → Deploy/Demo
5. Write US4 tests (T038a) → Add US4 implementation (T039-T045) → Validate tests pass → Deploy/Demo
6. Write US5 tests (T045a-T045b) → Add US5 implementation (T046-T055a) → Validate tests pass → Deploy/Demo
7. Write US6 tests (T055b-T055c) → Add US6 implementation (T056-T067) → Validate tests pass → Deploy/Demo
8. Add User Story 7 verification (T068) → Validate → Deploy/Demo
9. Polish (T069-T078) → Final quality pass

### Parallel Team Strategy (Test-First)

With multiple developers:

1. Team completes Foundational (T001-T004) together
2. Once Foundational is done:
   - Developer A: Write US1 tests (T004a-T004b) → US1 implementation (T005-T011) - Admin Menu (MVP)
   - Developer B: Write US2 tests (T011a-T011b) → US2 implementation (T012-T023) - Class Management
   - Developer C: Write US4 tests (T038a) → US4 implementation (T039-T045) - Single Borrower Editing
3. After US1 and US2 complete:
   - Developer A: Write US3 tests (T023a-T023c) → US3 implementation (T024-T038) - Bulk Borrower Operations (depends on US2)
   - Developer B: Write US5 tests (T045a-T045b) → US5 implementation (T046-T055a) - Bulk Catalog Operations
   - Developer C: Write US6 tests (T055b-T055c) → US6 implementation (T056-T067) - Single Catalog Editing
4. All tests pass, stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Test-First Development**: Write tests BEFORE implementation per Constitution Principle III
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- **Service-layer integration tests included** (T004a-T055c) - 80%+ coverage target per Constitution
- All bulk operations MUST use atomic transactions with full rollback (all succeed or all fail, no partial updates)
- All error messages MUST use error_code + context pattern for i18n
- All confirmation dialogs MUST show count and names/titles (max 10 visible, scrollable)
- Progress indicators REQUIRED for ≥100 record operations (threshold: 100 records)
- CASCADE delete behavior documented in data-model.md
- Student count uses denormalized counter pattern per FR-014
- Field list for bulk catalog edit: category, genre, target_audience, language, medium_type per FR-030
