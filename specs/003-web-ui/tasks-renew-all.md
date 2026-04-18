# Tasks: Renew All Feature (Web UI Enhancement)

**Input**: Enhancement to existing Web UI - add "Renew All" buttons to circulation and borrower management
**Prerequisites**: plan-renew-all.md (complete), spec.md (scenarios 9-10, 13-14 added), existing web UI implementation

**Tests**: Manual testing only (consistent with existing web UI testing approach - no automated E2E tests requested, though test scenarios defined for future)

**Organization**: This enhancement spans two user stories: User Story 1 (Circulation Dashboard) and User Story 3 (Borrower Management). All tasks are web UI focused with minimal backend changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 (Circulation Dashboard)
- **[US3]**: User Story 3 (Borrower Management)
- **[BOTH]**: Shared between both stories
- Include exact file paths and implementation details in descriptions

## Path Conventions

- Backend API: `src/bcd_api/api/v1/circulation.py` (minimal changes - add htmx support only)
- Templates: `src/bcd_web/templates/fragments/` (borrower_info.html, borrower_detail.html, new renew_confirmation.html)
- JavaScript: `src/bcd_web/js/pages/` (circulation.js, borrowers.js)
- Translations: `src/bcd_web/locales/` (en.json, fr.json)
- Tests: `tests/e2e/` (optional future implementation)

---

## Phase 1: Shared Infrastructure (Blocking Prerequisites)

**Goal**: Add htmx dual-response support to existing renewal endpoint and create shared confirmation template

**Why these tasks block**: Both circulation and borrower management need the API to return HTML for htmx requests, and both use the same confirmation template. Must complete before any UI work.

### Backend API (No Changes Needed)

- [X] T001 [BOTH] Verify POST /api/v1/circulation/renew endpoint exists in src/bcd_api/api/v1/circulation.py - confirm it accepts borrower_id and item_ids parameters, returns JSON response with renewed/failed arrays - NO CODE CHANGES needed, endpoint already exists and returns JSON

**Note**: Following block/unblock pattern - API returns JSON, UI uses JavaScript to display results

**Checkpoint**: API endpoint verified and returns JSON (consistent with block/unblock pattern)

---

## Phase 2: User Story 1 - Circulation Dashboard Implementation 🎯 MVP

**Goal**: Add "Renew All" button to borrower info panel on circulation page to enable single-click renewal during checkout workflow

**User Story Context**: Enhances User Story 1 (Circulation Dashboard - P1 Priority). Implements acceptance scenarios 9-10.

**Independent Test**:
1. Start web UI: `python -m src.bcd_web.server`
2. Navigate to `http://127.0.0.1:8888/#circulation`
3. Enter borrower ID "106" (has 3 items with 0/2 renewals)
4. Click "Renew All" button → Verify green success alert "Renewed 3 item(s)"
5. Enter borrower ID "107" (has 2 renewable + 1 at limit)
6. Click "Renew All" → Verify mixed result: 2 success + 1 warning
7. Test both English and French languages

### Internationalization (i18n)

- [X] T002 [P] [US1] Add English translations to src/bcd_web/locales/en.json - in circulation section add keys: renew_all: "Renew All", renewing: "Renewing items...", renewed_successfully: "Renewed {count} item(s) successfully", renewal_failed: "Failed to renew {count} item(s)", renewal_limit_reached: "Renewal limit reached", and in common section add renew_error: "Error renewing items"
- [X] T003 [P] [US1] Add French translations to src/bcd_web/locales/fr.json - in circulation section add keys matching en.json: renew_all: "Tout renouveler", renewing: "Renouvellement en cours...", renewed_successfully: "Renouvelé {count} document(s) avec succès", renewal_failed: "Échec du renouvellement de {count} document(s)", renewal_limit_reached: "Limite de renouvellement atteinte", and in common section add renew_error: "Erreur lors du renouvellement"

### UI Components - Circulation Page

- [X] T004 [US1] Add "Renew All" button to src/bcd_web/templates/fragments/borrower_info.html after current loans list (around line 25) - add Jinja2 conditional: {% if current_loans and current_loans_count > 0 %}, create button with class="btn btn-sm btn-primary mt-2", onclick="renewAll('{{ borrower.borrower_id }}')", data-i18n="circulation.renew_all", initial text "Renew All", {% endif %}

### JavaScript - Renewal Functionality

