# Feature Specification: Circulation History — Pagination and Performance

**Feature Branch**: `007-circulation-history`
**Created**: 2026-03-26
**Status**: Draft
**Input**: User description: "add a circulation history that will not overload the old library computer"

## Context

The system already records every checkout, return, and renewal in a `circulation_transaction` table. Two history views already exist:

- **Borrower history tab** (in the borrower detail modal) — truncated to the last 20 records, no pagination, no filtering
- **Item history tab** (in the item detail view) — truncated to the last 10 records, no pagination, no filtering

As the library accumulates years of data, these truncated views silently drop older records and any attempt to remove the hard limit would freeze the browser or slow down the server on old hardware. This feature makes both views complete and performant.

**Archive note**: A manual archive process exists that moves transactions older than 5 years to long-term storage. This feature only covers non-archived circulation records — archived records are out of scope.

## Clarifications

### Session 2026-03-26

- Q: What borrower information appears in the item history view? → A: Borrower full name only.
- Q: Must new UI elements (pagination controls, date filter labels, empty-state messages) support French and English? → A: Yes, all new user-facing text must be in both French and English.
- Q: Does the borrower history tab include currently active loans? → A: No — only returned or overdue-resolved transactions; active loans remain in the Current Loans tab.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse a Student's Full Borrowing History (Priority: P1)

A librarian opens a student's borrower record and navigates to the History tab to review their complete borrowing history — not just the most recent 20 loans. They page through older records without the screen freezing.

**Why this priority**: The most common history use case. A student's full history is needed for parent meetings, missing-book investigations, and reading tracking. The current 20-record cap silently hides older records, making the view untrustworthy.

**Independent Test**: Open the borrower detail modal for a student with more than 20 past loans, navigate to the History tab, and verify all records are reachable via page controls without browser freeze.

**Acceptance Scenarios**:

1. **Given** a borrower with 50 past loans, **When** the librarian opens their History tab, **Then** the first page shows the 20 most recent records and a page indicator shows how many pages of records exist.
2. **Given** the first page is displayed, **When** the librarian clicks to the next page, **Then** the next 20 records load without freezing the browser, and the previous-page control becomes active.
3. **Given** the last page is displayed, **When** the librarian tries to go further, **Then** the next-page control is disabled or absent.
4. **Given** a borrower with 5 past loans (fewer than one page), **When** the History tab opens, **Then** all 5 records appear and no pagination controls are shown.

---

### User Story 2 - Browse a Book's Full Borrowing History (Priority: P2)

A librarian selects a book to see every borrower who has ever had it — useful for tracking down a missing copy or understanding how popular a title is. The current 10-record cap makes this unreliable for books that have circulated for several years.

**Why this priority**: Less frequent than borrower lookups but equally affected by the truncation problem. Investigation of popular or missing books requires the full record.

**Independent Test**: Open the item detail view for a book with more than 10 past loans and verify all records are reachable via page navigation without a slow or frozen browser.

**Acceptance Scenarios**:

1. **Given** a book with 30 past loans, **When** the librarian opens its history view, **Then** the first page shows the 20 most recent records and pagination controls indicate more pages exist.
2. **Given** the history is displayed, **When** the librarian navigates to a subsequent page, **Then** the older records appear in under 2 seconds on old hardware.
3. **Given** a book that has never been borrowed, **When** its history view is opened, **Then** a clear message indicates no borrowing history exists, with no pagination controls.

---

### User Story 3 - Filter History by School Year (Priority: P3)

At the end of a school year, a librarian wants to review the borrowing activity for a given student or book during the current academic year only — without paging through years of older records.

**Why this priority**: Reduces the number of records fetched and displayed, directly helping performance on old hardware. It is also a practical need for year-end reporting.

**Independent Test**: Apply a start-date filter on a borrower or item history view and verify only matching records appear.

**Acceptance Scenarios**:

