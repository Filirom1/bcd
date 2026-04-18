# Feature Specification: Admin Features Panel

**Feature Branch**: `006-admin-features`
**Created**: 2026-02-07
**Status**: Draft
**Input**: User description: "admin features. That will be displayed in an admin button menu top right (red). import export button will be moved in this menu. Add a feature to bulk edit borrower (change class, delete borrower (when they change of school), change role), and also edit single borrower (rename, change id, change role). Regarding notice & examplaire, a feature a allow bulk edit (remove, rename fields) & also single edit notice & borrower . Add a feature to manage class (CRUD)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Menu on Borrower & Catalog Pages (Priority: P1)

A librarian needs to access administrative operations (import/export, bulk actions) without accidentally clicking them during normal workflows. Dangerous actions should be grouped in a clearly marked admin menu.

**Why this priority**: Foundation for all admin features. Protects against misclicks on destructive operations while keeping them accessible when needed.

**Independent Test**: Can be fully tested by visiting Borrower and Catalog pages, clicking the admin menu, and verifying all operations are accessible.

**Acceptance Scenarios**:

1. **Given** a librarian is on the Borrowers page, **When** they look at the top-right action area, **Then** they see a red "Admin" dropdown button (replaces individual import/export buttons)
2. **Given** a librarian clicks the "Admin" dropdown on the Borrowers page, **When** the menu opens, **Then** they see options: Import Borrowers, Export Borrowers, Bulk Edit, Edit Selected
3. **Given** a librarian is on the Catalog page, **When** they look at the top-right action area, **Then** they see a red "Admin" dropdown button
4. **Given** a librarian clicks the "Admin" dropdown on the Catalog page, **When** the menu opens, **Then** they see options: Import Catalog, Export Catalog, Bulk Edit, Edit Selected
5. **Given** the admin menu is collapsed, **When** a librarian performs normal operations (search, checkout, etc.), **Then** they cannot accidentally trigger destructive admin actions

---

### User Story 2 - Class Management Page (Priority: P2)

A librarian needs a dedicated page to manage classes (create, view, edit, delete) since classes don't currently have a web UI. This is essential for organizing borrowers by class.

**Why this priority**: Classes are foundational data. Without a UI, librarians cannot manage classes, which blocks bulk borrower operations (P3) that reassign students to classes.

**Independent Test**: Can be fully tested by creating a new class, editing it, deleting it, and verifying database changes.

**Acceptance Scenarios**:

1. **Given** a librarian navigates to the Classes page (new), **When** the page loads, **Then** they see a table listing all classes with columns: Class Name, Grade Level, Student Count, Actions
2. **Given** a librarian clicks "Create Class", **When** they fill in the form (name, grade level) and submit, **Then** a new class is created and appears in the list
3. **Given** a librarian clicks "Edit" on a class, **When** they modify the name or grade level and save, **Then** the class is updated
4. **Given** a librarian clicks "Delete" on a class with no students, **When** they confirm deletion, **Then** the class is removed
5. **Given** a librarian clicks "Delete" on a class with assigned students, **When** they confirm deletion, **Then** all students are unassigned (class_id set to NULL) and the class is removed

---

### User Story 3 - Bulk Borrower Operations (Priority: P3)

A librarian needs to perform bulk operations on borrowers (change class for grade advancement, delete borrowers leaving school, change roles) to save time during administrative transitions.

**Why this priority**: Enables efficient year-end transitions (e.g., moving 30 students from CP to CE1). Depends on Class Management (P2) for class reassignment.

**Independent Test**: Can be fully tested by selecting multiple borrowers, changing their class, and verifying all updates succeed.

**Acceptance Scenarios**:

1. **Given** a librarian is on the Borrowers page, **When** they select multiple borrowers using checkboxes, **Then** the "Admin" dropdown shows "Bulk Edit" option as enabled
2. **Given** multiple borrowers are selected and librarian clicks "Bulk Edit", **When** they choose "Change Class" and select a target class, **Then** all selected borrowers are reassigned
3. **Given** multiple borrowers are selected and librarian clicks "Bulk Edit", **When** they choose "Change Role" and select a role (student/teacher/staff), **Then** all selected borrowers have their role updated
4. **Given** multiple borrowers are selected and librarian clicks "Bulk Edit", **When** they choose "Delete", **Then** they see a confirmation dialog showing count and names of borrowers to be deleted
5. **Given** librarian confirms deletion, **When** the operation completes, **Then** all selected borrowers and their circulation history are removed

