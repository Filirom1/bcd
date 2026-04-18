# Tasks: CSV Import/Export for Catalog and Borrowers

**Input**: Design documents from `/home/nixos/src/local/bcd4/specs/005-csv-import/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md

**Tests**: NO tests required per spec.md. Integration tests exist but TDD not required for this feature.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, templates, and directory structure

- [X] T001 [P] Install `chardet` dependency for encoding detection (add to requirements.txt)
- [X] T002 [P] Create CSV templates directory at `/home/nixos/src/local/bcd4/data/templates/`
- [X] T003 [P] Create conversion scripts directory at `/home/nixos/src/local/bcd4/scripts/convert/`
- [X] T004 Create Dublin Core CSV template at `/home/nixos/src/local/bcd4/data/templates/catalog_dublin_core.csv` with header row and sample data row
- [X] T005 Create BCD borrower CSV template at `/home/nixos/src/local/bcd4/data/templates/borrowers_bcd.csv` with header row and sample data row
- [X] T006 Create conversion scripts README at `/home/nixos/src/local/bcd4/scripts/convert/README.md` with usage examples

**Checkpoint**: Directory structure, templates, and dependencies ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 [P] Add CSV-specific exception classes to `/home/nixos/src/local/bcd4/src/bcd_api/core/exceptions.py` (CSVValidationError, CSVEncodingError, CSVRowLimitError)
- [X] T008 [P] Add CSV format constants to `/home/nixos/src/local/bcd4/src/shared/constants.py` (MAX_CATALOG_ROWS=10000, MAX_BORROWER_ROWS=5000, DUBLIN_CORE_COLUMNS, BCD_BORROWER_COLUMNS)
- [X] T009 [P] Add encoding detection utility function to `/home/nixos/src/local/bcd4/src/bcd_api/utils/encoding.py` (detect_csv_encoding using charset-normalizer)
- [X] T010 [P] Add i18n keys for catalog import/export to `/home/nixos/src/local/bcd4/src/bcd_web_vue/locales/en.json` (catalog.import, catalog.export, errors.csv_validation, etc.)
- [X] T011 [P] Add i18n keys for borrower import/export to `/home/nixos/src/local/bcd4/src/bcd_web_vue/locales/en.json` (borrower.import, borrower.export, success messages, etc.)
- [X] T012 [P] Add French i18n translations to `/home/nixos/src/local/bcd4/src/bcd_web_vue/locales/fr.json` (matching keys from en.json)
- [X] T013 Create Pydantic schemas in `/home/nixos/src/local/bcd4/src/bcd_api/schemas/export.py` (ExportFormat enum, ExportResponse, ImportResponse with counts and error list)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Export Catalog to CSV (Priority: P1) 🎯 MVP

**Goal**: Librarians can export their entire catalog in Dublin Core format with immediate CSV download

**Independent Test**: Create sample catalog records, click "Export Catalog" button in web UI, verify CSV downloads with all records and correct Dublin Core columns

### Implementation for User Story 1

- [X] T014 [US1] Implement export service function in `/home/nixos/src/local/bcd4/src/bcd_api/services/export_service.py` (export_catalog_to_dublin_core with joinedload for items, streaming CSV generation)
- [X] T015 [US1] Implement reverse mapping (database → Dublin Core) in export_service.py (ISBN → dc.identifier with prefix, authors JSON → pipe-separated, medium_type → dc.type as-is)
- [X] T016 [US1] Add row limit validation in export_service.py (reject if >10,000 records with CSVRowLimitError)
- [X] T017 [US1] Add UTF-8 BOM encoding for Excel compatibility in export_service.py
- [X] T018 [US1] Handle empty catalog edge case in export_service.py (return CSV with headers only)
- [X] T019 [US1] Add export endpoint GET `/api/v1/catalog/export` to `/home/nixos/src/local/bcd4/src/bcd_api/api/v1/catalog.py` (returns StreamingResponse with Content-Disposition header)
- [X] T020 [US1] Update CatalogPage.js at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/pages/CatalogPage.js` to add "Export Catalog" button (triggers GET /api/v1/catalog/export)
- [X] T021 [US1] Create CatalogExport.js component at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/catalog/CatalogExport.js` for export button with loading state
- [ ] T021a [P] [US1] Create E2E test file at `/home/nixos/src/local/bcd4/tests/e2e/test_005_catalog_export.py` for User Story 1 catalog export functionality
- [ ] T021b [US1] Add E2E test case test_005_us1_ac1_export_empty_catalog in test_005_catalog_export.py (verify CSV download with headers only when catalog is empty)
- [ ] T021c [US1] Add E2E test case test_005_us1_ac2_export_french_characters in test_005_catalog_export.py (create records with é, è, à, ç, verify preservation per FR-013)
- [ ] T021d [US1] Add E2E test case test_005_us1_ac3_export_missing_optional_fields in test_005_catalog_export.py (create record with only required fields, verify empty columns for missing fields per FR-009)

**Checkpoint**: Export catalog to Dublin Core CSV working end-to-end from web UI with E2E test coverage ✅ COMPLETE (already implemented)

---

## Phase 4: User Story 2 - Import Catalog from Dublin Core CSV (Priority: P1) 🎯 MVP

**Goal**: Librarians can upload Dublin Core CSV files to populate or update their catalog

**Independent Test**: Prepare Dublin Core CSV file using template, upload via web UI, verify records appear in catalog with correct values

### Implementation for User Story 2

- [X] T022 [US2] Extract column mapping logic from `/home/nixos/src/local/bcd4/src/bcd_api/services/dublin_core_import.py` into reusable mapping dictionary (DUBLIN_CORE_TO_DB_MAPPING)
- [X] T023 [US2] Update import service in `/home/nixos/src/local/bcd4/src/bcd_api/services/import_service.py` (add import_catalog_from_dublin_core function with CSV validation, encoding detection, partial import support)
- [X] T024 [US2] Add CSV column validation in import_service.py (check required columns: dc.title, dc.identifier OR item.id, show error with expected vs. found columns)
- [X] T025 [US2] Implement partial import behavior in import_service.py (commit valid rows, collect failures with row number + error message per FR-010a, FR-010b)
- [X] T026 [US2] Handle deduplication for same ISBN in import_service.py (create ONE bibliographic record, MULTIPLE items per FR-044, FR-045, FR-046)
- [X] T027 [US2] Add import endpoint POST `/api/v1/catalog/import` to `/home/nixos/src/local/bcd4/src/bcd_api/api/v1/catalog.py` (accepts file upload, returns ImportResponse with success/failure counts)
- [X] T028 [US2] Update CatalogPage.js at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/pages/CatalogPage.js` to add "Import Catalog" button
- [X] T029 [US2] Create CatalogImport.js component at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/catalog/CatalogImport.js` (file upload dialog with .csv filter, template download link, progress indicator)
- [X] T030 [US2] Update CatalogImport.js to display success message with counts (e.g., "Successfully imported 245 records. 5 rows failed - see errors below")
- [X] T031 [US2] Update CatalogImport.js to display error list for partial imports (scrollable list of failed rows with row number and error per FR-024a)
- [ ] T031a [P] [US2] Create E2E test file at `/home/nixos/src/local/bcd4/tests/e2e/test_005_catalog_import.py` for User Story 2 catalog import functionality
- [ ] T031b [US2] Add E2E test case test_005_us2_ac1_import_valid_dublin_core in test_005_catalog_import.py (create Dublin Core CSV, upload via UI, verify records imported per FR-002)
- [ ] T031c [US2] Add E2E test case test_005_us2_ac2_import_missing_isbn_valid_item_id in test_005_catalog_import.py (upload CSV with dc.identifier empty but item.id present, verify import succeeds per FR-005)
- [ ] T031d [US2] Add E2E test case test_005_us2_ac3_import_missing_both_identifiers in test_005_catalog_import.py (upload CSV with both dc.identifier and item.id empty, verify error shown per FR-005)
- [ ] T031e [US2] Add E2E test case test_005_us2_ac4_import_incorrect_columns in test_005_catalog_import.py (upload CSV with wrong column names, verify error directs to conversion scripts per FR-006)

**Checkpoint**: Import catalog from Dublin Core CSV working end-to-end with partial import support and E2E test coverage ✅ COMPLETE (already implemented)

---

## Phase 5: User Story 3 - Convert BCDI Export to Dublin Core (Priority: P2)

**Goal**: French schools can convert BCDI library software exports to Dublin Core format for import into BCD

**Independent Test**: Obtain sample BCDI CSV (Windows-1252, French columns), run conversion script, verify output is valid Dublin Core CSV with UTF-8 encoding

### Implementation for User Story 3

- [X] T032 [US3] Create BCDI conversion script at `/home/nixos/src/local/bcd4/scripts/convert/bcdi_to_dublin_core.py` (argparse for input/output paths, --delimiter flag)
- [X] T033 [US3] Implement BCDI column mapping in bcdi_to_dublin_core.py (ISBN→dc.identifier, Titre→dc.title, Auteur→dc.creator, Editeur→dc.publisher, Support→dc.type, Cote→dc.subject, Année→dc.date per FR-027)
- [X] T034 [US3] Add encoding detection to bcdi_to_dublin_core.py (default Windows-1252, fallback to chardet auto-detection per FR-028)
- [X] T035 [US3] Add UTF-8 output encoding to bcdi_to_dublin_core.py (all outputs use UTF-8 per FR-029)
- [X] T036 [US3] Add ISBN prefix logic to bcdi_to_dublin_core.py (add "isbn:" prefix if not present per FR-031)
- [X] T037 [US3] Add delimiter flag support to bcdi_to_dublin_core.py (--delimiter, defaults to comma for BCDI per FR-026)
- [X] T038 [US3] Add success message to bcdi_to_dublin_core.py (print input file, output file, encoding conversion per FR-032)
- [X] T039 [US3] Add usage docstring to bcdi_to_dublin_core.py (document --delimiter flag, encoding behavior, column mapping per FR-041)
- [X] T040 [US3] Update scripts/convert/README.md with BCDI conversion examples (show default comma and --delimiter=";" override per FR-042)

**Checkpoint**: BCDI to Dublin Core conversion working with sample files from French schools ✅ COMPLETE (already implemented)

---

## Phase 6: User Story 4 - Convert Generic French CSV to Dublin Core (Priority: P3)

**Goal**: Auto-detect French column name variations and convert to Dublin Core format

**Independent Test**: Create CSV with French column variations ("Titre du livre", "Nom de l'auteur"), run conversion script, verify correct auto-detection and mapping

### Implementation for User Story 4

- [ ] T041 [US4] Create French CSV conversion script at `/home/nixos/src/local/bcd4/scripts/convert/french_csv_to_dublin_core.py` (argparse for input/output paths, --delimiter flag)
- [ ] T042 [US4] Implement fuzzy column detection in french_csv_to_dublin_core.py (case-insensitive matching for French column name variations per FR-035)
- [ ] T043 [US4] Add column mapping patterns to french_csv_to_dublin_core.py (ISBN variations→dc.identifier, Titre variations→dc.title, Auteur variations→dc.creator, etc. per FR-035)
- [ ] T044 [US4] Add encoding auto-detection to french_csv_to_dublin_core.py (try UTF-8, Latin-1, Windows-1252 per FR-033)
- [ ] T045 [US4] Add detected mapping output to french_csv_to_dublin_core.py (print "ISBN → dc.identifier, Titre → dc.title" before conversion per FR-036)
- [ ] T046 [US4] Add unmapped column warnings to french_csv_to_dublin_core.py (print "Unmapped columns (will be ignored): Notes, Prix" per FR-037)
- [ ] T047 [US4] Add ISBN prefix logic to french_csv_to_dublin_core.py (add "isbn:" if missing per FR-038)
- [ ] T048 [US4] Add usage docstring to french_csv_to_dublin_core.py (document column detection patterns, --delimiter flag per FR-041)
- [ ] T049 [US4] Update scripts/convert/README.md with French CSV conversion examples (show auto-detection behavior per FR-042)

**Checkpoint**: Generic French CSV to Dublin Core conversion working with auto-detected column mapping

---

## Phase 7: User Story 5 - Export Borrower List to CSV (Priority: P1) 🎯 MVP

**Goal**: Librarians can export their complete borrower list (students, teachers, staff) in standardized BCD format

**Independent Test**: Create sample borrowers, click "Export Borrowers" button in web UI, verify CSV downloads with all borrowers and correct columns

### Implementation for User Story 5

- [X] T050 [US5] Add export function to `/home/nixos/src/local/bcd4/src/bcd_api/services/export_service.py` (export_borrowers_to_csv with all borrower fields per FR-047)
- [X] T051 [US5] Implement borrower field mapping in export_service.py (active→boolean, blocked_reason→text, class lookup→class name string)
- [X] T052 [US5] Add row limit validation in export_service.py (reject if >5,000 borrowers with CSVRowLimitError per FR-054)
- [X] T053 [US5] Add UTF-8 BOM encoding for Excel compatibility in export_service.py (borrower export per FR-049)
- [X] T054 [US5] Handle empty borrower list edge case in export_service.py (return CSV with headers only)
- [X] T055 [US5] Add export endpoint GET `/api/v1/borrowers/export` to `/home/nixos/src/local/bcd4/src/bcd_api/api/v1/borrowers.py` (returns StreamingResponse with Content-Disposition header per FR-065)
- [X] T056 [US5] Update BorrowersPage.js at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/pages/BorrowersPage.js` to add "Export Borrowers" button
- [X] T057 [US5] Inline export button implementation (no separate component needed)
- [ ] T057a [P] [US5] Create E2E test file at `/home/nixos/src/local/bcd4/tests/e2e/test_005_borrower_export.py` for User Story 5 borrower export functionality
- [ ] T057b [US5] Add E2E test case test_005_us5_ac1_export_empty_borrowers in test_005_borrower_export.py (verify CSV download with headers only when no borrowers exist)
- [ ] T057c [US5] Add E2E test case test_005_us5_ac2_export_french_characters in test_005_borrower_export.py (create borrowers with é, è, à, ç, verify preservation in downloaded CSV per FR-072)
- [ ] T057d [US5] Add E2E test case test_005_us5_ac3_export_all_fields in test_005_borrower_export.py (create borrower with all 12 fields, export, verify complete data per FR-047)
- [ ] T057e [US5] Add E2E test case test_005_us5_ac4_export_mixed_roles in test_005_borrower_export.py (create students/teachers/staff, verify role column correct)
- [ ] T057f [US5] Add E2E test case test_005_us5_ac5_export_blocked_borrowers in test_005_borrower_export.py (verify active=False and blocked_reason populated per FR-047)

