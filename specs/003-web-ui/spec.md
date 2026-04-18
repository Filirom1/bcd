# Feature Specification: Localhost Web UI for BCD Library System

**Feature Branch**: `003-web-ui`
**Created**: 2026-01-30
**Updated**: 2026-02-05 (Vue 3 migration complete, production deployment)
**Status**: Production
**Input**: User description: "Create a localhost web UI for the BCD software your built. Avoid complex build tool. Professional interface with a small kids theme for elementary school library."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Circulation Dashboard: Quick Checkout and Return (Priority: P1)

A librarian needs to perform circulation operations (checkout, return, renew) through a web interface during busy library hours. For checkout, the librarian scans or enters a borrower ID (student), then scans item barcodes - each item is checked out immediately as it's scanned (no confirmation step needed). For returns, the librarian only scans item barcodes - each item is returned immediately as it's scanned. When a borrower's info panel is displayed, the librarian can click "Renew All" to extend due dates for all renewable items the borrower currently has checked out. The interface provides immediate visual feedback for success, errors, and overdue warnings. Both barcode scanners and keyboard entry are supported.

**Why this priority**: This is the primary daily function of the library system. Librarians need a quick, accessible interface that works on any device with a browser. This represents 80% of daily interactions and must be fast and reliable. The streamlined immediate checkout/return workflow minimizes clicks and speeds up processing.

**Independent Test**: Can be fully tested by opening the web UI in a browser, performing checkout and return operations with test data. Delivers immediate value by providing a graphical alternative to the CLI for circulation operations.

**Acceptance Scenarios**:

1. **Given** librarian opens circulation page, **When** they scan or enter borrower ID "101", **Then** system displays borrower info panel with name, class, current loans, and overdue warnings if any
2. **Given** borrower info is loaded, **When** librarian scans item barcode "785", **Then** item is immediately checked out and added to running list with title, barcode, and due date (no confirmation needed)
3. **Given** borrower has items in checkout list, **When** librarian scans another item "787", **Then** item is immediately checked out and appears in the list
4. **Given** librarian has no barcode scanner, **When** they type item barcode manually and press Enter, **Then** item is checked out just like scanning
5. **Given** librarian is on return page, **When** they scan or enter item barcode "785", **Then** item is immediately returned with confirmation showing title, borrower name, and overdue status if applicable
6. **Given** an item "800" is already on loan to another borrower, **When** librarian attempts to check it out, **Then** system displays error message showing current borrower and due date, item is not added to list
7. **Given** borrower "102" has overdue items, **When** librarian enters borrower ID, **Then** system displays prominent red warning with list of overdue items in borrower info panel
8. **Given** borrower "103" is at loan limit (2/2 items), **When** librarian attempts to scan another item, **Then** system prevents checkout and displays loan limit error message
9. **Given** borrower "106" has 3 current loans checked out (items "785", "787", "790" with 0/2 renewals used), **When** librarian clicks "Renew All" button in borrower info panel, **Then** system extends due dates for all 3 items by 14 days and displays success notification "Renewed 3 item(s) successfully" with updated loan list showing new due dates
10. **Given** borrower "107" has 3 items checked out where 2 are renewable (0/2 renewals) and 1 is at renewal limit (2/2 renewals), **When** librarian clicks "Renew All" button, **Then** system renews the 2 eligible items, displays summary showing "Renewed 2 item(s)" with titles and new due dates, plus warning "1 item could not be renewed: Item 800 - Renewal limit reached (2/2)" in orange alert

---

### User Story 2 - Catalog Search and Browse Interface (Priority: P2)

Librarians and authorized users need to search the catalog through a web interface to find bibliographic records and check item availability. Users can search by title, author, ISBN, or subject. Search results display item availability status with visual indicators (available in green, on loan in orange, overdue in red). Clicking a result shows full bibliographic details and all copies with their current status. The detail view includes cross-navigation links to related entities (borrower currently holding the item, circulation history with clickable borrower links) and quick actions (return this item, view all items by same author).

**Why this priority**: Essential for helping borrowers find materials and for librarians to verify inventory. Web interface makes catalog accessible from multiple devices without CLI knowledge. Cross-navigation and quick actions enable efficient workflows without returning to search.