---

### User Story 4 - Single Borrower Editing (Priority: P4)

A librarian needs to edit individual borrower details (name, ID, role, class) to correct data entry errors or handle special cases.

**Why this priority**: Handles individual corrections that don't fit bulk operations. Lower priority than bulk since it affects fewer records.

**Independent Test**: Can be fully tested by selecting one borrower, editing their details, and verifying changes are saved.

**Acceptance Scenarios**:

1. **Given** a librarian selects a single borrower on the Borrowers page, **When** they click "Admin" → "Edit Selected", **Then** they see an edit form with fields: first name, last name, borrower ID, role, class
2. **Given** a librarian edits the borrower's name, **When** they save, **Then** the name is updated in the database and reflected in all views
3. **Given** a librarian changes the borrower ID to a unique value, **When** they save, **Then** the ID is updated if it passes validation (format and uniqueness)
4. **Given** a librarian changes the borrower ID to a duplicate value, **When** they save, **Then** they see an error message preventing the duplicate
5. **Given** a librarian changes the borrower's class or role, **When** they save, **Then** the borrower's class/role is updated

---

### User Story 5 - Bulk Catalog Operations (Priority: P5)

A librarian needs to perform bulk operations on bibliographic records (delete multiple records, edit common fields) for catalog maintenance.

**Why this priority**: Less frequently needed than borrower management. Most catalog updates happen via re-import. This handles cleanup scenarios.

**Independent Test**: Can be fully tested by selecting multiple catalog records, performing bulk edit, and verifying changes apply to all.

**Acceptance Scenarios**:

1. **Given** a librarian is on the Catalog page, **When** they select multiple bibliographic records using checkboxes, **Then** the "Admin" dropdown shows "Bulk Edit" option as enabled
2. **Given** multiple records are selected and librarian clicks "Bulk Edit", **When** they choose "Delete Records", **Then** they see a confirmation dialog with count and list of titles
3. **Given** librarian confirms deletion, **When** the operation completes, **Then** selected bibliographic records and their associated items are removed (cascade delete)
4. **Given** multiple records are selected and librarian clicks "Bulk Edit", **When** they choose "Edit Fields", **Then** they see a form to edit common fields: publisher, publication year, language, subject tags
5. **Given** librarian edits common fields and saves, **When** the operation completes, **Then** all selected records have the specified fields updated in a single transaction

---

### User Story 6 - Single Catalog Record/Item Editing (Priority: P6)

A librarian needs to edit individual bibliographic records and items (correct metadata, update item details) for minor corrections.

**Why this priority**: Most granular operation. Most corrections handled via re-import. This is for edge cases.

**Independent Test**: Can be fully tested by selecting one record, editing its metadata, and verifying changes are saved.

**Acceptance Scenarios**:

1. **Given** a librarian selects a single bibliographic record on the Catalog page, **When** they click "Admin" → "Edit Selected", **Then** they see an edit form with fields: title, author, ISBN, publisher, publication year, language, subject tags, description
2. **Given** a librarian edits metadata fields, **When** they save, **Then** the record is updated and changes appear in search results
3. **Given** a librarian views items (exemplaires) for a record, **When** they click "Edit Item", **Then** they can edit: item ID/barcode, status, location, notes, loanable flag
4. **Given** a librarian changes an item's barcode to a unique value, **When** they save, **Then** the barcode is updated if it passes validation
5. **Given** a librarian changes an item's barcode to a duplicate, **When** they save, **Then** they see an error preventing the duplicate

---

### Edge Cases