- [X] T005 [US1] Implement renewAll function in src/bcd_web/js/pages/circulation.js after loadBorrowerInfo function (around line 85) - create async function renewAll(borrowerId) matching block/unblock pattern: (1) show loading notification showNotification('info', i18n.t('circulation.renewing')), (2) POST to /api/v1/circulation/renew with body {borrower_id: borrowerId, item_ids: null}, Accept: application/json header, (3) if response.ok parse JSON data, build success message showing data.renewed_count and data.failed_count, call showNotification with success/warning based on results, then call loadBorrowerInfo(borrowerId) to refresh display, (4) on error show error notification

### Manual Testing - Circulation Page

- [X] T006 [US1] Execute manual testing checklist for circulation page - verify (1) "Renew All" button appears only when borrower has loans, (2) button hidden when no loans, (3) click renews all eligible items and shows success notification with renewed count (e.g., "Renewed 3 item(s) successfully"), (4) partial renewal shows notification mentioning both success and failure counts (e.g., "Renewed 2 item(s), failed 1 item(s)"), (5) borrower info panel refreshes automatically with new due dates, (6) both English "Renew All" and French "Tout renouveler" work, (7) no console errors, (8) pattern matches block/unblock (JSON response, notification display)

**Checkpoint**: ✅ MVP COMPLETE - Renew All working on circulation page (primary 80% workflow) using standard JSON + notification pattern

---

## Phase 3: User Story 3 - Borrower Management Implementation

**Goal**: Add "Renew All" button to borrower detail modal to enable renewal from borrower management interface

**User Story Context**: Enhances User Story 3 (Borrower Management - P3 Priority). Implements acceptance scenarios 13-14.

**Independent Test**:
1. Navigate to `http://127.0.0.1:8888/#borrowers`
2. Click borrower "106" to open detail modal
3. Click "Renew All" button in modal footer
4. Verify renewal summary displays within modal (not new page)
5. Verify current loans table refreshes with updated due dates
6. Test both English and French languages

### Internationalization (i18n)

**Note**: Borrower management uses same i18n keys from circulation section (already added in T002-T003), no additional keys needed

### UI Components - Borrower Detail Modal

- [X] T007 [US3] Add "Renew All" button to src/bcd_web/templates/fragments/borrower_detail.html modal footer (around line 95) - add Jinja2 conditional: {% if current_loans_count > 0 %}, create button with class="btn btn-primary", onclick="renewAllItems('{{ borrower.borrower_id }}')", data-i18n="circulation.renew_all", initial text "Renew All", place before existing Close and Edit buttons, {% endif %}

### JavaScript - Renewal Functionality

- [X] T008 [US3] Implement renewAllItems function in src/bcd_web/js/pages/borrowers.js after confirmUnblockBorrower function (around line 530) - create async function matching confirmBlockBorrower pattern: (1) show loading notification showNotification('info', i18n.t('circulation.renewing')), (2) POST to /api/v1/circulation/renew with body {borrower_id: borrowerId, item_ids: null}, Accept: application/json header, (3) if response.ok parse JSON data, show success notification with renewed_count and failed_count, then call htmx.ajax('GET', `/api/v1/borrowers/${borrowerId}?detail=true`, {target: '#borrower-detail-modal-content', swap: 'innerHTML'}) to refresh modal without closing, (4) on error show error notification

### Manual Testing - Borrower Detail Page

- [X] T009 [US3] Execute manual testing checklist for borrower detail page - verify (1) "Renew All" button appears in modal footer only when borrower has loans, (2) button hidden when no loans, (3) click renews all items and shows notification with counts, (4) partial renewal shows notification mentioning both success and failure counts, (5) borrower detail modal refreshes with new due dates (modal stays open), (6) both English and French work, (7) behavior identical to circulation page (JSON response, notification pattern), (8) pattern matches block/unblock implementation exactly, (9) no console errors

**Checkpoint**: ✅ FEATURE COMPLETE - Renew All working in both locations with identical JSON + notification pattern

---

## Phase 4: Optional E2E Tests (Future Enhancement)

**Purpose**: Automated browser-based tests using Playwright (can be deferred)

**Note**: Manual testing is sufficient per existing web UI approach. These E2E tests are defined in spec but not required for feature deployment. Implement when E2E test infrastructure is prioritized.

### E2E Tests - Circulation Page

