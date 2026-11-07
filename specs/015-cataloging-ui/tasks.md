# Tasks: Fast Cataloging Workflow

**Input**: Design documents from `/specs/015-cataloging-ui/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/cataloging-route.md`, `quickstart.md`

**Organization**: Tasks are grouped by user story so layout, navigation, remote text discovery, and cover work can be verified independently.

## Phase 1: Setup

**Purpose**: The repository already has Vue, FastAPI, provider clients, and JS/Python test runners. No dependency or project setup changes are required.

## Phase 2: Foundational

**Purpose**: No new shared infrastructure is needed. Each story can use the current router, API client, catalog services, and localization framework.

**Checkpoint**: Existing infrastructure is ready; begin story-specific work.

## Phase 3: User Story 1 - Fast scanning layout (Priority: P1)

**Goal**: Keep the current step and primary action accessible without page scrolling and let the librarian begin a new book with one existing action.

**Independent Test**: At 1280×720, verify the stepper, step content, and primary action are visible, and the existing new-book action is available without scrolling.

### Tests

- [x] T001 [P] [US1] Add a CatalogingPage test that verifies the stepper and existing new-book action are rendered in the page heading area in `tests/js/pages/cataloging/CatalogingPage.test.js`

### Implementation

- [x] T002 [US1] Reposition the existing stepper and new-book action into a compact persistent top area without duplicating actions in `src/bcd_web_vue/js/pages/CatalogingPage.js`
- [x] T003 [US1] Keep the copy barcode input and its primary action above secondary copy lists at the standard viewport in `src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js`

**Checkpoint**: The layout can be independently checked at the target viewport without changing catalog behavior.

## Phase 4: User Story 2 - Keyboard and browser navigation (Priority: P1)

**Goal**: Make workflow state navigable through the URL and browser history while preserving saved records and scanner focus.

**Independent Test**: Move through lookup, saved notice, and copy creation; use Back/Forward and refresh; verify route state and persisted data match without restoring unsaved form fields.

### Tests

- [x] T004 [P] [US2] Add tests for route query changes, saved-record restoration, Back/Forward, and invalid route state in `tests/js/pages/cataloging/CatalogingPage.test.js`
- [x] T005 [P] [US2] Add tests for restoring the lookup value and focusing the scan field after reset in `tests/js/components/cataloging/FindNotice.test.js`

### Implementation

- [x] T006 [US2] Derive the active step from `step`, lookup value, and `record_id` route query; push transitions and replace reset/canonical states in `src/bcd_web_vue/js/pages/CatalogingPage.js`
- [x] T007 [US2] Reload persisted notices and copies from existing catalog APIs when browser history restores a saved step in `src/bcd_web_vue/js/pages/CatalogingPage.js`
- [x] T008 [US2] Scope Escape reset to the cataloging page, preserve existing contextual Enter submission, prevent duplicate actions, and return focus to the lookup scanner in `src/bcd_web_vue/js/pages/CatalogingPage.js`
- [x] T009 [US2] Prefill the lookup field from the restored route value without restoring unsaved bibliographic or copy fields in `src/bcd_web_vue/js/components/cataloging/FindNotice.js`

**Checkpoint**: Back/Forward and refresh restore only valid route state and persisted catalog data; Escape starts a clean workflow without deleting saved data.

## Phase 5: User Story 3 - Search remote catalogs by text (Priority: P1)

**Goal**: After a local text-search miss, display selectable BnF, Google Books, and SUDOC candidates with available covers; keep ISBN/ISSN behavior unchanged.

**Independent Test**: Search for a title absent locally, verify local-first ordering, inspect multiple remote candidates, select one to prefill the form, and verify provider failure still allows another source or manual entry.

### Tests

- [x] T010 [P] [US3] Test that free text routes to BnF, Google Books, and SUDOC while ISBN/ISSN and unsupported-barcode routing remain unchanged in `tests/integration/services/test_catalog_notice_lookup.py`
- [x] T011 [P] [US3] Test BnF title query parsing, diagnostic-record filtering, candidate limit, empty results, and timeout propagation in `tests/unit/services/test_bnf.py`
- [x] T012 [P] [US3] Test Google Books text query results, candidate limit, cover URLs, and empty results in `tests/unit/services/test_google_books.py`
- [x] T013 [P] [US3] Test SUDOC text candidates, candidate limit, missing covers, empty results, and timeout propagation in `tests/unit/services/test_sudoc.py`
- [x] T014 [P] [US3] Test text-search candidate selection, local-first behavior, provider continuation, and manual fallback in `tests/js/components/cataloging/FindNotice.test.js`
- [x] T015 [P] [US3] Test the text lookup candidate response shape and unchanged ISBN/ISSN response behavior in `tests/api/test_cataloging_notice_endpoints.py`
- [x] T016 [US3] Replaced the feature-specific browser journey with Vitest, provider, service, and API coverage per user preference to avoid additional E2E tests.