**Independent Test**: Can be tested by cataloging sample records and performing searches with various criteria. Verifies that users can discover materials through an intuitive interface.

**Acceptance Scenarios**:

1. **Given** catalog has bibliographic records, **When** user types "Stuart" in search box and submits, **Then** system displays matching records with titles, authors, and availability indicators
2. **Given** search returns multiple results, **When** user clicks on a bibliographic record, **Then** system shows full details including all copies with barcode numbers, status, and due dates if on loan
3. **Given** an item is on loan, **When** user views item details, **Then** system displays borrower name as clickable link that navigates to borrower detail page
4. **Given** user views bibliographic record detail, **When** they scroll to circulation history section, **Then** system shows all past checkouts with clickable borrower names and dates
5. **Given** user is viewing item detail for on-loan item, **When** they click "Return this item" quick action, **Then** system processes return and updates item status immediately
6. **Given** all copies of a title are on loan, **When** user views the record, **Then** system displays due dates for each copy and highlights the earliest return date
7. **Given** user searches by ISBN "9782211234567", **When** search executes, **Then** system returns exact match immediately without pagination
8. **Given** user is on search results page, **When** they filter by "Available only", **Then** system shows only records with at least one available copy

---

### User Story 3 - Borrower Management Interface (Priority: P3)

A librarian needs to manage borrower records through a web interface. They can view borrower lists organized by class, search for specific borrowers, view circulation history, update borrower information, and import new borrowers. The interface displays borrower details including current loans (with clickable item links), overdue items, and contact information. The detail view includes quick actions (return all items, renew all items, view borrowing history) and cross-navigation to related items. Librarians can also bulk import borrowers from CSV files.

**Why this priority**: Important for borrower administration but less frequent than circulation operations. Web interface makes it easier to manage multiple borrowers without CLI commands. Import functionality enables efficient setup at start of school year.

**Independent Test**: Can be tested by creating borrowers, searching, viewing details, updating records, and importing CSV files. Delivers value by providing an organized view of borrower data.

**Acceptance Scenarios**:

1. **Given** librarian is on borrowers page, **When** they select class "CP-A" from dropdown, **Then** system displays all borrowers in that class with names, IDs, and current loan counts
2. **Given** librarian searches for "BENALI", **When** search executes, **Then** system displays matching borrowers with highlighting on matched text
3. **Given** librarian clicks on borrower "101", **When** detail page loads, **Then** system shows full borrower info, current loans with due dates, and circulation history with clickable item titles
4. **Given** librarian views borrower with current loans, **When** they click on item title in current loans list, **Then** system navigates to that item's detail page
5. **Given** librarian views borrower circulation history, **When** they click on any historical item title, **Then** system navigates to that item's detail page
6. **Given** librarian is on borrower detail page with current loans, **When** they click "Return all items" quick action button, **Then** system processes return for all items and updates display
7. **Given** borrower "104" has overdue items, **When** viewing borrower list, **Then** system displays red warning icon next to borrower name
8. **Given** librarian edits borrower class from "CP-A" to "CP-B", **When** they save changes, **Then** system updates borrower record and refreshes display with new class assignment
9. **Given** librarian is on borrowers page, **When** they click "Import Borrowers" and select a CSV file with borrower data, **Then** system validates and imports all borrowers showing success/error count
10. **Given** librarian views active borrower "105" detail page, **When** they click "Block Borrower" button, **Then** modal opens with blocking reason dropdown (Lost Book, Damaged Materials, Repeated Overdue, Policy Violation, Other) and optional notes field
11. **Given** librarian selects "Lost Book" reason and enters notes "Lost: Stuart Little", **When** they click "Block Borrower" confirm button, **Then** borrower is blocked, modal closes, detail page refreshes showing red "Bloqué" badge with reason "Lost Book - Lost: Stuart Little"
12. **Given** librarian views blocked borrower "105" detail page, **When** they click "Unblock Borrower" button and confirm in dialog, **Then** borrower is unblocked, detail page refreshes showing green "Actif" badge, and borrower can borrow materials again
13. **Given** librarian views borrower "106" detail page with 3 current loans (items "785", "787", "790" all renewable with 0/2 renewals), **When** they click "Renew All" button in modal footer, **Then** system extends due dates for all 3 items by 14 days, displays green success alert "Renewed 3 item(s) successfully" with list of renewed titles and new due dates, and refreshes current loans table showing updated information
14. **Given** librarian views borrower "107" detail page with mixed renewal status (2 items renewable, 1 at limit), **When** they click "Renew All" button on borrower detail page, **Then** system displays renewal summary in modal showing green section "Successfully renewed (2)" with titles "Stuart Little (new due: 2025-06-15)" and "Charlotte's Web (new due: 2025-06-15)", plus orange warning section "Could not renew (1)" with "The Trumpet of the Swan - Renewal limit reached (2/2)", and current loans table updates to reflect new due dates