- [ ] T010 [US1] Create test_renew_all_success in tests/e2e/test_circulation.py - test that: (1) loads borrower with 3 renewable items, (2) clicks "Renew All" button, (3) asserts success notification displays with "Renewed 3 item(s) successfully", (4) verifies borrower info refreshes with new due dates (old_due_date + 14 days), (5) checks no error messages appear
- [ ] T011 [US1] Create test_renew_all_partial in tests/e2e/test_circulation.py - test that: (1) loads borrower with 2 renewable items + 1 at limit (2/2 renewals), (2) clicks "Renew All", (3) asserts notification shows "Renewed 2 item(s), failed 1 item(s)" or similar mixed result message, (4) verifies borrower info refreshes with updated due dates for renewed items, (5) checks items at limit remain unchanged

### E2E Tests - Borrower Detail Page

- [ ] T012 [US3] Create test_renew_all_from_detail in tests/e2e/test_borrowers.py - test that: (1) opens borrower detail modal, (2) clicks "Renew All" button in footer, (3) asserts success notification displays, (4) verifies modal stays open (not closed), (5) checks current loans table refreshed with new due dates, (6) verifies no navigation occurred (still on borrowers page)
- [ ] T013 [US3] Create test_renew_all_mixed_results in tests/e2e/test_borrowers.py - test that: (1) loads borrower with mixed renewal states (some renewable, some at limit), (2) clicks "Renew All", (3) asserts notification shows both success and failure counts, (4) verifies modal refreshes showing updated due dates for renewed items only, (5) checks notification message is clear and informative

**Checkpoint**: E2E tests implemented - automated regression testing available

---

## Dependencies & Execution Strategy

### Task Dependencies

```text
Phase 1 (Verification - Quick Check)
  └─ T001 (verify API exists) ─────────┐
                                       │
                    ┌──────────────────┴──────────────────┐
                    ↓                                     ↓
Phase 2 (Circulation - US1)              Phase 3 (Borrower Detail - US3)
  ├─ T002 (en.json) ──┐                   (uses same translations from Phase 2)
  ├─ T003 (fr.json) ──┼─→ T004 (button)
  └────────────────┬──→ T005 (JS func)    T007 (button) ─→ T008 (JS func)
                   │                                    └─→ T009 (test)
                   └─→ T006 (test)
                                      │
                                      └──────────┬───────────────────┘
                                                 ↓
                                    Phase 4 (Optional E2E Tests)
                                      ├─ T010 (success test)
                                      ├─ T011 (partial test)
                                      ├─ T012 (detail test)
                                      └─ T013 (mixed results test)
```

### Parallel Execution Opportunities

**Phase 1** is just verification (1-2 minutes) - not blocking, just confirms API exists.

**After Phase 1**, Phases 2 and 3 are **FULLY INDEPENDENT** - can be done in parallel by different developers or sequentially.

**Within Phase 2** (Circulation):
- **Round 1** (parallel): T002 (en.json) + T003 (fr.json)
- **Round 2** (after Round 1): T004 (button)
- **Round 3** (after Round 2): T005 (JS function)
- **Round 4**: T006 (manual testing)

**Within Phase 3** (Borrower Detail):
- **Round 1**: T007 (button) - reuses translations from Phase 2
- **Round 2** (after Round 1): T008 (JS function)
- **Round 3**: T009 (manual testing)

**Phase 4** (all 4 tests can run in parallel)

### MVP vs Full Feature

**MVP Scope** (minimum viable product):
- Phase 1: T001 (verification only - 5 minutes)
- Phase 2: T002-T006 (circulation page)
- **Total**: 6 tasks
- **Result**: Renew All working on primary circulation workflow (80% of daily usage)
- **Time Estimate**: 1-2 hours for experienced developer

**Full Feature Scope**:
- Phase 1: T001
- Phase 2: T002-T006
- Phase 3: T007-T009
- **Total**: 9 tasks
- **Result**: Renew All working in both locations with identical JSON + notification pattern
- **Time Estimate**: 2-3 hours for experienced developer

**With E2E Tests** (future):
- All phases: T001-T013
- **Total**: 13 tasks
- **Time Estimate**: Add 2-3 hours for E2E test implementation

---

## Testing Summary

### Manual Test Scenarios (Required - 10 scenarios)

**Circulation Page** (5 scenarios):
1. **Full renewal** - All items renewable → Verify all renewed with green success
2. **Partial renewal** - Mix of renewable and at-limit → Verify green + orange alerts
3. **No loans** - Borrower with 0 items → Verify button not shown
4. **Blocked borrower** - Blocked status → Verify error handling
5. **French language** - Switch to FR → Verify "Tout renouveler" and all text

