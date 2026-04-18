# Feature Specification: Collection Inventory Page

**Feature Branch**: `008-inventory-page`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "Collection inventory page with barcode scanning, file import, search with rotation filter, bulk edit and delete, and CSV export"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Barcode Scanning Inventory (Priority: P1)

A librarian conducts a physical inventory of the collection by scanning item barcodes one by one with a barcode scanner. As each item is scanned, it appears in a working list and is marked as physically verified with today's date. The scanner input remains active at all times, so the librarian never needs to click before scanning the next item.

**Why this priority**: This is the core workflow that justifies the feature — establishing physical proof of presence for each item. Without scanning, no meaningful inventory session can be conducted.

**Independent Test**: Can be fully tested by scanning several barcodes in sequence and verifying that items appear in the working table with their inventory date updated, including edge cases: unknown barcodes, duplicate scans, and scanning while a different tab is visible.

**Acceptance Scenarios**:

1. **Given** the inventory page is open, **When** a valid barcode is scanned, **Then** the item appears in the working table with its barcode, title, and status, and its inventory date is updated to today.
2. **Given** an item is already in the working table, **When** the same barcode is scanned again, **Then** the item's row is highlighted and moves to the top — no duplicate is created.
3. **Given** the inventory page is open, **When** an unknown barcode is scanned, **Then** an error notification is shown and the table is unchanged.
4. **Given** the user has switched to another tab (File or Search), **When** a barcode is scanned, **Then** the scan is captured and the item is added to the working table without requiring the user to click the input field first.

---

### User Story 2 - Search-Based Item Discovery (Priority: P2)

A librarian wants to find items meeting specific criteria — such as never having been inventoried, rarely borrowed, or belonging to a particular category or location — and add them to the working table for batch processing. The search combines item-level filters (condition, status, location) with record-level filters (genre, reading level, publication year) and inventory-specific filters (last verified date, loan frequency over a period).

**Why this priority**: Many inventory tasks target specific subsets (e.g., "all items in Room B never inventoried" or "all items borrowed fewer than twice in three years"). Search enables targeted workflows that barcode scanning alone cannot support.

**Independent Test**: Can be fully tested by applying various filter combinations, selecting results, and adding them to the working table — verifying inventory dates are updated and items already in the table are not duplicated.

**Acceptance Scenarios**:

1. **Given** no filters are applied, **When** the search runs, **Then** all items in the collection are returned.
2. **Given** the "never inventoried" filter is selected, **When** the search runs, **Then** only items that have never had a physical inventory check are shown.
3. **Given** the "low rotation" filter is set to "fewer than 2 loans since 01/04/2022", **When** the search runs, **Then** only items with 0 or 1 loans in that period are shown, with each item's loan count displayed.
4. **Given** items are selected from search results, **When** "Add selection" is clicked, **Then** selected items are added to the working table, their inventory dates are updated, and the view switches to the working table; items already present in the table are silently ignored.
5. **Given** the rotation filter's start date falls before the archive cutoff date, **When** the search runs, **Then** a warning is displayed informing the user that older loan records may be missing from the count.
6. **Given** a search returns more than 200 matching items, **When** results are displayed, **Then** exactly 200 items are shown with a message such as "More than 200 results — refine your filters to narrow down." No pagination controls appear.

---

### User Story 3 - Bulk Edit of Items and Records (Priority: P3)

A librarian selects items in the working table and applies the same changes to all of them at once: updating physical condition, borrowing status, borrowability, shelf location, or classification metadata (category, genre, reading level, target audience). Changes to bibliographic records are applied once per unique title, not once per copy.

**Why this priority**: During an inventory, librarians typically identify whole groups of items needing the same action (e.g., marking a shelf of damaged books, reclassifying a section). Editing items individually would be prohibitively slow.

**Independent Test**: Can be fully tested by selecting items with shared and distinct titles, applying a set of changes, and verifying that items are updated correctly and that each unique title's record is updated exactly once.

**Acceptance Scenarios**:

1. **Given** 42 items are selected, **When** the librarian sets condition to "damaged" and clicks Apply, **Then** a confirmation modal shows the number of items and affected titles before any change is made.
2. **Given** 3 of the 42 selected items are currently on loan, **When** a status change is applied, **Then** the confirmation modal warns that those 3 items will not have their status changed; after confirmation, 39 items are updated.
3. **Given** 42 selected items share 7 unique titles that collectively have 15 other copies not in the working table, **When** a category change is applied, **Then** the confirmation modal warns "Note: these 7 records have 15 other copies outside your selection that will also be updated", and after confirmation exactly 7 bibliographic records are updated.
4. **Given** a field is left at "unchanged", **When** the batch is applied, **Then** that field is not modified on any item or record.
5. **Given** items with an active hold reservation are selected for a status change, **When** Apply is confirmed, **Then** those items are updated and the confirmation modal included a warning about the active holds.

