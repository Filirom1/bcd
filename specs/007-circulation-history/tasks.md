# Tasks: Circulation History — Pagination and Performance

**Input**: Design documents from `/specs/007-circulation-history/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks grouped by user story — each phase is independently deliverable and testable.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no conflict)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Database Foundation)

**Purpose**: Add the missing `return_date` index. This is the only infrastructure change required and blocks all user story work.

**⚠️ CRITICAL**: Must complete before any user story begins — without this index, paginated queries cause full table scans that defeat the performance goal.

- [X] T001 Add `index=True` to `return_date` column in `src/bcd_api/models/circulation.py` (change `nullable=True` line to include `index=True`)
- [X] T002 Create Alembic migration for `return_date` index: run `alembic revision --autogenerate -m "add return_date index to circulation_transaction"` and verify the generated file in `migrations/versions/` adds `ix_circulation_transaction_return_date`; confirm down migration drops the index
- [X] T003 Apply migration: run `alembic upgrade head` and confirm success

**Checkpoint**: `return_date` is now indexed. All subsequent queries filtering on `return_date IS NOT NULL` use an index seek.

---

## Phase 2: Foundational (Shared Schema)

**Purpose**: `PaginationMeta` is used by both US1 and US2 response schemas. Must exist before either user story's schemas are defined.

**⚠️ CRITICAL**: Blocks US1 and US2 implementation.

- [X] T004 Add `PaginationMeta` Pydantic schema to `src/bcd_api/schemas/circulation.py` with fields: `page: int`, `page_size: int`, `total_items: int`, `total_pages: int`

**Checkpoint**: `PaginationMeta` is importable. US1 and US2 can now proceed independently.

---

## Phase 3: User Story 1 — Browse a Student's Full Borrowing History (Priority: P1) 🎯 MVP

**Goal**: Librarian can open a borrower's History tab and page through their complete completed loan history (20 per page), replacing the current silent 20-record truncation.

**Independent Test**: Load a borrower with 25+ past loans → open History tab → verify page 1 shows exactly 20 records with a "Next" control → click Next → verify 5+ records appear on page 2 → no browser freeze.

### Tests for User Story 1

> **Write these tests FIRST — they must FAIL before T007 is implemented**

- [X] T005 [US1] Write integration tests for borrower history pagination in `tests/integration/test_circulation_history_pagination.py` using `db_session` fixture and AAA pattern — cover: `test_borrower_history_returns_first_page` (25 records → 20 on page 1), `test_borrower_history_returns_correct_second_page` (page 2 has remaining 5), `test_borrower_history_excludes_active_loans` (active loan absent from history), `test_borrower_history_sorted_checkout_date_desc` (most recent checkout first), `test_borrower_history_pagination_meta_correct` (total_items=25, total_pages=2), `test_borrower_history_single_page_no_pagination` (5 records → total_pages=1)

### Implementation for User Story 1

- [X] T006 [US1] Add `BorrowerHistoryItem` and `BorrowerHistoryResponse` Pydantic schemas to `src/bcd_api/schemas/circulation.py` per data-model.md section "New API Response Schemas" (`BorrowerHistoryItem` fields: `item_id`, `bibliographic_record_id`, `title`, `checkout_date`, `due_date`, `return_date`, `was_overdue`; `BorrowerHistoryResponse` fields: `borrower_id`, `borrower_name`, `history`, `pagination`)
- [X] T007 [US1] Extend `get_borrower_circulation_history()` in `src/bcd_api/services/circulation_service.py`: add `page: int = 1` and `page_size: int = 20` parameters; filter `return_date IS NOT NULL`; count filtered records for `total_items`; apply `.order_by(CirculationTransaction.checkout_date.desc()).offset((page-1)*page_size).limit(page_size)`; return `BorrowerHistoryResponse` with `PaginationMeta`; remove embedded `current_loans` from this response (T005 tests must pass)
- [X] T008 [US1] Update `GET /borrower/{borrower_id}/history` endpoint in `src/bcd_api/api/v1/circulation.py`: add `page: int = Query(1, ge=1)` and `page_size: int = Query(20, ge=1, le=50)` query parameters; update `response_model=BorrowerHistoryResponse`; pass new params to service
- [X] T009 [US1] Update History tab in `src/bcd_web_vue/js/components/borrowers/BorrowerDetail.js`: remove loading of `circulationHistory` from the borrower detail endpoint response; add reactive state (`historyPage`, `historyPagination`, `historyItems`, `historyLoading`); lazy-load on first History tab click via `GET /api/v1/circulation/borrower/{id}/history?page=1&page_size=20`; wire `Pagination.js` `page-change` event to reload with new page number; show empty state using existing `circulation.no_history` key when `history` is empty

**Checkpoint**: US1 fully functional. Borrower History tab paginates. Tests pass. No browser freeze on 50+ record history.

---

## Phase 4: User Story 2 — Browse a Book's Full Borrowing History (Priority: P2)

**Goal**: Librarian can open a catalog record's History tab and see every borrower who has ever had the book, paginated (20 per page), with the current active loan shown separately at the top. Replaces the stub placeholder.

**Independent Test**: Load a book with 25+ past loans → open History tab → verify active loan appears in banner (if any), page 1 shows 20 completed loans with "Next" control → click Next → older records appear → no freeze.

### Tests for User Story 2

> **Write these tests FIRST — they must FAIL before T012 is implemented**

- [X] T010 [US2] Extend `tests/integration/test_circulation_history_pagination.py` with item history tests: `test_item_history_first_page` (25 completed loans → 20 on page 1), `test_item_history_shows_current_loan` (active loan in `current_loan`, absent from `history`), `test_item_history_empty_never_borrowed` (`current_loan=null`, `history=[]`, `total_items=0`), `test_item_history_sorted_checkout_date_desc` (most recent completed first), `test_item_history_pagination_meta_correct` (total_pages ceiling: 21 records → 2 pages)

### Implementation for User Story 2

- [X] T011 [US2] Add `ItemHistoryItem` and `ItemHistoryResponse` Pydantic schemas to `src/bcd_api/schemas/circulation.py` per data-model.md (`ItemHistoryItem` fields: `borrower_name`, `checkout_date`, `due_date`, `return_date` optional, `was_overdue`, `status`; `ItemHistoryResponse` fields: `item_id`, `title`, `current_loan` optional, `history`, `pagination`)
- [X] T012 [US2] Extend `get_item_circulation_history()` in `src/bcd_api/services/circulation_service.py`: add `page: int = 1` and `page_size: int = 20` parameters; fetch `current_loan` separately (`return_date IS NULL`, not paginated); query completed transactions (`return_date IS NOT NULL`); count for `total_items`; apply `checkout_date DESC` ordering with offset/limit; return `ItemHistoryResponse` with `PaginationMeta` (T010 tests must pass)
- [X] T013 [US2] Update `GET /item/{item_id}/history` endpoint in `src/bcd_api/api/v1/circulation.py`: add `page: int = Query(1, ge=1)` and `page_size: int = Query(20, ge=1, le=50)`; update `response_model=ItemHistoryResponse`; pass new params to service
- [X] T014 [US2] Implement History tab in `src/bcd_web_vue/js/components/catalog/RecordDetail.js`: replace the stub alert with full implementation; add reactive state (`itemHistoryPage`, `itemHistoryPagination`, `itemHistoryItems`, `itemCurrentLoan`, `itemHistoryLoading`); lazy-load on History tab activation via `GET /api/v1/circulation/item/{item_id}/history?page=1&page_size=20`; show `current_loan` as Bootstrap `alert-info` using `circulation.currently_on_loan_to` key; render paginated table (columns: Borrower, Checkout, Return, Status) with status badges using existing Bootstrap badge classes; wire `Pagination.js` for page navigation; show empty state with `circulation.no_history` key

**Checkpoint**: US2 fully functional. Item History tab no longer a stub. Tests pass. Pagination works.

---

## Phase 5: User Story 3 — Filter History by School Year (Priority: P3)

**Goal**: Librarian can set a date range (start and/or end date) on either history tab to narrow results to a specific school year, with the view resetting to page 1 on filter apply/clear.

**Independent Test**: Open borrower with multi-year history → enter `date_from=2024-09-01` → click Apply → verify only records from that date forward appear → click Clear → verify full history returns → confirm French labels appear when language is set to French.

### Tests for User Story 3

> **Write these tests FIRST — they must FAIL before T016 is implemented**

- [X] T015 [US3] Extend `tests/integration/test_circulation_history_pagination.py` with date filter tests: `test_borrower_history_date_from_filter` (only records on/after date_from), `test_borrower_history_date_to_filter` (only records on/before date_to), `test_borrower_history_date_range_filter` (both bounds applied), `test_borrower_history_empty_for_period` (no records in range → total_items=0), `test_item_history_date_filter` (date filter applies only to completed transactions, not current_loan)

### Implementation for User Story 3

- [X] T016 [US3] Add `date_from: Optional[date] = None` and `date_to: Optional[date] = None` parameters to both `get_borrower_circulation_history()` and `get_item_circulation_history()` in `src/bcd_api/services/circulation_service.py`; apply filters on `CirculationTransaction.checkout_date` when provided (date_from → `>= date_from`, date_to → `<= date_to`); filters apply before `COUNT(*)` and before pagination (T015 tests must pass)
- [X] T017 [US3] Add `date_from: Optional[date] = Query(None)` and `date_to: Optional[date] = Query(None)` to both history endpoints in `src/bcd_api/api/v1/circulation.py`; pass through to service calls
- [X] T018 [P] [US3] Add date filter inputs to History tab in `src/bcd_web_vue/js/components/borrowers/BorrowerDetail.js`: add `historyDateFrom` and `historyDateTo` reactive refs; render two date `<input type="date">` fields using `circulation.date_from` and `circulation.date_to` i18n keys; add Apply button (`circulation.apply_date_filter`) that resets `historyPage` to 1 and reloads; add Clear button (`circulation.clear_date_filter`) that clears both dates, resets page to 1, and reloads; show `circulation.no_history_for_period` empty state when filter active and no results
- [X] T019 [P] [US3] Add date filter inputs to History tab in `src/bcd_web_vue/js/components/catalog/RecordDetail.js` with identical behaviour as T018: `itemHistoryDateFrom`, `itemHistoryDateTo` refs; Apply/Clear buttons; `circulation.no_history_for_period` empty state; filter does not affect `current_loan` display
- [X] T020 [P] [US3] Add 10 new keys to `src/bcd_web_vue/locales/en.json` under `circulation`: `date_from`, `date_to`, `apply_date_filter`, `clear_date_filter`, `no_history_for_period`, `currently_on_loan_to`, `history_returned_on_time`, `history_returned_late`, `history_on_loan` ("On loan"), `history_overdue` ("Overdue") (base 8 values per plan.md section 1.6; last 2 cover item history active-loan and overdue statuses)
- [X] T021 [P] [US3] Add 10 matching French keys to `src/bcd_web_vue/locales/fr.json` under `circulation` (values per plan.md section 1.6 for base 8; add `history_on_loan` → "En cours d'emprunt", `history_overdue` → "En retard"); confirm key structure is identical to en.json

**Note**: T018 and T019 are parallelizable (different files). T020 and T021 are parallelizable (different files). T016 must complete before T017, T018, T019.

**Checkpoint**: US3 fully functional. Date filters work on both history tabs in both languages.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification and quality gate.

- [X] T022 Run full test suite `pytest tests/integration/test_circulation_history_pagination.py -v` and confirm all 16 tests pass; run `pytest --cov=src/bcd_api/services/circulation_service --cov-report=term-missing` and confirm ≥80% coverage on modified service functions
- [X] T023 Verify i18n key parity: confirm `en.json` and `fr.json` have identical key sets under `circulation` for all 10 new keys; verify `circulation.no_history` already exists in both files (referenced by T009 and T014 as an existing key) — if absent, add it to T020/T021 before marking those tasks complete; verify no hard-coded strings remain in `BorrowerDetail.js` or `RecordDetail.js` history tab sections
- [ ] T024 End-to-end validation using `quickstart.md`: start server, run simulation data (`python reset_and_simulate.py`), verify all curl examples return valid paginated JSON, open browser and confirm borrower History tab paginates, item History tab shows content (not placeholder), and date filter narrows results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 complete (migration applied)
- **Phase 3 (US1)**: Depends on Phase 2 — can start after `PaginationMeta` exists
- **Phase 4 (US2)**: Depends on Phase 2 — can start after `PaginationMeta` exists; independent of US1
- **Phase 5 (US3)**: Depends on Phase 3 AND Phase 4 — both service functions must exist before adding date filter params to them
- **Phase 6 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Unblocked after Phase 2 — no dependency on US2 or US3
- **US2 (P2)**: Unblocked after Phase 2 — no dependency on US1 or US3
- **US3 (P3)**: Depends on US1 + US2 (extends both service functions in place)

### Within Each User Story

- Tests (T005, T010, T015) MUST be written and confirmed FAILING before service implementation
- Schemas before services (T006 → T007, T011 → T012)
- Services before endpoints (T007 → T008, T012 → T013)
- Endpoints before UI (T008 → T009, T013 → T014)

### Parallel Opportunities

- T001, T004 can run in parallel (different files)
- US1 (Phase 3) and US2 (Phase 4) can run in parallel once Phase 2 is done
- Within US3: T018, T019, T020, T021 can all run in parallel (all different files)

---

## Parallel Example: US1 + US2 (after Phase 2 complete)

```
Thread A (US1):                          Thread B (US2):
T005 - Write borrower tests              T010 - Write item tests
T006 - Add borrower schemas              T011 - Add item schemas
T007 - Extend borrower service           T012 - Extend item service
T008 - Update borrower endpoint          T013 - Update item endpoint
T009 - Update BorrowerDetail.js          T014 - Implement RecordDetail.js
```

Both threads merge at Phase 5 (US3).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Apply migration
2. Complete Phase 2: Add PaginationMeta schema
3. Complete Phase 3: US1 (borrower history pagination)
4. **STOP and VALIDATE**: History tab paginates for borrowers → no truncation → no freeze
5. Ship US1 as immediate fix for the most common use case

### Incremental Delivery

1. Phase 1 + Phase 2 → foundation ready
2. Phase 3 (US1) → borrower history works → **demo / deploy**
3. Phase 4 (US2) → item history works → **demo / deploy**
4. Phase 5 (US3) → date filtering works on both → **demo / deploy**
5. Phase 6 → quality gate

### Full Parallel Strategy

With two developers after Phase 2:
- Developer A: US1 (Phase 3)
- Developer B: US2 (Phase 4)
- Both: US3 (Phase 5) — service changes in same file, coordinate on T016 first

---

## Notes

- [P] tasks touch different files and have no incomplete shared dependencies
- Each user story phase is independently testable — stop at any checkpoint to validate
- Test tasks always precede the service implementation they cover (TDD order)
- US3 is the only phase with cross-file coordination needed (T016 touches `circulation_service.py` which US1 and US2 already modified — complete US3 after both)
- The borrower detail endpoint (`GET /api/v1/borrowers/{id}?detail=true`) still returns `circulation_history` embedded for backward compatibility; BorrowerDetail.js simply stops reading that field and calls the dedicated endpoint instead