---

### User Story 4 - Cataloging Interface with ISBN Lookup (Priority: P4)

A librarian needs to add new bibliographic records and physical items to the catalog through a web form. The workflow is: scan or enter ISBN to retrieve bibliographic information from BNF API (auto-fill form), review/edit the information, then scan or enter the physical BCD barcode to create the item and link it to the bibliographic record. For items without ISBN, the librarian can manually enter bibliographic details. Librarians can also bulk import books from CSV files.

**Why this priority**: Important for maintaining catalog but can be done during quieter periods. Web interface makes cataloging more accessible than CLI commands. Import functionality enables efficient catalog population.

**Independent Test**: Can be tested by entering known ISBNs, verifying data retrieval, scanning BCD barcodes, and importing CSV files. Delivers value by simplifying cataloging workflow.

**Acceptance Scenarios**:

1. **Given** librarian is on cataloging page, **When** they scan or enter ISBN "9782211234567" and press lookup, **Then** system retrieves bibliographic data from BNF and auto-fills form fields (title, author, publisher, etc.)
2. **Given** BNF lookup succeeds and form is populated, **When** librarian reviews data and scans or enters BCD barcode "ITEM-785", **Then** system creates bibliographic record and physical item with that barcode, showing confirmation message
3. **Given** ISBN is not found in BNF, **When** lookup fails, **Then** system displays message and allows manual entry in blank form, then librarian can enter BCD barcode to create item
4. **Given** librarian enters ISBN for existing record, **When** lookup detects duplicate, **Then** system shows existing record and prompts to scan BCD barcode to add another copy (item) of same title
5. **Given** librarian manually enters bibliographic data, **When** they fill required fields and scan BCD barcode, **Then** system validates and creates bibliographic record and item
6. **Given** librarian has no barcode scanner, **When** they type ISBN and BCD barcode manually with keyboard, **Then** system processes just like scanning
7. **Given** librarian is on cataloging page, **When** they click "Import Books" and select CSV file with bibliographic and item data, **Then** system validates and imports all books showing success/error count

---

### User Story 5 - Reports and Statistics Dashboard (Priority: P5)

A librarian needs to view library statistics and generate reports through a web interface. The dashboard displays overdue items by class, never-borrowed titles, and most popular titles. Reports can be filtered by date range and class. The librarian can print or download reports for distribution.

**Why this priority**: Valuable for library management but not critical for daily operations. Web interface makes reports more accessible than CLI commands.

**Independent Test**: Can be tested by generating sample circulation data and viewing various reports. Verifies that statistics accurately reflect library activity.

**Acceptance Scenarios**:

1. **Given** some items are overdue, **When** librarian views overdue report, **Then** system displays items grouped by class with borrower names, titles, and days overdue
2. **Given** librarian selects class "CE1-B" from filter, **When** filter applies, **Then** system shows only overdue items for borrowers in that class
3. **Given** librarian views never-borrowed report, **When** page loads, **Then** system displays bibliographic records with zero checkouts in current academic year
4. **Given** librarian views most borrowed report, **When** page loads, **Then** system displays top 10 titles ranked by checkout count with visual chart
5. **Given** librarian clicks print button on overdue report, **When** print dialog opens, **Then** system formats report for printing with one page per class

---

### User Story 6 - System Settings and Configuration (Priority: P6)