---

### User Story 4 - File Import of Inventory IDs (Priority: P4)

A librarian has a list of item IDs in a text file (e.g., exported from a handheld scanner) and wants to import it in bulk to mark all those items as inventoried and populate the working table.

**Why this priority**: Some schools use handheld scanners that produce text file exports rather than direct USB input. File import supports this common real-world workflow.

**Independent Test**: Can be fully tested by importing a valid file, a file with some unknown IDs, and a file with only unknown IDs — verifying table state, error reporting, and inventory date updates in each case.

**Acceptance Scenarios**:

1. **Given** a valid text file with 120 item IDs (one per line), **When** the file is selected, **Then** the file is parsed immediately showing "120 IDs found", and an Import button becomes available.
2. **Given** a file where 3 IDs are unknown, **When** parsed, **Then** the interface shows "117 valid, 3 unknown" with an option to view the unknown IDs; the Import button is available for the 117 valid ones.
3. **Given** a file where all IDs are unknown, **When** parsed, **Then** the Import button is disabled.
4. **Given** a valid import is confirmed, **When** import completes, **Then** all valid items appear in the working table with inventory dates updated; items already in the table are not duplicated.

---

### User Story 5 - Bulk Deaccessioning and Deletion (Priority: P5)

A librarian selects items in the working table to remove from the collection — either by marking them as "weeded" (withdrawn from circulation) or by permanently deleting them from the system.

**Why this priority**: Deaccessioning is a core outcome of an inventory session. Librarians need to efficiently process items identified as unfit for continued circulation.

**Independent Test**: Can be fully tested by selecting items including some currently on loan, attempting deletion, and verifying that on-loan items are excluded, the remaining items are deleted, and the table reflects the changes accurately.

**Acceptance Scenarios**:

1. **Given** 42 items are selected for deletion, **When** Delete is clicked, **Then** a confirmation modal warns the action is irreversible and states the exact count to be deleted.
2. **Given** 3 of the 42 selected items are on loan, **When** deletion is confirmed, **Then** the modal has warned about those 3, and after confirmation 39 items are deleted while the 3 on-loan items remain.
3. **Given** a selected item has an active hold reservation, **When** it is deleted, **Then** the hold reservation is also cancelled.
4. **Given** no items are selected, **When** Delete is clicked, **Then** the action has no effect.

---

### User Story 6 - Working Table Management and Export (Priority: P6)

A librarian manages the working table during an inventory session: selecting items using checkboxes or range selection, clearing unwanted entries, and exporting the full list to a spreadsheet for reporting or record-keeping.

**Why this priority**: The working table is the central workspace of the inventory page; being able to manage its contents and produce a formal record is essential for completing a documented inventory.

**Independent Test**: Can be fully tested by populating the table, using header checkbox and shift-click selection, clearing with and without a prior selection, and verifying CSV contents match the full table.

**Acceptance Scenarios**:

1. **Given** the working table has items, **When** the CSV export button is clicked, **Then** a file is downloaded containing all rows with columns: barcode, title, author, call number, location, status, condition, last loan date, last inventory date.
2. **Given** 42 of 347 items are checked, **When** Clear is clicked, **Then** a confirmation asks "Clear the 42 selected items?"; on confirm, only those 42 are removed.
3. **Given** no items are checked, **When** Clear is clicked, **Then** a confirmation asks "Clear all 347 items?"; on confirm, the table is emptied (previously set inventory dates are not reverted).
4. **Given** items in the table, **When** shift-click is used between two rows, **Then** all rows between them inclusive are selected.

---

### User Story 7 - Orphan Record Cleanup (Priority: P7)

An administrator removes bibliographic records (titles) that have no remaining physical copies in the system, keeping the catalog tidy after bulk deletions.

**Why this priority**: After bulk deletions, orphan records clutter the catalog and search results. This cleanup operation is infrequent but necessary for catalog hygiene.

**Independent Test**: Can be fully tested by creating an orphan record scenario, triggering cleanup from the admin menu, and verifying the record is removed without affecting other records.

**Acceptance Scenarios**:

1. **Given** the admin menu is opened, **When** "Delete records with no copies" is selected, **Then** the system fetches the current orphan count and presents a confirmation modal showing that count.
2. **Given** no orphan records exist, **When** the menu action is triggered, **Then** a modal informs the user there is nothing to delete.
3. **Given** the confirmation modal shows 12 orphan records, **When** the user confirms, **Then** all 12 records are permanently deleted.

---

### Edge Cases