**Borrower Detail Page** (5 scenarios):
1. **Full renewal** - All items renewable → Verify success within modal
2. **Partial renewal** - Mix of states → Verify success/failure breakdown
3. **Modal stays open** - After renewal → Verify modal doesn't close
4. **Table refresh** - After renewal → Verify current loans updated
5. **Identical to circulation** - Same borrower → Verify same results in both locations

### Automated E2E Tests (Optional - 4 tests)

| Test File | User Story | Test Count | Focus |
|-----------|------------|------------|-------|
| `test_circulation.py` | US1 | 2 | Full renewal + partial renewal |
| `test_borrowers.py` | US3 | 2 | Modal renewal + failure display |

---

## Task Summary

**Total Tasks**: 13 tasks (9 implementation + 4 optional E2E tests)

**By Phase**:
- Phase 1 (Verification): 1 task (verify existing API)
- Phase 2 (Circulation Page - US1): 5 tasks 🎯 MVP
- Phase 3 (Borrower Detail - US3): 3 tasks
- Phase 4 (E2E Tests - Optional): 4 tasks

**By Type**:
- Backend API: 1 task (T001 - verify existing endpoint, NO changes)
- HTML templates: 2 tasks (T004, T007 - add buttons only)
- JavaScript: 2 tasks (T005, T008 - renewal functions)
- Translations: 2 tasks (T002, T003 - en/fr keys)
- Manual testing: 2 tasks (T006, T009)
- E2E tests: 4 tasks (T010-T013, optional)

**Parallelizable Tasks**: 2 tasks marked [P] (T002, T003 - translations)

**Independent Phases**: Phases 2 and 3 fully parallel after Phase 1 verification

**Suggested MVP**: Phases 1-2 (6 tasks, ~1-2 hours)

**Format Validation**: ✅ All 13 tasks follow checklist format with Task ID, [P] marker (where applicable), [Story] label, exact file paths, and detailed implementation notes **matching block/unblock pattern exactly** (JSON response + notifications, NO htmx dual-response)

---

## Implementation Checklist

### Pre-Implementation

- [ ] Read plan-renew-all.md (understand design decisions, especially "no auto-unblocking")
- [ ] Review spec.md scenarios 9-10 (US1) and 13-14 (US3) for acceptance criteria
- [ ] Review existing circulation.js and borrowers.js code patterns
- [ ] Verify API endpoint POST /circulation/renew exists and accepts borrower_id + item_ids params
- [ ] Verify existing renew endpoint returns success/failure breakdown with items arrays

### Phase 1: Shared Infrastructure

- [ ] Complete T001 (API htmx support) ✅ Test: curl with HX-Request header returns HTML
- [ ] Complete T002 (confirmation template) ✅ Test: template renders with sample data
- [ ] **GATE**: Phase 1 must be complete and tested before proceeding

### Phase 2: Circulation Page (MVP)

- [ ] Complete T003-T004 (translations) ✅ Test: language switcher shows correct strings
- [ ] Complete T005-T006 (UI components) ✅ Test: button appears, container exists
- [ ] Complete T007 (JavaScript) ✅ Test: click button, check network tab for POST
- [ ] Complete T008 (manual testing) ✅ All 5 circulation scenarios pass
- [ ] **MILESTONE**: MVP deployed - circulation workflow enhanced

### Phase 3: Borrower Detail (Full Feature)

- [ ] Complete T009-T010 (translations) ✅ Test: borrower section translations work
- [ ] Complete T011-T012 (UI components) ✅ Test: button in modal, results container
- [ ] Complete T013 (JavaScript) ✅ Test: renewal works, modal stays open
- [ ] Complete T014 (manual testing) ✅ All 5 borrower detail scenarios pass
- [ ] **MILESTONE**: Full feature deployed - both locations working

### Phase 4: E2E Tests (Optional, Future)

- [ ] Complete T015-T016 (circulation tests) ✅ Playwright tests passing
- [ ] Complete T017-T018 (borrower tests) ✅ Playwright tests passing
- [ ] **MILESTONE**: Automated regression testing available

### Deployment

- [ ] All manual tests passing in Chrome, Firefox, Safari, Edge
- [ ] No console errors or warnings in browser DevTools
- [ ] Performance acceptable (API call + UI update <600ms)
- [ ] French translations verified by native speaker (if available)
- [ ] Documentation updated (update quickstart.md with renew all examples)
- [ ] Git commit with message: "feat(web-ui): add Renew All button to circulation and borrower management"