An administrator needs to configure system settings through a web interface. Settings include loan duration, checkout limits, academic year dates, and barcode format preferences. Changes are saved immediately and applied to future operations.

**Why this priority**: Necessary for system configuration but rarely changed after initial setup. Web interface makes settings more accessible than configuration files.

**Independent Test**: Can be tested by changing settings and verifying they affect circulation operations. Delivers value by providing GUI for system configuration.

**Acceptance Scenarios**:

1. **Given** admin is on settings page, **When** they change loan duration from 14 to 21 days and save, **Then** system updates setting and shows confirmation message
2. **Given** admin changes checkout limit from 2 to 3 items, **When** they save settings, **Then** future checkouts allow up to 3 items per borrower
3. **Given** admin views current settings, **When** page loads, **Then** system displays all configurable parameters with current values in form fields
4. **Given** admin enters invalid value (e.g., negative loan duration), **When** they attempt to save, **Then** system displays validation error without saving changes
5. **Given** admin changes academic year start date, **When** saved, **Then** reports use new date boundary for "current year" calculations

---

### Edge Cases

- What happens when network connection to API server fails? UI must display clear error messages and allow retry without losing entered data.
- What happens when barcode scanner input is received? UI must capture scanned barcodes in input fields just like keyboard entry.
- What happens when browser doesn't support JavaScript? System must display message requiring modern browser with JavaScript enabled.
- What happens when librarian has multiple browser tabs open? Each tab operates independently; changes in one tab require manual refresh in others to see updates.
- What happens when API returns validation errors? UI must display field-specific error messages inline near relevant form fields.
- What happens when search returns hundreds of results? UI must paginate results with 50 items per page and provide navigation controls.
- What happens when user navigates back after submitting a form? Browser may show cached data; UI should not allow duplicate submissions.
- What happens when session is idle for extended period? UI should handle stale data gracefully and refresh from API when user returns.
- What happens when printing labels on different browsers? UI should use browser print functionality; actual formatting depends on browser print engine.
- What happens when user resizes browser window? UI must be responsive and adapt layout for different screen sizes (desktop, tablet).

## Requirements *(mandatory)*

### Functional Requirements

**Core Web UI Infrastructure**

- **FR-001**: System MUST serve static HTML, CSS, and JavaScript files from FastAPI server without requiring external build tools
- **FR-002**: System MUST provide a single-page application (SPA) interface that loads once and updates dynamically via API calls
- **FR-003**: System MUST use Vue 3 framework loaded from CDN (no build tools, no npm, no webpack)
- **FR-004**: System MUST communicate with BCD REST API using fetch API for all data operations
- **FR-005**: System MUST display user-friendly error messages when API requests fail with appropriate retry options
- **FR-006**: System MUST support browser-based barcode scanner input in all relevant input fields
- **FR-007**: System MUST be responsive and functional on desktop browsers with minimum 1024x768 resolution
- **FR-008**: System MUST work on modern browsers (Chrome, Firefox, Safari, Edge - latest 2 versions)

**Circulation Operations Interface**

- **FR-009**: System MUST provide checkout page with borrower ID input and item barcode scanning interface
- **FR-010**: System MUST display real-time validation when borrower ID is entered (active status, current loans, overdue items)
- **FR-011**: System MUST check out each item IMMEDIATELY when barcode is scanned (no separate confirmation step required)
- **FR-012**: System MUST show visual confirmation in running list after each item is checked out with item title, barcode, and due date
- **FR-013**: System MUST prevent checkout and display error message when borrower is over limit or item is unavailable
- **FR-014**: System MUST provide return page with item barcode scanning interface (no borrower ID required)
- **FR-015**: System MUST return each item IMMEDIATELY when barcode is scanned (no separate confirmation step required)
- **FR-016**: System MUST display return confirmation showing item title, borrower name, and overdue status if applicable after each scan
- **FR-017**: System MUST support both barcode scanner input and manual keyboard entry for all barcode fields
- **FR-018**: System MUST process keyboard-entered barcodes identically to scanned barcodes (press Enter to submit)
- **FR-019**: System MUST display overdue warnings prominently in red when borrower has overdue items