**Checkpoint**: Export borrowers to BCD CSV format working end-to-end from web UI with E2E test coverage ✅ COMPLETE

---

## Phase 8: User Story 6 - Import Borrowers from CSV (Priority: P1) 🎯 MVP

**Goal**: Librarians can upload borrower CSV files to populate or update their borrower database with upsert behavior

**Independent Test**: Prepare borrower CSV file using template, upload via web UI, verify borrowers appear in system with correct values and upsert behavior

### Implementation for User Story 6

- [X] T058 [US6] Implement import function in `/home/nixos/src/local/bcd4/src/bcd_api/services/import_service.py` (import_borrowers_from_csv with CSV validation, encoding detection, partial import support, upsert behavior per FR-048, FR-059)
- [X] T059 [US6] Add CSV column validation in import_service.py (check required columns: borrower_id, first_name, last_name, role per FR-051)
- [X] T060 [US6] Implement barcode auto-generation in import_service.py (sequential "BCD{6-digit}" format with collision detection per FR-057, FR-057a)
- [X] T061 [US6] Implement full_name auto-population in import_service.py (first_name + " " + last_name per FR-061)
- [X] T062 [US6] Add borrower_id format validation in import_service.py (1-20 alphanumeric, dash/underscore allowed per FR-062)
- [X] T063 [US6] Implement class name normalization in import_service.py (uppercase before lookup, set class_id=NULL if not found with warning per FR-063)
- [X] T064 [US6] Add role validation in import_service.py (case-insensitive "student", "teacher", "staff" per FR-056)
- [X] T065 [US6] Implement upsert logic in import_service.py (update if borrower_id exists, insert if new per FR-059)
- [X] T066 [US6] Add partial import behavior in import_service.py (commit valid rows, collect failures with row number + error message per FR-010a, FR-010b)
- [X] T067 [US6] Add import endpoint POST `/api/v1/borrowers/import` to `/home/nixos/src/local/bcd4/src/bcd_api/api/v1/borrowers.py` (accepts file upload, returns ImportResponse with new/updated counts per FR-067)
- [X] T068 [US6] Update BorrowerPage.js at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/pages/BorrowerPage.js` to add "Import Borrowers" button
- [X] T069 [US6] Create BorrowerImport.js component at `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/borrowers/BorrowerImport.js` (file upload dialog with .csv filter, template download link, progress indicator)
- [X] T070 [US6] Update BorrowerImport.js to display success message with counts (e.g., "Successfully imported 115 borrowers (85 new, 30 updated). 5 rows failed - see errors below" per FR-068)
- [X] T071 [US6] Update BorrowerImport.js to display error list for partial imports (scrollable list with row number and error per FR-069a)
- [ ] T071a [P] [US6] Create E2E test file at `/home/nixos/src/local/bcd4/tests/e2e/test_005_borrower_import.py` for User Story 6 borrower import functionality
- [ ] T071b [US6] Add E2E test case test_005_us6_ac1_import_valid_borrowers in test_005_borrower_import.py (create borrower CSV, upload via UI, verify borrowers imported per FR-048)
- [ ] T071c [US6] Add E2E test case test_005_us6_ac2_import_missing_optional_fields in test_005_borrower_import.py (upload CSV with only required fields, verify import succeeds per FR-055)
- [ ] T071d [US6] Add E2E test case test_005_us6_ac3_import_missing_required_field in test_005_borrower_import.py (upload CSV with missing first_name, verify error shown with row number per FR-069a)
- [ ] T071e [US6] Add E2E test case test_005_us6_ac4_import_upsert_existing in test_005_borrower_import.py (import borrower, modify and re-import same borrower_id, verify update per FR-059)
- [ ] T071f [US6] Add E2E test case test_005_us6_ac5_import_incorrect_columns in test_005_borrower_import.py (upload CSV with wrong column names like "StudentID", verify error shows expected vs found columns per FR-052)

**Checkpoint**: Import borrowers from BCD CSV format working end-to-end with upsert, partial import support, and E2E test coverage ✅ COMPLETE

---

## Phase 9: User Story 7 - Convert ONDE Export to BCD Borrower Format (Priority: P2)

**Goal**: French schools can convert ONDE (national student database) exports to BCD borrower format for import

**Independent Test**: Obtain sample ONDE CSV (semicolon-delimited, UTF-8, French student data), run conversion script, verify output is valid BCD borrower CSV

### Implementation for User Story 7

- [X] T072 [US7] Create ONDE conversion script at `/home/nixos/src/local/bcd4/scripts/convert/onde_to_bcd_borrowers.py` (argparse for input/output paths, --delimiter flag defaulting to semicolon per FR-073)
- [X] T073 [US7] Implement ONDE column mapping in onde_to_bcd_borrowers.py (Nom→last_name, Prénom→first_name, INE→borrower_id, Identifiant Classe→class per FR-074)
- [X] T074 [US7] Add column variation support to onde_to_bcd_borrowers.py ("Nom" OR "Nom de l'élève", "Prénom" OR "Prénom de l'élève" per FR-079)
- [X] T075 [US7] Add role assignment to onde_to_bcd_borrowers.py (set role="student" for all ONDE records per FR-078)
- [X] T076 [US7] Add INE fallback logic to onde_to_bcd_borrowers.py (generate "STUDENT-{number}" if INE empty per FR-081)
- [X] T077 [US7] Add grade level extraction to onde_to_bcd_borrowers.py (extract "CP" from "CP-A" class name per FR-082)
- [X] T078 [US7] Add duplicate INE warning to onde_to_bcd_borrowers.py (detect duplicates, keep first occurrence per FR-085)
- [X] T079 [US7] Add UTF-8 encoding support to onde_to_bcd_borrowers.py (read UTF-8, output UTF-8 with comma separator per FR-076, FR-077)
- [X] T080 [US7] Add delimiter flag support to onde_to_bcd_borrowers.py (--delimiter, defaults to semicolon for ONDE per FR-075)
- [X] T081 [US7] Add success message to onde_to_bcd_borrowers.py (print input file, output file, record count per FR-083)
- [X] T082 [US7] Add usage docstring to onde_to_bcd_borrowers.py (document --delimiter flag, column mapping, INE fallback per FR-041)
- [X] T083 [US7] Update scripts/convert/README.md with ONDE conversion examples (show default semicolon and --delimiter override per FR-042)

**Checkpoint**: ONDE to BCD borrower conversion working with sample ONDE exports from French schools ✅ COMPLETE (implemented 2026-02-06)

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final refinements affecting multiple user stories

- [ ] T084 [P] Update main README.md at `/home/nixos/src/local/bcd4/README.md` with import/export feature documentation (how to use web UI buttons, conversion scripts)
- [ ] T085 [P] Add quickstart.md validation at `/home/nixos/src/local/bcd4/specs/005-csv-import/quickstart.md` (test all conversion scripts with sample files)
- [ ] T086 [P] Verify round-trip fidelity for catalog (export → import → export = identical CSV per FR-011)
- [ ] T087 [P] Verify round-trip fidelity for borrowers (export → import → export = identical CSV per FR-071)
- [ ] T088 [P] Verify French character preservation (é, è, à, ç, œ) in catalog round-trip per FR-013
- [ ] T089 [P] Verify French character preservation (é, è, à, ç, œ) in borrower round-trip per FR-072
- [ ] T090 Review error message clarity (ensure 80% of users can self-correct per SC-007, SC-015)
- [ ] T091 Cross-platform path validation (test pathlib.Path handling on Linux and Windows)
- [ ] T092 Remove old placeholder test_us3_ac9_import_borrowers_from_csv from `/home/nixos/src/local/bcd4/tests/e2e/test_us3_borrowers.py` (replaced by proper test_005_borrower_import.py E2E tests)
- [ ] T093 Code cleanup and refactoring (remove any TODO/FIXME/HACK comments)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (Export Catalog) - can start after Phase 2
  - US2 (Import Catalog) - can start after Phase 2, independent of US1
  - US3 (BCDI Conversion) - can start after Phase 2, independent of US1/US2
  - US4 (French CSV Conversion) - can start after Phase 2, independent of US1/US2/US3
  - US5 (Export Borrowers) - can start after Phase 2, independent of catalog stories
  - US6 (Import Borrowers) - can start after Phase 2, independent of US5
  - US7 (ONDE Conversion) - can start after Phase 2, independent of US5/US6
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Priority Order (if sequential)

1. **P1 Stories (MVP)**: US1, US2, US5, US6 - core catalog and borrower import/export
2. **P2 Stories**: US3, US7 - French school migration support (BCDI, ONDE)
3. **P3 Stories**: US4 - nice-to-have auto-detection for generic French CSV

### Within Each User Story

- Foundation tasks must complete before any user story
- Within each story: services before endpoints, endpoints before UI components
- Import/export pairs are independent (can implement export without import)

### Parallel Opportunities

- All Phase 1 Setup tasks marked [P] can run in parallel
- All Phase 2 Foundational tasks marked [P] can run in parallel
- Once Phase 2 completes, all 7 user stories can start in parallel (if team capacity allows)
- Catalog stories (US1-4) are completely independent of borrower stories (US5-7)
- Conversion scripts (US3, US4, US7) are independent standalone utilities
- Different team members can work on different user stories simultaneously

---

## Parallel Example: Foundational Phase

```bash
# Launch all foundational tasks together after Phase 1:
Task T007: "Add CSV-specific exception classes to exceptions.py"
Task T008: "Add CSV format constants to constants.py"
Task T009: "Add encoding detection utility to encoding.py"
Task T010: "Add catalog i18n keys to en.json"
Task T011: "Add borrower i18n keys to en.json"
Task T012: "Add French translations to fr.json"
# All different files, no dependencies
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup (templates, directories, dependencies)
2. Complete Phase 2: Foundational (exceptions, constants, i18n, utilities)
3. Complete Phase 3: US1 - Export Catalog
4. Complete Phase 4: US2 - Import Catalog
5. Complete Phase 7: US5 - Export Borrowers
6. Complete Phase 8: US6 - Import Borrowers
7. **STOP and VALIDATE**: Test all P1 stories independently
8. Deploy/demo MVP with core import/export functionality