---

## Quick Start for Developers

### Setup

```bash
# 1. Ensure development environment running
python -m src.bcd_web.server

# 2. Open browser to circulation page
http://127.0.0.1:8888/#circulation

# 3. Have two borrowers ready for testing:
#    - Borrower 106: 3 items, all renewable (0/2)
#    - Borrower 107: 2 renewable + 1 at limit (2/2)
```

### Implementation Order

```bash
# Phase 1: Verification (Quick - 5 minutes)
1. Verify: src/bcd_api/api/v1/circulation.py - confirm POST /renew exists and returns JSON
   (NO CODE CHANGES NEEDED)

# Phase 2: Circulation (MVP - 1-2 hours)
2-3. Edit: src/bcd_web/locales/en.json and fr.json (add ~6 translation keys each)
4. Edit: src/bcd_web/templates/fragments/borrower_info.html (add "Renew All" button)
5. Edit: src/bcd_web/js/pages/circulation.js (add renewAll function - similar to confirmBlockBorrower)
6. Manual test: 5 scenarios

# Phase 3: Borrower Detail (Full Feature - 1 hour)
7. Edit: src/bcd_web/templates/fragments/borrower_detail.html (add "Renew All" button in modal footer)
8. Edit: src/bcd_web/js/pages/borrowers.js (add renewAllItems function - copy pattern from confirmBlockBorrower)
9. Manual test: 5 scenarios
```

**Total implementation time**: 2-3 hours (vs 4-6 hours with old htmx dual-response approach)

### Testing Commands

```bash
# Manual testing (required)
# 1. Test full renewal: Enter borrower 106 → Click "Renew All"
# 2. Test partial renewal: Enter borrower 107 → Click "Renew All"
# 3. Test no loans: Enter borrower with 0 items → Verify button hidden
# 4. Test French: Click FR → Verify "Tout renouveler"
# 5. Test borrower detail: Open modal → Click "Renew All" → Verify modal stays open

# E2E testing (optional, future)
pytest tests/e2e/test_circulation.py::test_renew_all_success -v --headed
pytest tests/e2e/test_circulation.py::test_renew_all_partial -v --headed
pytest tests/e2e/test_borrowers.py::test_renew_all_from_detail -v --headed
```

---

## Success Criteria

✅ **Feature complete when**:

**Phase 1**:
- [ ] Verified POST /api/v1/circulation/renew endpoint exists
- [ ] Confirmed it accepts borrower_id and item_ids parameters
- [ ] Confirmed it returns JSON with renewed/failed arrays

**Phase 2 (MVP)**:
- [ ] "Renew All" button appears in borrower info panel when loans > 0
- [ ] Button hidden when no current loans
- [ ] Click calls POST /circulation/renew with JSON body
- [ ] Success notification displays with message "Renewed X item(s) successfully" (green toast)
- [ ] Partial renewal shows "Renewed X item(s), failed Y item(s)" notification (warning/orange toast)
- [ ] Borrower info panel refreshes automatically with new due dates
- [ ] French translation "Tout renouveler" works
- [ ] No console errors
- [ ] Performance <600ms (API + UI refresh)
- [ ] **Pattern matches block/unblock** (JSON response, notification, refresh)

**Phase 3 (Full Feature)**:
- [ ] "Renew All" button appears in borrower detail modal footer when loans > 0
- [ ] Button hidden when no current loans
- [ ] Click calls POST /circulation/renew with JSON body (identical to Phase 2)
- [ ] Success notification displays (green toast)
- [ ] Borrower detail modal refreshes via htmx.ajax (modal stays open)
- [ ] Current loans table shows updated due dates
- [ ] Behavior identical to circulation page for same borrower
- [ ] French translation works in modal context
- [ ] **Pattern matches confirmBlockBorrower/confirmUnblockBorrower exactly**
- [ ] No console errors

**Phase 4 (Optional)**:
- [ ] All 4 E2E tests passing
- [ ] Tests run on all browsers (Chromium, Firefox, WebKit)
- [ ] No flaky tests (100% reliable)

---

**Ready for**: Manual implementation starting with T001 (verify API), then T002-T009, or automated implementation using `/speckit.implement --feature-dir specs/003-web-ui --tasks-file tasks-renew-all.md`

**Key Pattern Change**: Now uses standard **JSON response + notification** pattern (matching block/unblock) instead of htmx dual-response. This is simpler, more consistent, and requires NO backend API changes.