**Renewal Actions (Cross-Context)**

- **FR-020-RENEW-1**: System MUST provide "Renew All" button in TWO contexts: (a) borrower info panel on circulation page, and (b) borrower detail modal footer - button appears only when borrower has current loans (current_loans_count > 0)
- **FR-020-RENEW-2**: "Renew All" action MUST extend due dates for all renewable items currently checked out to the borrower by the configured loan_duration_days (default: 14 days) - logic identical in both contexts
- **FR-020-RENEW-3**: System MUST display renewal summary showing successfully renewed items with titles and new due dates in green success alert, and failed items with reasons (e.g., "Renewal limit reached (2/2)") in orange warning alert
- **FR-020-RENEW-4**: System MUST NOT renew items that have reached the renewal_limit configured in system settings (default: 2 renewals)
- **FR-020-RENEW-5**: "Renew All" action MUST NOT trigger any blocking or unblocking of borrowers - it only extends due dates for eligible items
- **FR-020-RENEW-6**: System MUST refresh UI after renewal completes: circulation page refreshes borrower info panel, borrower detail modal refreshes current loans table without closing modal

**Catalog Search and Browse Interface**

- **FR-017**: System MUST provide search interface with input field and search button
- **FR-018**: System MUST support searching by title, author, ISBN, subject, and item barcode
- **FR-019**: System MUST display search results with title, author, publication year, and availability status
- **FR-020**: System MUST use color-coded indicators for item status (green=available, orange=on loan, red=overdue)
- **FR-021**: System MUST show detailed bibliographic record when user clicks on search result
- **FR-022**: System MUST display all copies (items) for a bibliographic record with individual status and due dates
- **FR-023**: System MUST paginate search results with 50 items per page and page navigation controls
- **FR-024**: System MUST provide filter options for availability status on search results page

**Borrower Management Interface**

- **FR-025**: System MUST provide borrower list page with search and class filter options
- **FR-026**: System MUST display borrower summary showing ID, name, class, and current loan count
- **FR-027**: System MUST highlight borrowers with overdue items using visual warning indicators
- **FR-028**: System MUST show borrower detail page with full information, current loans, and circulation history
- **FR-029**: System MUST provide edit form for updating borrower information (class, contact info, active status)
- **FR-030**: System MUST validate borrower data before submitting updates to API

**Borrower Blocking Actions**

- **FR-030-BLOCK-1**: System MUST provide dedicated block/unblock button on borrower detail page that appears conditionally (block button when borrower active, unblock button when borrower blocked)
- **FR-030-BLOCK-2**: Block action MUST open modal dialog with standardized blocking reasons dropdown containing: "Lost Book", "Damaged Materials", "Repeated Overdue Items", "Policy Violation", and "Other"
- **FR-030-BLOCK-3**: System MUST allow optional notes field for additional blocking context with combined reason + notes maximum of 200 characters total
- **FR-030-BLOCK-4**: Unblock action MUST display confirmation dialog before restoring borrower access with borrower name and warning about restoring privileges
- **FR-030-BLOCK-5**: System MUST validate that a reason is selected from dropdown before allowing block action to proceed
- **FR-030-BLOCK-6**: System MUST display success notification after block/unblock action completes and refresh borrower detail display to show updated status

**Cataloging Interface**

- **FR-031**: System MUST provide cataloging form with ISBN lookup button and manual entry fields
- **FR-032**: System MUST display retrieved BNF data in editable form fields after successful ISBN lookup
- **FR-033**: System MUST allow manual entry of bibliographic data when ISBN lookup fails
- **FR-034**: System MUST detect duplicate ISBNs and offer to add additional copy instead of new record
- **FR-035**: System MUST generate item barcode after bibliographic record is created
- **FR-036**: System MUST validate required bibliographic fields before submission

**Reports and Statistics Interface**

- **FR-037**: System MUST provide dashboard page displaying key library statistics
- **FR-038**: System MUST generate overdue report showing items grouped by class with borrower and item details
- **FR-039**: System MUST generate never-borrowed report showing bibliographic records with zero circulations in current year
- **FR-040**: System MUST generate most borrowed report showing top titles ranked by circulation count
- **FR-041**: System MUST allow filtering reports by class and date range
- **FR-042**: System MUST format reports for printing using browser print functionality