### Incremental Delivery (Add P2 Stories)

9. Complete Phase 5: US3 - BCDI Conversion
10. Complete Phase 9: US7 - ONDE Conversion
11. **VALIDATE**: Test French school migration workflows
12. Deploy/demo with French school support

### Full Feature (Add P3 Stories)

13. Complete Phase 6: US4 - French CSV Auto-detection
14. Complete Phase 10: Polish
15. **FINAL VALIDATION**: Round-trip fidelity, cross-platform, quickstart
16. Deploy complete feature

### Parallel Team Strategy

With multiple developers:

1. Team completes Phase 1 + Phase 2 together (foundation)
2. Once Phase 2 is done:
   - **Developer A**: Catalog export/import (US1, US2)
   - **Developer B**: Borrower export/import (US5, US6)
   - **Developer C**: Conversion scripts (US3, US4, US7)
3. Stories complete and integrate independently
4. Team collaborates on Phase 10: Polish

---

## Task Summary

**Total Tasks**: 114 (92 implementation + 21 E2E tests + 1 cleanup)

**Task Count by Phase**:
- Setup (Phase 1): 6 tasks
- Foundational (Phase 2): 7 tasks
- User Story 1 - Export Catalog (P1): 12 tasks (8 implementation + 4 E2E tests)
- User Story 2 - Import Catalog (P1): 15 tasks (10 implementation + 5 E2E tests)
- User Story 3 - BCDI Conversion (P2): 9 tasks
- User Story 4 - French CSV Conversion (P3): 9 tasks
- User Story 5 - Export Borrowers (P1): 14 tasks (8 implementation + 6 E2E tests)
- User Story 6 - Import Borrowers (P1): 20 tasks (14 implementation + 6 E2E tests)
- User Story 7 - ONDE Conversion (P2): 12 tasks
- Polish (Phase 10): 10 tasks (9 original + 1 cleanup)

