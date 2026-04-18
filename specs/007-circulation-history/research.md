# Research: Circulation History — Pagination and Performance

**Feature**: 007-circulation-history
**Date**: 2026-03-26

---

## Decision 1: Pagination approach (offset vs cursor)

**Decision**: Offset-based pagination (`page`, `page_size`)

**Rationale**: The existing `Pagination.js` component uses `currentPage`/`totalPages` which maps directly to offset-based pagination. Cursor-based pagination would require a rewrite of the existing component and adds complexity with no benefit at the expected data volumes (a student averaging 5 books/year for 5 years = 25 records; a popular book for 5 years ≈ 50–100 records). Offset-based pagination is simpler to implement, test, and understand, and performs well within the data volumes expected from a single elementary school library.

**Alternatives considered**:
- Cursor-based (keyset) pagination: better for infinite scroll and very large datasets, but overkill here and incompatible with the existing Pagination.js component's page-number UI.

---

## Decision 2: Sort order for history records

**Decision**: `checkout_date DESC` (most recent checkout first)

**Rationale**: The spec requires "most recent first." Using `checkout_date` rather than `return_date` is more meaningful to the librarian — a book checked out in January and returned in February belongs to January in the mental model. Also allows the date range filter to be applied consistently against the same field used for sorting. The current service implementation sorts by `return_date DESC`; this will be corrected.

**Alternatives considered**:
- `return_date DESC`: used in current implementation, but semantically less correct and cannot apply consistently when `return_date` is NULL (active loans in item history).

---

## Decision 3: Where borrower history is loaded in the UI

**Decision**: BorrowerDetail history tab will call the dedicated `GET /api/v1/circulation/borrower/{id}/history` endpoint directly, with pagination and date filter parameters.

**Rationale**: Currently the history tab loads from the borrower detail endpoint (`GET /api/v1/borrowers/{id}?detail=true`), which embeds a hardcoded 20-record slice in the full borrower response. Pagination requires calling the history endpoint on each page change — this cannot be done through the borrower detail endpoint without reloading the entire borrower record. Calling the dedicated history endpoint is cleaner, avoids unnecessary data transfer, and follows the single-responsibility principle.

**Alternatives considered**:
- Adding pagination params to the borrower detail endpoint: would pollute the borrower endpoint with concerns that belong to circulation history; also requires loading all borrower data on each history page navigation.

---

## Decision 4: Database index for `return_date`

**Decision**: Add `index=True` to the `return_date` column on `CirculationTransaction` via an Alembic migration.

**Rationale**: Every history query filters on `return_date IS NOT NULL` to exclude active loans from the completed-transaction history. Without an index on `return_date`, this condition causes a full table scan as the transaction count grows — exactly the performance failure the feature is designed to prevent. A database index on `return_date` makes this filter use an index seek instead.

**Note**: `checkout_date`, `borrower_id`, and `item_id` already have `index=True` in the model. Only `return_date` is missing.

**Alternatives considered**:
- Composite index on `(borrower_id, checkout_date)` and `(item_id, checkout_date)`: would be even faster for the specific queries used, but adds more complexity. Adding the single-column `return_date` index is sufficient for the expected scale and follows the existing pattern.

---

## Decision 5: Total count strategy

**Decision**: Include total count in every paginated history response; do not make it optional.

**Rationale**: The `Pagination.js` component requires `totalItems` to render "Page X of Y" and to disable the Next button on the last page. At the scale of a single school's library (one borrower having at most a few hundred transactions over 5 years), the `COUNT(*)` query with `WHERE borrower_id = ?` (using the existing index on `borrower_id`) is fast and adds negligible overhead. The constitution's guidance to make count queries optional is targeted at very large datasets (millions of rows) where `COUNT(*)` is expensive.

**Alternatives considered**:
- Skip count and hide total pages: would make pagination controls show only "Next" / "Previous" without "Page X of Y", which is a worse UX with no meaningful performance gain at this scale.

---

## Decision 6: Item history tab implementation

**Decision**: Implement the stub item history tab in `RecordDetail.js` to call `GET /api/v1/circulation/item/{item_id}/history` with pagination and date filter parameters. Show the active loan (if any) in a highlighted banner above the paginated history table.

**Rationale**: The item history endpoint and service already exist but are never called from the web UI (the history tab in RecordDetail is a placeholder stub). This feature activates the existing server-side capability by implementing the client side.

---

## Decision 7: New i18n keys needed

**Keys to add** in both `en.json` and `fr.json` under the `circulation` section:

| Key | English | French |
|-----|---------|--------|
| `circulation.date_from` | "From" | "Du" |
| `circulation.date_to` | "To" | "Au" |
| `circulation.apply_date_filter` | "Apply" | "Appliquer" |
| `circulation.clear_date_filter` | "Clear" | "Effacer" |
| `circulation.no_history_for_period` | "No history found for this period." | "Aucun historique trouvé pour cette période." |
| `circulation.currently_on_loan_to` | "Currently on loan to {name}" | "Actuellement emprunté par {name}" |
| `circulation.history_returned_on_time` | "On time" | "À temps" |
| `circulation.history_returned_late` | "Late" | "En retard" |

**Existing keys that can be reused** (no new keys needed):
- Pagination controls: `common.previous`, `common.next`, `common.page`, `pagination.showing`, `pagination.of`, `pagination.items`
- Empty state (no history): `circulation.no_history`

---

## Existing Infrastructure Reused

| Component | Location | Status |
|-----------|----------|--------|
| `Pagination.js` | `src/bcd_web_vue/js/components/ui/Pagination.js` | ✅ Fully functional, reused as-is |
| Borrower history service | `circulation_service.get_borrower_circulation_history()` | ✅ Exists, needs new params |
| Item history service | `circulation_service.get_item_circulation_history()` | ✅ Exists, needs new params |
| Borrower history API endpoint | `GET /api/v1/circulation/borrower/{id}/history` | ✅ Exists, needs new query params |
| Item history API endpoint | `GET /api/v1/circulation/item/{id}/history` | ✅ Exists, needs new query params |
| `checkout_date` index | `CirculationTransaction.checkout_date` | ✅ Already indexed |
| `borrower_id` index | `CirculationTransaction.borrower_id` | ✅ Already indexed |
| `item_id` index | `CirculationTransaction.item_id` | ✅ Already indexed |
| `return_date` index | `CirculationTransaction.return_date` | ❌ Missing — migration needed |