**System Settings Interface**

- **FR-043**: System MUST provide settings page displaying all configurable system parameters
- **FR-044**: System MUST allow editing loan duration, checkout limit, and academic year dates
- **FR-045**: System MUST validate settings before submission (positive numbers, valid dates)
- **FR-046**: System MUST display confirmation message after settings are successfully updated
- **FR-047**: System MUST show current values when settings page loads

**Navigation and User Experience**

- **FR-048**: System MUST provide navigation menu accessible from all pages with links to main sections
- **FR-049**: System MUST highlight current page/section in navigation menu
- **FR-050**: System MUST display loading indicators during API requests longer than 500ms
- **FR-051**: System MUST preserve form data when API requests fail to prevent data loss
- **FR-052**: System MUST provide keyboard shortcuts for common operations (Enter to submit, Escape to cancel)
- **FR-053**: System MUST support browser back/forward navigation without breaking application state
- **FR-054-CROSS**: System MUST provide clickable links for cross-navigation between related entities (borrower name links to borrower detail, item title links to item detail)
- **FR-055-CROSS**: System MUST display borrowing history with clickable item titles and borrower names that navigate to respective detail pages
- **FR-056-QUICK**: System MUST provide quick action buttons in detail views (e.g., "Return this item" on item detail, "Return all items" on borrower detail, "Renew all items" on borrower detail)
- **FR-057-QUICK**: Quick actions MUST process immediately without requiring navigation to another page

**Import and Export**

- **FR-058-IMPORT**: System MUST provide CSV import functionality for bulk adding borrowers through web interface
- **FR-059-IMPORT**: System MUST provide CSV import functionality for bulk adding books and items through web interface
- **FR-060-IMPORT**: System MUST validate imported data and display success/error count with detailed error messages for failed rows
- **FR-061-IMPORT**: System MUST support keyboard file selection when no drag-and-drop is available

**Visual Design and Theming**

- **FR-062-UI**: System MUST use Bootstrap 5.3.3 design system with professional typography (font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; base font-size: 16px; line-height: 1.5)
- **FR-063-UI**: System MUST use warm color palette with measurable values:
  - Primary brand: #4A90E2 (warm blue, used for navigation and primary buttons)
  - Success/Available: #28A745 (green, used for availability badges and success alerts)
  - Warning/On-Loan: #FFC107 (amber, used for on-loan status and warning alerts)
  - Danger/Overdue: #DC3545 (red, used for overdue badges and error alerts)
  - Neutral backgrounds: #F8F9FA (light gray for cards), #FFFFFF (white for main content)
- **FR-064-UI**: System MUST incorporate book/education-themed Bootstrap Icons 1.11.3 with minimum 1.25rem size for visibility: bi-book, bi-person-badge, bi-calendar-check, bi-search, bi-printer, bi-gear
- **FR-065-UI**: System MUST use Bootstrap button sizing for efficient workflows:
  - Primary actions (checkout, save, submit): .btn-lg (min-height: 48px, min-width: 120px for touch compatibility)
  - Secondary actions (cancel, reset): .btn (min-height: 38px)
  - Tertiary actions (filter toggles): .btn-sm (min-height: 31px)