### Implementation

- [x] T017 [US3] Route non-empty free-text input to BnF, Google Books, and SUDOC while preserving ISBN, ISSN, and unsupported-barcode routing in `src/bcd_api/utils/catalog_input.py`
- [x] T018 [US3] Add bounded BnF title search using the SRU title index, ignore diagnostic records, and parse up to 10 usable candidates in `src/bcd_api/services/external/bnf.py`
- [x] T019 [US3] Add bounded Google Books free-text search returning up to 10 normalized candidates with available cover URLs in `src/bcd_api/services/external/google_books.py`
- [x] T020 [US3] Add bounded SUDOC free-text search returning up to 10 normalized Pica+ candidates in `src/bcd_api/services/external/sudoc.py`
- [x] T021 [US3] Extend single-source lookup to return text candidate lists, retain the local recheck, apply configured timeouts, and preserve identifier lookup responses in `src/bcd_api/services/catalog/notice_lookup.py`
- [x] T022 [US3] Add local-first remote-candidate rendering, source attribution, explicit candidate selection, next-source controls, and manual-entry fallback in `src/bcd_web_vue/js/components/cataloging/FindNotice.js`
- [x] T023 [P] [US3] Add matching English and French labels for remote candidates, source continuation, and selection actions in `src/bcd_web_vue/locales/en.json` and `src/bcd_web_vue/locales/fr.json`

**Checkpoint**: Text-search candidates are bounded, never auto-selected, and lead into the existing review form; empty, disabled, or failed providers do not block fallback.

## Phase 6: User Story 4 - See covers throughout cataloging (Priority: P2)

**Goal**: Show an available cover in bibliographic review and copy creation, and keep the workflow usable when no image can be loaded.

**Independent Test**: Use a notice with a cover and one without; verify both screens show the available cover only and that image failure does not block adding a copy.

### Tests

- [x] T024 [P] [US4] Test that copy creation displays the notice cover and hides a failed/missing image without blocking the barcode form in `tests/js/components/cataloging/ItemBarcodeInput.test.js`
- [x] T025 [P] [US4] Test that the bibliographic preview supports a selected text-search candidate's cover URL in `tests/js/components/cataloging/BibliographicForm.test.js`

### Implementation

- [x] T026 [US4] Pass the persisted record cover through the cataloging page and display it beside the copy scanner with a safe image-error fallback in `src/bcd_web_vue/js/pages/CatalogingPage.js` and `src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js`
- [x] T027 [US4] Preserve remote cover URLs and existing local cover references in bibliographic prefill and preview in `src/bcd_web_vue/js/components/cataloging/BibliographicForm.js`

**Checkpoint**: Covers appear when available on both steps; image absence or failure has no effect on cataloging actions.

## Phase 7: Polish and cross-cutting validation

**Purpose**: Document the feature and validate the full acceptance criteria.

- [x] T028 [P] Update the Unreleased entry for the cataloging workflow and text search in `CHANGELOG.md`
- [x] T029 Run the focused backend suites for catalog lookup and all three providers in `tests/integration/services/test_catalog_notice_lookup.py`, `tests/unit/services/test_bnf.py`, `tests/unit/services/test_google_books.py`, and `tests/unit/services/test_sudoc.py`
- [x] T030 Run the JavaScript suite and verify bilingual labels, keyboard, history, and provider-fallback behavior with focused tests; no performance tests were added.
- [x] T031 Run the existing browser smoke test; the feature-specific remote selection journey is covered by JS, provider, service, and API tests instead.

## Dependencies

```text
US1 ─────┐
         ├── independent
US2 ─────┘
US2 -> US3 (text query restoration and route state)
US4 is independent of US3 for notice/copy covers; remote candidate covers are tested with US3.
```

## Parallel execution

- US1: T001 can be written independently from provider work; T002 and T003 touch separate files but should be validated together at the viewport.
- US2: T004 and T005 can be authored in parallel; route implementation in T006-T009 must use a single route-state contract.
- US3: T010-T015 are independent unit/API/service tests; T016 is the sole browser journey test and uses mocked provider data. T018-T020 are separate provider adapters; T023 is independent locale work. T021 depends on T017-T020, and T022 depends on the response contract from T021.
- US4: T024 and T025 can be authored in parallel; T026/T027 update separate components and can be developed independently after their tests.

## Implementation strategy

Complete layout and route/navigation foundations first. Deliver remote text search as a separate increment with independently selectable provider results and the existing manual fallback. Add cover propagation after candidate data is available, then run focused JavaScript/Python suites and one deterministic browser-to-API journey for the critical remote-selection flow. Keep all other permutations at the component/API boundaries. Live provider probes are not part of the automated suite. No dependency installation, migration, or schema change is expected.