- What happens if the same ID appears multiple times in an imported file? Duplicates are deduplicated silently; each item appears once in the working table.
- What happens if a barcode has a school-specific prefix? The prefix is stripped automatically using the same logic applied throughout the application.
- What happens if blank lines or comment lines (`#`) appear in the imported file? They are silently ignored.
- What happens if "Apply" fails for some items? The operation is atomic — either all changes succeed or none are applied.
- What happens if the working table contains thousands of items? The table remains usable with standard scrolling; selection and export continue to work on the full set.
- What happens if the user clears the working table — are inventory dates reverted? No. Inventory dates written to items are permanent; clearing the table only removes items from the session view.

## Requirements *(mandatory)*

### Functional Requirements

**Inventory Date Tracking**

- **FR-001**: The system MUST record a "last inventoried" date on each item when it is added to the working table via scanning, file import, or search selection.
- **FR-002**: The "last inventoried" date MUST be distinct from the item's last loan date and last modification date, representing physical presence verification exclusively.
- **FR-003**: Items that have never been inventoried MUST be identifiable as such (distinguishable from items inventoried at least once).

**Barcode Scanning**

- **FR-004**: The barcode input field MUST maintain keyboard focus at all times on the inventory page, regardless of which tab is active, so the librarian can scan without clicking.
- **FR-005**: When a valid barcode is scanned, the corresponding item MUST be added to the working table and its inventory date updated immediately.
- **FR-006**: If a scanned barcode is already in the working table, the system MUST highlight that row and move it to the top — no duplicate is added.
- **FR-007**: If a scanned barcode does not correspond to any known item, the system MUST show an error notification and leave the table unchanged.

**File Import**

- **FR-008**: The system MUST accept plain text files with one item ID per line; blank lines and lines beginning with `#` are ignored.
- **FR-009**: The file MUST be parsed as soon as it is selected, without requiring a separate action.
- **FR-010**: Unknown IDs found in the file MUST be listed and viewable before the import is confirmed.
- **FR-011**: The Import action MUST be disabled when no valid IDs are found in the file.
- **FR-012**: Items added via file import MUST arrive in the working table as unselected.

**Search and Discovery**

- **FR-013**: The search MUST support filtering items by: free text (title, author, ISBN, call number), status, condition, and shelf location.
- **FR-014**: The search MUST support filtering items by their inventory history: never inventoried, or not inventoried since a given date.
- **FR-015**: The search MUST support filtering items by bibliographic record attributes: medium type, target audience, category, genre, reading level, and publication year range.
- **FR-016**: The search MUST support a "low rotation" filter: items loaned fewer than N times since a specified date.
- **FR-017**: When the low rotation filter is active, each search result MUST display the loan count for the selected period.
- **FR-018**: When the rotation filter's start date precedes the archive cutoff date, the system MUST display a warning that historical loan records may be incomplete.
- **FR-019**: Items selected from search results MUST be added to the working table without duplicating items already present.
- **FR-019b**: Search results MUST be displayed as a scrollable list capped at 200 items. When the cap is reached, the system MUST display a message indicating that not all results are shown and prompting the user to refine their filters. No pagination controls are shown.

**Working Table**

- **FR-020**: The working table MUST display for each item: a sequential number, barcode, truncated title, and condition.
- **FR-021**: The table header MUST include a checkbox that cycles through: select all, deselect all, and indeterminate states.
- **FR-022**: The table MUST support shift-click range selection.
- **FR-023**: The "Clear" action MUST remove only the selected items when a selection exists, or all items when no selection exists, with an explicit confirmation prompt in both cases.
- **FR-024**: Clearing the table MUST NOT revert previously written inventory dates.
- **FR-024b**: The working table contents MUST be persisted in browser storage so that an accidental page refresh or tab close does not lose the session; the table is restored automatically when the page is reopened on the same device.

**Bulk Editing**

- **FR-025**: The system MUST allow batch update of the following item fields across all selected items: physical condition, borrowing status, borrowability flag, and shelf location.
- **FR-026**: The system MUST allow batch update of the following bibliographic record fields for the titles associated with selected items: category, genre, reading level, and target audience.
- **FR-027**: When bulk edits are applied, each bibliographic record MUST be updated exactly once regardless of how many copies of that title are selected.
- **FR-028**: Fields set to "unchanged" MUST be excluded from the update payload; only explicitly changed fields are applied.
- **FR-029**: Items currently on loan MUST be excluded from status changes during bulk edit; the count of excluded items MUST be shown in the confirmation modal before the user confirms.
- **FR-030**: The bulk edit operation MUST be atomic: all changes succeed together or none are applied.
- **FR-031**: A confirmation modal MUST be displayed before any bulk edit is applied, showing: the number of items to be updated, the number of bibliographic records affected, the count of other copies of those titles that are NOT in the working table but will also be affected by record-level changes, and any warnings (items on loan, items on hold).