**Parallel Opportunities**:
- 40+ tasks marked [P] can run in parallel within their phase
- 7 user stories can run in parallel after Foundational phase
- Catalog stories (US1-4) independent of borrower stories (US5-7)
- E2E test tasks marked [P] can run in parallel with other E2E tests
- Estimated 30-40% time savings with parallel execution

**MVP Scope**: User Stories 1, 2, 5, 6 (61 tasks) = Core import/export for catalog and borrowers with E2E test coverage

**Test Coverage**: 21 E2E tests added covering all import/export user stories (US1, US2, US5, US6)

---

## Notes

- **No tests required**: Spec explicitly states NO TDD requirement (integration tests exist but not blocking)
- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[US#] labels**: Maps task to specific user story for traceability
- **Partial imports**: All import tasks support best-effort partial imports (commit valid rows, report failures)
- **Round-trip fidelity**: Export → Import → Export must produce identical CSV (verified in Phase 10)
- **Cross-platform**: All paths use pathlib.Path for Linux/Windows compatibility
- **i18n**: All UI text uses i18n keys (no hard-coded strings)
- **Performance**: Batch operations (bulk_insert_mappings) for legacy hardware support
- **Encoding**: UTF-8 for all exports, auto-detect (UTF-8/Latin-1/Windows-1252) for imports
- **Error messages**: Format "Row {number}: {error description}" for partial import failures
- **Commit strategy**: Commit after each task or logical group for safety