1. **Given** the borrower history tab is open, **When** the librarian sets a start date, **Then** only transactions checked out on or after that date are shown.
2. **Given** both a start and end date are set, **When** the filter is applied, **Then** only transactions within that period appear and the view resets to the first page.
3. **Given** a date range with no transactions, **When** the filter is applied, **Then** a clear message indicates no records were found for that period.
4. **Given** a date range filter is active, **When** the librarian clears the filter, **Then** the full paginated history reappears starting from the first page.

---

### Edge Cases

- What happens when a borrower has hundreds of records accumulated over many years? Only the records for the current page are fetched — the full set is never loaded at once into memory or the browser.
- What happens when a student or book is deleted from the system? Any remaining transactions in the active table that still reference the deleted record must continue to display with the information captured at checkout time (name, title, barcode).
- What happens when navigating pages quickly on a slow computer? Each navigation replaces the previous request — stacked or duplicate requests do not accumulate.
- What happens to records that have been moved to long-term archive (5+ years old)? They are not shown in these history views; only non-archived circulation records are displayed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The borrower history tab MUST display results in pages of 20 records, ordered by checkout date descending (most recent first).
- **FR-002**: The item history view MUST display results in pages of 20 records, ordered by checkout date descending.
- **FR-003**: Both history views MUST show pagination controls (previous page, next page, current page position) when the total record count exceeds one page.
- **FR-004**: Pagination controls MUST be hidden when all records fit on a single page.
- **FR-005**: Each page load MUST fetch only the records for that page from the data store — the complete history MUST NOT be loaded into memory at any point.
- **FR-006**: Both history views MUST provide a start date and end date filter (each independently optional) applied to the checkout date.
- **FR-007**: Applying or clearing a date range filter MUST reset the view to the first page of the resulting record set.
- **FR-008**: Each borrower history record MUST display: book title, checkout date, due date, return date, and status (returned on time / returned late). The borrower history tab shows only completed transactions; active loans are not included.
- **FR-008b**: Each item history record MUST display: borrower full name, checkout date, due date, return date (if returned), and status (on loan / returned on time / returned late / overdue). The item history view includes the currently active loan if one exists.
- **FR-009**: The system MUST retrieve each page of history efficiently — response time MUST NOT degrade proportionally as the total number of historical transactions grows.
- **FR-010**: History views MUST only display non-archived circulation records — records moved to long-term archive are not shown.
- **FR-011**: All new user-facing text introduced by this feature (pagination controls, date filter labels, empty-state messages) MUST be available in both French and English.

### Key Entities

- **Circulation Transaction**: A single loan event linking a borrower to an item, with checkout date, due date, return date, and status. The source data for all history views.
- **History Page**: A bounded, ordered slice of transactions for one borrower or one item, defined by page number, page size (20), and optional date range filter.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The first page of any borrower's history loads in under 2 seconds on a computer 5 or more years old, regardless of how many total transactions that borrower has in the active table.
- **SC-002**: Navigating to any subsequent page of history takes under 2 seconds on the same hardware.
- **SC-003**: Applying a date range filter and loading the first page of filtered results takes under 2 seconds on old hardware.
- **SC-004**: A borrower or item with 200+ active transactions can be fully browsed page by page — no records are silently dropped or inaccessible.
- **SC-005**: The browser remains responsive (no visible freeze or hang) while navigating between pages on old hardware.
- **SC-006**: Performance targets in SC-001 and SC-002 continue to hold when the library has accumulated 10,000 or more total circulation transactions — load time does not degrade as historical data grows.

## Assumptions

- Page size of 20 records is used for both borrower and item history, consistent with the current borrower history default.
- The date range filter applies to `checkout_date` as the anchor — not return date.
- The existing borrower history and item history endpoints will be extended to support pagination and date filtering rather than introducing new endpoints.
- The existing History tab in the borrower detail modal and the existing item detail history view are the only two surfaces modified — no new navigation items are added.
- "Old computer" is a machine 5 or more years old with limited RAM and a slow processor, consistent with the project's existing legacy hardware performance target.
- Export or print of history is out of scope for this feature.