- **FR-066-UI**: System MUST use Bootstrap badge components for status indicators with WCAG 2.1 AA contrast ratios (minimum 4.5:1 for text):
  - Available: .badge.bg-success with white text (#FFFFFF on #28A745 = 4.53:1 contrast)
  - On Loan: .badge.bg-warning with dark text (#212529 on #FFC107 = 6.47:1 contrast)
  - Overdue: .badge.bg-danger with white text (#FFFFFF on #DC3545 = 5.91:1 contrast)
- **FR-067-UI**: System MUST use consistent spacing scale from Bootstrap 5 spacing utilities (0.25rem increments): p-2 (0.5rem), p-3 (1rem), p-4 (1.5rem), mb-3 (1rem bottom margin), gap-2 (0.5rem grid gap)

**Localization**

- **FR-068**: System MUST provide complete interface in French (primary language for school library)
- **FR-069**: System MUST display dates in French format (DD/MM/YYYY)
- **FR-070**: System MUST support English as secondary language with language switcher in UI

**Vue 3 Implementation Notes** (Implemented as of 2026-02-05)

- System uses Vue 3 framework loaded from CDN (unpkg.com) - no build tools required
- Vue 3 Composition API with reactive components for all pages
- Vue Router 4 provides hash-based routing (#/checkout, #/catalog, etc.)
- Vue I18n 9 handles internationalization using existing locale files (locales/en.json, locales/fr.json)
- All pages implemented with reusable component architecture (40+ components)
- Legacy HTMX implementation archived at `src/bcd_web_legacy/` for reference
- Performance validated: scanner feedback <200ms, page navigation <100ms, all acceptance scenarios passed

### Key Entities

*Note: These are the same entities as the core BCD system, accessed via the REST API*

- **Web Page/View**: Represents a distinct UI screen in the SPA; examples include Circulation Page (checkout/return forms), Catalog Search Page (search interface and results), Borrower List Page (filterable borrower table), Borrower Detail Page (individual borrower information and loans), Cataloging Page (ISBN lookup and manual entry form), Reports Dashboard (statistics and report generation), Settings Page (system configuration form)

- **UI Component**: Represents reusable interface elements; examples include Navigation Menu (main navigation links), Search Box (text input with search button), Data Table (paginated list with sorting), Form Field (input with validation), Status Badge (color-coded availability indicator), Alert Message (success/error/warning notifications), Loading Spinner (API request feedback)

- **User Interaction Flow**: Represents a sequence of user actions to complete a task; examples include Checkout Flow (enter borrower ID → scan items → confirm), Search Flow (enter search term → view results → select record), Add Catalog Flow (enter ISBN → lookup → review → save)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Librarian can complete checkout transaction (open page, enter borrower, scan 2 items, confirm) in under 45 seconds
- **SC-002**: Librarian can process return transaction (open page, scan 5 items) in under 30 seconds
- **SC-003**: Search results appear within 2 seconds of entering search query for catalog of 5,000 records
- **SC-004**: Web UI loads and becomes interactive within 3 seconds on standard school computer with broadband connection
- **SC-005**: UI remains responsive during API requests longer than 1 second by displaying loading indicators
- **SC-006**: All pages are functional without JavaScript frameworks, using only vanilla JavaScript and modern browser APIs
- **SC-007**: UI works correctly on Chrome, Firefox, Safari, and Edge (latest 2 versions) without browser-specific code
- **SC-008**: Barcode scanner input is captured correctly in all input fields just like keyboard entry
- **SC-009**: Error messages are displayed clearly and provide actionable guidance for resolution
- **SC-010**: Navigation between pages feels instant (under 100ms) due to SPA architecture
- **SC-011**: UI adapts correctly to different screen sizes from 1024x768 to 1920x1080 resolution
- **SC-012**: Users can complete common tasks (search, checkout, return) in under 3 clicks from home page
- **SC-013**: Print formatting for reports produces readable output on standard office printers

### Assumptions

- School has existing BCD API server running on localhost or local network accessible via HTTP
- Librarians use desktop or laptop computers with modern browsers (Chrome, Firefox, Safari, Edge)
- Barcode scanners emit keyboard input just like typing (standard USB HID keyboard mode)
- Web UI will be served from the same FastAPI server as the API (no CORS issues)
- Librarians have basic web browser skills (click, type, navigate)
- Internet connection is available for initial page load and API requests (all data from API, not third-party CDNs)
- JavaScript is enabled in browsers (modern web standard requirement)
- UI will be accessed locally or on school LAN, not over public internet (no authentication required)
- FastAPI server has capability to serve static files from a directory
- Librarians will access UI from URLs like http://localhost:8000 or http://library-server.local:8000
- CSS and JavaScript can be written in modern standards (ES6+, CSS3) without transpilation
- No complex state management needed beyond local component state and API data
- Reports will be printed using browser print functionality (Ctrl+P / Cmd+P)
- System settings changes take effect immediately for new operations (no server restart required)
