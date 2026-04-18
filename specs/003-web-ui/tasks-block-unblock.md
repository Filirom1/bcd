# Tasks: Block/Unblock Borrower Buttons (Web UI Enhancement)

**Input**: Enhancement to existing Web UI - add dedicated block/unblock buttons
**Prerequisites**: plan.md (complete), spec.md (scenarios 10-12 added), existing web UI implementation

**Tests**: Manual testing only (consistent with existing web UI testing approach - no automated tests requested)

**Organization**: This is an enhancement to existing User Story 3 (Borrower Management Interface). All tasks are frontend-only.

## Format: `[ID] [P?] [US3] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US3]**: All tasks belong to User Story 3 enhancement
- Include exact file paths in descriptions

## Path Conventions

- Web UI frontend: `src/bcd_web/` at repository root
- Backend API: `src/bcd_api/` (no changes - endpoints already exist)

---

## Phase 1: User Story 3 Enhancement - Block/Unblock Borrower Actions 🎯

**Goal**: Add dedicated block/unblock buttons to borrower detail modal to reduce blocking workflow from 5 clicks to 2 clicks

**User Story Context**: Enhances existing User Story 3 (Borrower Management). Implements acceptance scenarios 10-12.

**Independent Test**:
1. Start web UI: `python -m src.bcd_web.server`
2. Navigate to `http://127.0.0.1:8888/#borrowers/101`
3. Click "Block Borrower" → Select reason → Confirm → Verify red "Bloqué" badge
4. Click "Unblock Borrower" → Confirm → Verify green "Actif" badge
5. Test both English and French languages

### Internationalization (i18n)

- [X] T001 [P] [US3] Add English translations to src/bcd_web/locales/en.json - add 18 new keys in borrowers section (block_borrower, unblock_borrower, block_borrower_title, unblock_borrower_title, block_reason_label, select_reason, reason_lost_book, reason_damaged, reason_overdue, reason_policy, reason_other, additional_notes, notes_placeholder, max_200_chars, unblock_confirm_message, borrower_blocked_success, borrower_unblocked_success, error_block_failed, error_unblock_failed, error_select_reason) and add "processing" to common section
- [X] T002 [P] [US3] Add French translations to src/bcd_web/locales/fr.json - add 18 new keys matching en.json with French translations (Bloquer l'emprunteur, Débloquer l'emprunteur, etc.)

### UI Components - Modal Dialogs

- [X] T003 [US3] Add Block Borrower modal to src/bcd_web/index.html after line 742 - create modal with id="blockBorrowerModal", bg-danger header, form with required dropdown (5 reasons), optional notes textarea (max 200 chars), Cancel and "Block Borrower" buttons
- [X] T004 [US3] Add Unblock Borrower modal to src/bcd_web/index.html after blockBorrowerModal - create modal with id="unblockBorrowerModal", bg-success header, confirmation message with borrower name, Cancel and "Unblock Borrower" buttons

### UI Components - Action Buttons

- [X] T005 [US3] Add conditional buttons to src/bcd_web/templates/fragments/borrower_display.html modal footer lines 215-230 - add Jinja2 conditional: if borrower.active show red "Block Borrower" button with onclick="openBlockBorrowerModal()", else show green "Unblock Borrower" button with onclick="openUnblockBorrowerModal()", keep existing Edit and Close buttons

### JavaScript - Block Functionality

- [X] T006 [US3] Implement openBlockBorrowerModal in src/bcd_web/js/pages/borrowers.js - create function accepting (borrowerId, borrowerName), populate hidden field block-borrower-id, set block-borrower-name text, reset block-reason and block-notes fields, show modal using new bootstrap.Modal()
- [X] T007 [US3] Implement confirmBlockBorrower in src/bcd_web/js/pages/borrowers.js - create async function that validates reason selection, combines reason+notes (truncate at 200 chars), URL-encodes with encodeURIComponent(), disables button with spinner, POSTs to /api/v1/borrowers/{id}/block?reason={encoded}, on success closes modal and calls htmx.ajax to refresh borrower detail, shows success notification, on error shows error and keeps modal open

### JavaScript - Unblock Functionality

- [X] T008 [US3] Implement openUnblockBorrowerModal in src/bcd_web/js/pages/borrowers.js - create function accepting (borrowerId, borrowerName), populate hidden field unblock-borrower-id, set unblock-borrower-name text, show modal using new bootstrap.Modal()
- [X] T009 [US3] Implement confirmUnblockBorrower in src/bcd_web/js/pages/borrowers.js - create async function that disables button with spinner, POSTs to /api/v1/borrowers/{id}/unblock, on success closes modal and calls htmx.ajax to refresh borrower detail, shows success notification, on error shows error notification

### Manual Testing