**Bulk Deletion**

- **FR-032**: The system MUST allow permanent deletion of selected items without deleting their parent bibliographic record (the record is preserved as long as other copies remain).
- **FR-033**: Items currently on loan MUST be excluded from deletion silently (not deleted); the count of excluded items MUST be shown in the confirmation modal.
- **FR-034**: Deleting an item with an active hold reservation MUST also cancel that hold.
- **FR-035**: A confirmation modal MUST be shown before any deletion, clearly stating the action is irreversible and showing the number of items that will be deleted.

**Export**

- **FR-036**: The CSV export MUST include all items currently in the working table (not only selected ones), with these columns: barcode, title, author, call number, location, status, condition, last loan date, last inventory date.

**Admin Operations**

- **FR-037**: An admin-only menu on the inventory page MUST provide a "Delete records with no copies" action.
- **FR-038**: The count of records with no copies MUST be fetched on demand when the user triggers the action, not preloaded at page open.
- **FR-039**: The system MUST show a confirmation modal before deleting orphan records, displaying the count and a warning that the action is irreversible.
- **FR-040**: If no orphan records exist, the system MUST inform the user rather than proceeding silently.

### Key Entities

- **Item (Exemplaire)**: A physical copy of a book. Key attributes: unique barcode, condition (good/damaged), status (available, on loan, on hold, in repair, lost, withdrawn), borrowability flag, shelf location, last loan date, last inventory date. Each item belongs to exactly one bibliographic record.
- **Bibliographic Record (Notice)**: Represents a distinct title. Key attributes: category, genre, reading level, target audience, medium type, publication year. May have zero or more associated items; records with zero items are considered orphans.
- **Working Table**: A session-scoped list of items under review during an active inventory session. Persisted in browser storage on the same device — survives page refresh and tab close. Not synced across devices or users.
- **Inventory Date**: The timestamp of the most recent physical verification of an item's presence during a formal inventory check. Distinct from modification date and loan date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A librarian can scan 100 items and have all of them marked as inventoried in under 5 minutes without needing to use a mouse between scans.
- **SC-002**: Bulk editing 300 items (applying a status and condition change) completes within 30 seconds of the librarian confirming the action.
- **SC-003**: The search with all filters simultaneously active returns results in under 2 seconds on a school computer that is at least 5 years old.
- **SC-004**: A librarian can complete a full inventory session — scan, review, bulk edit, and export — without navigating away from the inventory page.
- **SC-005**: After a bulk deletion, items from the same title that were not selected remain fully accessible in the catalog.
- **SC-006**: The CSV export exactly reflects the current contents of the working table at the moment of export.
- **SC-007**: An imported file of 500 item IDs is parsed and ready to import in under 3 seconds.

## Clarifications

### Session 2026-04-02

- Q: Who can access the inventory page? → A: Any authenticated user — same access model as all other pages in the application; the admin menu within the page gates destructive operations only.
- Q: Should the working table survive a page refresh? → A: Yes — persisted in browser storage (survives refresh and tab close on the same device; not synced across devices).
- Q: When bulk-editing bibliographic records, should the confirmation modal warn that other copies of the same titles (not in the working table) will also be affected? → A: Yes — the modal must explicitly state the count of other affected copies outside the selection.
- Q: How should search results be displayed in the search tab? → A: All results up to a hard cap (200 items), with a visible message when the cap is reached prompting the user to refine filters. No pagination controls.

## Assumptions

- The barcode prefix-stripping logic used elsewhere in the application (catalog, checkout) is reused here without modification.
- The archive cutoff date (beyond which historical loans are unavailable) is exposed by the system to the inventory page so the rotation filter warning can be shown.
- Items currently on loan cannot have their status changed — this is an existing business rule applied consistently across the application.
- Items with "on hold" status can have their status changed with a warning; the hold is not automatically cancelled by a status change (only by deletion).
- The working table is client-side only (not persisted to the database) but MUST survive page refreshes and tab closes via browser storage on the same device. It is not synced across devices or users.
- Reading level and publication year range are new search capabilities not yet available in the existing catalog search.
- Bulk editing bibliographic records applies to all copies of those titles system-wide, not only the selected copies — this is intentional. The confirmation modal MUST explicitly state the count of other copies outside the working table that will also be affected.

## Out of Scope

- Printing inventory reports or barcode labels.
- Input or export formats other than plain text (.txt) for import and CSV for export.
- Real-time collaborative inventory sessions (multiple users editing the same working table simultaneously).
- Scheduling or automating periodic inventory runs.
- Undo functionality after bulk edits or deletions have been confirmed.
- Modifying bibliographic identity fields (title, author, ISBN, publisher) through the inventory page.