- **Delete class with assigned borrowers**: Borrowers are unassigned (class_id set to NULL), class is deleted
- **Delete bibliographic record with items on loan**: Record and items are deleted (cascade delete even if on loan)
- **Change borrower ID to duplicate**: Display error message "ID not available"
- **Bulk operations on 100+ records**: Show progress indicator like import workflow (percentage, progress bar)
- **Network/database errors during bulk operations**: Localhost-only deployment, rollback transaction on database errors
- **Delete borrower with active loans**: Borrower and all their circulation history are deleted (CASCADE delete for simplicity)
- **Duplicate barcode**: Display error message preventing duplicate
- **Click "Edit Selected" with no selection**: Button is disabled (no action occurs)

## Requirements *(mandatory)*

### Functional Requirements

#### Admin Menu UI (Borrowers & Catalog Pages)

- **FR-001**: Borrowers page MUST replace individual Import/Export buttons with a single red "Admin" dropdown menu in the top-right action area
- **FR-002**: Catalog page MUST replace individual Import/Export buttons with a single red "Admin" dropdown menu in the top-right action area
- **FR-003**: Admin dropdown on Borrowers page MUST contain: Import Borrowers, Export Borrowers, Bulk Edit (when ≥1 selected), Edit Selected (when exactly 1 selected)
- **FR-004**: Admin dropdown on Catalog page MUST contain: Import Catalog, Export Catalog, Bulk Edit (when ≥1 selected), Edit Selected (when exactly 1 selected)
- **FR-005**: Admin dropdown MUST use red styling (e.g., `btn-danger` class) to indicate destructive/sensitive operations
- **FR-006**: Admin dropdown menu items MUST be conditionally enabled based on selection count ("Edit Selected" enabled only when exactly 1 item selected, "Bulk Edit" enabled when ≥1 items selected, disabled otherwise)

#### Class Management Page (NEW)

- **FR-007**: System MUST provide a new "Classes" page accessible from main navigation
- **FR-008**: Classes page MUST display a table with columns: Class Name, Grade Level, Student Count, Actions (Edit, Delete)
- **FR-009**: Classes page MUST include a "Create Class" button that opens a creation form
- **FR-010**: Class creation form MUST require: name (text, unique), grade level (text, e.g., "CP", "CE1")
- **FR-011**: System MUST allow editing existing classes (name, grade level)
- **FR-012**: System MUST allow deletion of classes regardless of assigned students
- **FR-013**: When deleting a class with assigned borrowers, system MUST unassign all borrowers from the class (set class_id to NULL) before deleting the class
- **FR-014**: Class table MUST show real-time student count using denormalized counter pattern (Class.student_count incremented/decremented on borrower class assignment changes)

#### Bulk Borrower Operations

- **FR-015**: Borrowers page MUST support multi-selection via checkboxes
- **FR-016**: "Bulk Edit" option in Admin dropdown MUST open a modal with operations: Change Class, Change Role, Delete Selected
- **FR-017**: "Change Class" operation MUST show a dropdown of all available classes and update all selected borrowers
- **FR-018**: "Change Role" operation MUST show role options (student, teacher, staff) and update all selected borrowers
- **FR-019**: "Delete Selected" operation MUST show confirmation dialog with count and borrower names
- **FR-020**: System MUST allow deletion of borrowers even with active loans (CASCADE delete removes borrower and all their circulation history)
- **FR-021**: All bulk operations MUST execute in a single database transaction (atomic)
- **FR-022**: Bulk operations affecting ≥100 records MUST show progress indicator (percentage, progress bar) matching import workflow pattern

#### Single Borrower Editing

- **FR-023**: "Edit Selected" in Admin dropdown (enabled when exactly 1 borrower selected) MUST open an edit form
- **FR-024**: Borrower edit form MUST include fields: first name, last name, borrower ID, role (dropdown), class (dropdown)
- **FR-025**: System MUST validate borrower ID uniqueness on save
- **FR-026**: System MUST validate borrower ID format against system settings regex on save
- **FR-027**: System MUST prevent duplicate borrower IDs with error message "ID not available"

#### Bulk Catalog Operations