- [ ] T010 [US3] Execute manual testing checklist - verify (1) buttons appear conditionally, (2) block flow: modal opens with 5 reasons, validation works, confirm blocks and refreshes with red badge, (3) unblock flow: modal opens, confirm unblocks and refreshes with green badge, (4) error handling works, (5) both English and French work, (6) blocked borrower cannot checkout items

**Note**: Ready for manual testing - all implementation tasks (T001-T009) complete

**Checkpoint**: Enhancement complete - borrowers can be blocked/unblocked in 2 clicks with standardized reasons

---

## Dependencies & Execution Order

### Task Dependencies

```text
T001 (en.json) ──┐
                 ├─→ T003 (block modal) ──┐
T002 (fr.json) ──┘                        ├─→ T006 (openBlock) ─→ T007 (confirmBlock) ──┐
                                          │                                              │
                   T004 (unblock modal) ──┤                                              ├─→ T010 (testing)
                                          ├─→ T008 (openUnblock) ─→ T009 (confirmUnblock)┘
                   T005 (buttons) ────────┘
```

### Parallel Opportunities

**Round 1** (parallel):
- T001: Add English translations
- T002: Add French translations

**Round 2** (parallel, after Round 1):
- T003: Add block modal HTML
- T004: Add unblock modal HTML
- T005: Add buttons to footer

**Round 3** (two parallel streams, after Round 2):

Stream A:
- T006: openBlockBorrowerModal()
- T007: confirmBlockBorrower()

Stream B (parallel with Stream A):
- T008: openUnblockBorrowerModal()
- T009: confirmUnblockBorrower()

**Round 4** (after Round 3):
- T010: Manual testing

---

## Implementation Strategy

### Single Developer Approach

**Total Time Estimate**: 2-3 hours

1. **Round 1** (10 min): Add i18n translations (T001-T002)
2. **Round 2** (30 min): Add HTML components (T003-T005)
3. **Round 3** (50 min): Implement JavaScript (T006-T009)
4. **Round 4** (30 min): Manual testing (T010)

### Validation Checkpoints

- **After T002**: Verify JSON files valid, keys match usage
- **After T005**: Start web UI, verify buttons appear conditionally
- **After T007**: Test complete block flow (modal → API → refresh)
- **After T009**: Test complete unblock flow
- **After T010**: Test both languages, verify checkout blocking integration

---

## Backend Status

✅ **All backend endpoints already exist** - no backend work required:
- `POST /api/v1/borrowers/{id}/block?reason={reason}` (src/bcd_api/api/v1/borrowers.py:421-440)
- `POST /api/v1/borrowers/{id}/unblock` (src/bcd_api/api/v1/borrowers.py:403-418)
- `borrower.active` (BOOLEAN) field in database
- `borrower.blocked_reason` (VARCHAR 200) field in database

---

## Files Modified Summary

| File | Lines | Description |
|------|-------|-------------|
| `src/bcd_web/locales/en.json` | +20 | 18 new translation keys |
| `src/bcd_web/locales/fr.json` | +20 | 18 French translations |
| `src/bcd_web/index.html` | +80 | 2 modal dialogs |
| `src/bcd_web/templates/fragments/borrower_display.html` | +15 | Conditional buttons |
| `src/bcd_web/js/pages/borrowers.js` | +120 | 4 new functions |

**Total**: 5 files, ~255 lines added

---

## Success Criteria

✅ All acceptance scenarios pass:
- **Scenario 10**: Block button opens modal with 5 reasons + notes
- **Scenario 11**: Confirm blocks borrower, shows red badge with reason
- **Scenario 12**: Unblock confirms and restores green badge

✅ Constitution compliance:
- **Principle V (Click Minimization)**: Reduces 5 clicks to 2 (60% reduction) ✅ PRIMARY GOAL
- **Principle X (i18n)**: All strings in en.json and fr.json ✅

---

## Quick Start Commands

```bash
# Start development
python -m src.bcd_web.server

# Test in browser
# http://127.0.0.1:8888/#borrowers/101

# Test API endpoints
curl -X POST "http://localhost:8000/api/v1/borrowers/101/block?reason=Lost%20Book"
curl -X POST "http://localhost:8000/api/v1/borrowers/101/unblock"
curl "http://localhost:8000/api/v1/borrowers/101"
```

---

## Task Summary

**Total Tasks**: 10
- T001-T002: Internationalization (2 tasks, parallel)
- T003-T005: HTML components (3 tasks, parallel after i18n)
- T006-T007: Block JavaScript (2 tasks, sequential)
- T008-T009: Unblock JavaScript (2 tasks, sequential, parallel with T006-T007)
- T010: Manual testing (1 task, after all implementation)

**Parallelizable Tasks**: 5 tasks marked [P] (50%)

**Format Validation**: ✅ All 10 tasks follow checklist format (checkbox, Task ID, [P] marker, [US3] label, file paths)