- **FR-028**: Catalog page MUST support multi-selection via checkboxes for bibliographic records
- **FR-029**: "Bulk Edit" option in Admin dropdown MUST open a modal with operations: Edit Fields, Delete Selected
- **FR-030**: "Edit Fields" operation MUST show form with common fields: category, genre, target_audience, language, medium_type
- **FR-031**: "Edit Fields" operation MUST update all selected records with specified field values (null values = no change)
- **FR-032**: "Delete Selected" operation MUST show confirmation dialog with count and record titles
- **FR-033**: "Delete Selected" operation MUST cascade delete to associated items even if items are currently on loan
- **FR-034**: All bulk catalog operations MUST execute in a single database transaction (atomic)

#### Single Catalog Record/Item Editing

- **FR-035**: "Edit Selected" in Admin dropdown (enabled when exactly 1 record selected) MUST open an edit form
- **FR-036**: Bibliographic record edit form MUST include fields: title, author, ISBN, publisher, publication year, language, subject tags, description
- **FR-037**: System MUST provide item editing interface accessible from record details view
- **FR-038**: Item edit form MUST include fields: item ID/barcode, status (dropdown), location, notes, loanable (checkbox)
- **FR-039**: System MUST validate item barcode uniqueness on save
- **FR-040**: System MUST validate item barcode format against system settings on save
- **FR-041**: System MUST prevent duplicate item barcodes with error message

#### General Requirements

- **FR-042**: All admin pages and dialogs MUST support bilingual display (English/French) via i18n
- **FR-043**: All forms MUST validate input client-side and server-side with clear error messages
- **FR-044**: All delete operations MUST require explicit confirmation dialog with details (count, names/titles in scrollable list with maximum 10 visible items)
- **FR-045**: All bulk operations MUST be atomic transactions with full rollback on any validation or database error (all succeed or all fail, no partial updates)
- **FR-046**: All admin operations MUST complete in <10 seconds for ≤100 records with progress indication
- **FR-047**: System MUST log all admin operations for audit trail (operation type, user, timestamp, affected records) except CASCADE deleted data

### Key Entities *(include if feature involves data)*

- **Class**: School class grouping. Attributes: id, name (unique), grade_level, created_at, updated_at. Computed: student_count (denormalized or count of Borrowers). Relationships: has many Borrowers.
- **Borrower**: Library user. Attributes: id, borrower_id (unique), first_name, last_name, role (student/teacher/staff), class_id (nullable FK), active, current_loans_count (denormalized). Relationships: belongs to Class, has many CirculationTransactions.
- **BiblographicRecord**: Catalog metadata. Attributes: id, title, author, isbn, publisher, publication_year, language, subject_tags (JSON/text), description. Relationships: has many Items (cascade delete).
- **Item**: Physical copy. Attributes: id, item_id (barcode, unique), bibliographic_record_id (FK), status, location, notes, loanable (boolean). Relationships: belongs to BiblographicRecord, has many CirculationTransactions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Librarians can access all admin operations in ≤2 clicks (Admin menu → operation)
- **SC-002**: Import/Export buttons no longer visible in default view, reducing accidental clicks by 100%
- **SC-003**: Librarians can perform bulk class changes for 30 students in <30 seconds (vs. 5+ minutes individually)
- **SC-004**: System prevents 100% of invalid operations (duplicate IDs, duplicate barcodes) with clear errors
- **SC-005**: All single-record edit forms validate and submit in <500ms
- **SC-006**: Bulk operations on 100 records complete in <10 seconds with progress indication
- **SC-007**: Zero data integrity violations (all bulk operations atomic)
- **SC-008**: 95% of admin operations completable via keyboard (Enter to submit, Esc to cancel)

## Assumptions

- Borrowers and Catalog pages already exist in the Vue 3 web UI
- Import/Export functionality already exists and just needs UI reorganization
- Database schema supports required operations (nullable class_id FK on Borrower, cascade delete on BiblographicRecord → Item)
- Vue 3 web UI uses Composition API and Bootstrap 5 (dropdown menus, modals, forms)
- API backend follows service-layer architecture (business logic in services, not routes)
- i18n infrastructure exists (en/fr locales) for error messages and UI labels
- Authentication/authorization handles admin access control
- Application runs on localhost (no network latency concerns)
- Database uses CASCADE delete for borrowers (simplicity over audit trail - deleting borrower deletes all their history)
- Progress indicator pattern from import workflow can be reused for bulk operations
