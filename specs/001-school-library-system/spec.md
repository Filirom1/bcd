# Feature Specification: School Library Management System

**Feature Branch**: `001-school-library-system`
**Created**: 2026-01-30
**Status**: Draft
**Input**: User description: "Write a small school library software (CLI first, web after). Main feature is loans/returns (bar code scanner), then cataloging (search by ISBN from BNF API, import standard format), user management (school with classes and students), document search, statistic, barcode print,"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Circulation Operations: Checkouts and Returns (Priority: P1)

A librarian needs to check out items to borrowers (students, teachers, staff) and process returns quickly during busy library hours. The librarian scans the borrower's ID barcode, then scans each item barcode to check them out. When borrowers return items, the librarian scans the item barcodes to complete the return transaction.

**Why this priority**: This is the core daily activity of a school library. Without circulation functionality, the library cannot operate. This represents 80% of daily library transactions.

**Independent Test**: Can be fully tested by creating a few borrower records and item records, then performing checkout and return operations via barcode scanning. Delivers immediate value by enabling the library's primary function.

**Acceptance Scenarios**:

1. **Given** a borrower exists in the system and items are available, **When** librarian scans borrower ID then scans 2 item barcodes, **Then** both items are checked out to the borrower with due dates assigned
2. **Given** a borrower has checked out items, **When** librarian scans the item barcodes at the return desk, **Then** items are marked as returned and removed from borrower's circulation list
3. **Given** an item is already on loan to another borrower, **When** librarian attempts to check it out, **Then** system displays error showing who has the item and when it's due back
4. **Given** a borrower has overdue items, **When** librarian scans the borrower's ID, **Then** system displays list of overdue items with days overdue before allowing new checkouts
5. **Given** a borrower reaches the maximum allowed checkouts, **When** librarian attempts to check out another item, **Then** system prevents the checkout and displays the loan limit

---

### User Story 2 - Cataloging with ISBN Lookup via BNF SRU API (Priority: P2)

A librarian needs to add new titles to the library collection efficiently. When a new book arrives, the librarian scans the ISBN barcode, and the system retrieves complete bibliographic information (title, author, publisher, publication date, subject) from the BNF (Bibliothèque nationale de France) SRU API in UNIMARC format. The librarian can review and confirm the information or make minor edits before saving the bibliographic record. The system then creates an item record (exemplaire) for the physical copy with a unique barcode. The librarian can also import bibliographic records in bulk using standard library formats.

**Why this priority**: Essential for maintaining an up-to-date catalog, but can be done in batches during quieter periods. Automated ISBN lookup significantly reduces manual data entry time from 5 minutes per title to 30 seconds.

**Independent Test**: Can be tested by scanning ISBNs of known books and verifying that correct bibliographic data is retrieved from BNF SRU API. Delivers value by streamlining the cataloging workflow.

**Acceptance Scenarios**:

1. **Given** librarian has a new book with ISBN, **When** librarian scans or enters ISBN, **Then** system retrieves and displays complete bibliographic information from BNF SRU API in UNIMARC format
2. **Given** bibliographic information is retrieved from BNF, **When** librarian reviews and confirms the data, **Then** bibliographic record is created in catalog and an item record is created with a unique barcode generated
3. **Given** an ISBN is not found in BNF database, **When** lookup fails, **Then** system allows manual entry of bibliographic record details
4. **Given** librarian has a file in standard library format (UNIMARC, MARC 21, or CSV), **When** librarian imports the file, **Then** all valid bibliographic records are added to the catalog with import summary showing successes and errors
5. **Given** a bibliographic record already exists in the catalog, **When** librarian attempts to add the same ISBN, **Then** system offers to add another item (copy) instead of creating duplicate bibliographic record

---

### User Story 3 - Borrower and Class Management (Priority: P3)

A school administrator or librarian needs to manage the borrower database (students, teachers, staff) organized by classes and roles. They can add individual borrowers or import entire class lists. Each borrower is assigned a unique barcode ID. Students can be grouped by grade level and class section for reporting and circulation policies.

**Why this priority**: Important for organization but can be set up initially and updated periodically (e.g., at start of school year). Not needed for daily library operations once initial setup is complete.

**Independent Test**: Can be tested by creating classes, adding borrowers individually and via bulk import, assigning barcodes, and verifying borrower organization by class and role. Delivers value by organizing users for better reporting and policy management.

**Acceptance Scenarios**:

1. **Given** administrator has borrower information, **When** they enter name, class (if student), role, and grade, **Then** borrower is created with unique barcode ID generated
2. **Given** administrator has class roster file, **When** they import CSV file with student names and class information, **Then** all borrowers are created with barcodes and grouped by class
3. **Given** borrowers exist in the system, **When** librarian views borrowers by class, **Then** borrowers are displayed organized by grade level, class section, and role
4. **Given** a student transfers to a different class, **When** administrator updates borrower's class assignment, **Then** borrower's record reflects new class while preserving circulation history
5. **Given** a student graduates or leaves school, **When** administrator marks borrower as inactive, **Then** borrower cannot check out new items but past circulation history is preserved

---

### User Story 4 - Catalog Search and Item Availability (Priority: P4)

Borrowers and librarians need to search the library catalog to find bibliographic records and check item availability. Users can search by title, author, subject, or ISBN. Search results show item availability status (available, on loan, overdue) and location information.

**Why this priority**: Valuable for helping borrowers find materials, but initially the collection may be small enough to browse. Becomes more critical as collection grows.

**Independent Test**: Can be tested by cataloging various bibliographic records with items and performing searches with different criteria. Verifies that users can discover and locate materials.

**Acceptance Scenarios**:

1. **Given** catalog has bibliographic records, **When** user searches by partial title or author name, **Then** system returns matching bibliographic records sorted by relevance
2. **Given** search returns results, **When** user views a bibliographic record's details, **Then** system displays full bibliographic information and current availability status for all items (copies)
3. **Given** an item is on loan, **When** user views the bibliographic record, **Then** system shows due date for loaned items and offers option to place a hold (reservation)
4. **Given** user searches by subject, **When** multiple records match, **Then** results are grouped by subject category
5. **Given** user searches by barcode or ISBN, **When** barcode matches an item or ISBN matches a bibliographic record, **Then** exact record is displayed immediately

---

### User Story 5 - Circulation Statistics and Reporting (Priority: P5)

Librarians and administrators need to view essential library statistics to manage overdue items and understand collection usage. The main reports are: overdue items per class (for printing and distribution), bibliographic records never borrowed this year (for collection evaluation), and most borrowed titles (top performers).

**Why this priority**: Important for library management but not critical for daily circulation operations. Can be implemented after core workflows are stable.

**Independent Test**: Can be tested by generating sample circulation transactions over time and verifying that statistics accurately reflect the data.

**Acceptance Scenarios**:

1. **Given** some items are overdue, **When** librarian generates overdue report, **Then** system produces one page per class showing all overdue items for borrowers in that class with borrower names, item information, and due dates
2. **Given** bibliographic records have circulation history throughout the year, **When** librarian requests never-borrowed report, **Then** system displays bibliographic records with zero checkouts in the current academic year
3. **Given** bibliographic records have different circulation counts, **When** librarian requests most borrowed titles, **Then** system displays bibliographic records ranked by number of checkouts showing top performers
4. **Given** librarian selects specific class, **When** generating overdue report, **Then** system produces single-page report for just that class
5. **Given** academic year boundary is crossed, **When** viewing never-borrowed report, **Then** system considers only circulation transactions from current academic year

---

### User Story 6 - Barcode Printing (Priority: P6)

Librarians need to print barcode labels for new items and borrower ID cards. The system generates printable barcode sheets in standard label formats compatible with common label printers.

**Why this priority**: Necessary for scaling the library, but initial setup can use pre-printed barcodes or manual assignment. Can be added once core system is operational.

**Independent Test**: Can be tested by generating barcode PDFs for items and borrowers and verifying they scan correctly with barcode readers.

**Acceptance Scenarios**:

1. **Given** new items are cataloged without physical barcodes, **When** librarian selects items and chooses print barcodes, **Then** system generates printable PDF with barcodes in standard label format (e.g., Avery 5160)
2. **Given** new borrowers are registered, **When** librarian generates borrower ID cards, **Then** system creates printable PDF with borrower barcode, name, and class information
3. **Given** librarian has specific label sheet format, **When** configuring barcode printing, **Then** system allows selection of common label dimensions and layout
4. **Given** barcode is generated, **When** librarian prints and scans it, **Then** barcode correctly identifies the associated item or borrower
5. **Given** librarian needs to reprint lost barcode, **When** selecting existing record, **Then** system regenerates same barcode number for consistency

---

### Edge Cases

- What happens when barcode scanner fails or is unavailable? System must allow manual entry of barcode numbers as fallback.
- What happens when network connection to BNF SRU API is down? Continue with manual entry of bibliographic records.
- What happens when a borrower loses an item? System must allow marking item as lost and updating inventory.
- What happens when two borrowers have the same name? System must distinguish borrowers by unique borrower ID number.
- What happens when an item is damaged upon return? System must allow marking item condition and potentially removing from circulation.
- What happens when school year ends and all borrowers have items checked out? System must support bulk operations for year-end processing and mass renewals.
- What happens when trying to scan a barcode that doesn't exist in the system? System must clearly indicate unknown barcode and offer to create new record or cancel.
- What happens with reserved items when another borrower tries to check them out? System must enforce holds/reservations and prevent checkout by others.
- What happens when importing duplicate borrower records from CSV? System must detect duplicates and offer options: skip, update existing, or create with suffix.
- What happens when multiple items exist for same bibliographic record? System must track each item (copy) separately with unique barcodes.

## Requirements *(mandatory)*

### Functional Requirements

**Circulation Operations (Prêt/Retour)**

- **FR-001**: System MUST record circulation transactions (checkouts) with borrower ID, item ID, checkout date, and due date
- **FR-002**: System MUST process returns by scanning item barcode and updating circulation status to returned with return date
- **FR-003**: System MUST support barcode scanning as primary input method for borrower IDs and item barcodes
- **FR-004**: System MUST prevent checking out items that are already on loan to another borrower
- **FR-005**: System MUST display overdue item warnings when a borrower with overdue items attempts to check out new items
- **FR-006**: System MUST enforce configurable checkout limits per borrower (default: 2 items)
- **FR-007**: System MUST calculate due dates based on configurable loan period (default: 14 days)
- **FR-008**: System MUST support manual barcode entry as fallback when scanner is unavailable
- **FR-009**: System MUST allow configuring both checkout limits and loan duration in system settings

**Cataloging and ISBN Integration (Catalogage)**

- **FR-010**: System MUST retrieve bibliographic data from BNF SRU API using ISBN as lookup key in UNIMARC format
- **FR-011**: System MUST display retrieved bibliographic metadata including title, author(s), publisher, publication date, and subject categories
- **FR-012**: System MUST allow librarian to edit retrieved bibliographic information before saving to catalog
- **FR-013**: System MUST generate unique item barcode numbers for new items (exemplaires)
- **FR-014**: System MUST support manual bibliographic record entry when ISBN lookup fails or for non-ISBN materials
- **FR-015**: System MUST import bibliographic records from standard library formats (UNIMARC, MARC 21, CSV)
- **FR-016**: System MUST detect duplicate ISBNs and offer to add additional item (copy) instead of duplicate bibliographic record
- **FR-017**: System MUST maintain one bibliographic record per title with multiple item records (copies/exemplaires) linked to it

**Borrower Management (Gestion des Emprunteurs)**

- **FR-018**: System MUST store borrower records with name, borrower ID, role (student/teacher/staff), class (if applicable), grade level, and unique barcode
- **FR-019**: System MUST organize borrowers by class, grade level, and role for reporting and filtering
- **FR-020**: System MUST import borrower lists from CSV files with validation and error reporting
- **FR-021**: System MUST generate unique barcode numbers for each borrower
- **FR-022**: System MUST allow updating borrower information including class transfers
- **FR-023**: System MUST support marking borrowers as inactive while preserving historical circulation data
- **FR-024**: System MUST distinguish between active and inactive borrowers in searches and circulation operations
- **FR-025**: System MUST use borrower ID number as unique identifier to distinguish borrowers with same name

**Catalog Search and Discovery (Recherche)**

- **FR-026**: System MUST support searching bibliographic records by title, author, ISBN, subject, and item barcode
- **FR-027**: System MUST support partial text matching for title and author searches
- **FR-028**: System MUST display item availability status: available, on loan (with due date), lost, or damaged
- **FR-029**: System MUST show complete bibliographic details and all associated items when viewing a bibliographic record
- **FR-030**: System MUST allow filtering search results by availability status and subject category

**Circulation Statistics and Reporting (Statistiques)**

- **FR-031**: System MUST generate overdue items report organized by class, printable as one page per class
- **FR-032**: System MUST generate report showing bibliographic records with zero circulations in current academic year
- **FR-033**: System MUST generate most borrowed titles report showing top bibliographic records ranked by circulation count
- **FR-034**: System MUST allow filtering overdue report by specific class
- **FR-035**: System MUST track academic year boundaries for circulation statistics

**Barcode Printing (Impression de Codes-barres)**

- **FR-036**: System MUST generate printable barcode labels for items in standard label sheet formats
- **FR-037**: System MUST generate printable borrower ID cards with barcode, name, and class
- **FR-038**: System MUST support common label sheet sizes (e.g., Avery 5160, A4 labels)
- **FR-039**: System MUST produce barcodes in Code 39 or Code 128 format compatible with standard scanners
- **FR-040**: System MUST allow reprinting existing barcodes for lost or damaged labels

**Localization**

- **FR-041**: System MUST provide complete interface translation in English and French
- **FR-042**: System MUST format dates, numbers, and messages according to selected language locale
- **FR-043**: System MUST support language switching without data loss or system restart

**Data Management (Gestion des Données)**

- **FR-044**: System MUST use versioned database migrations for schema changes
- **FR-045**: System MUST paginate all list views and search results (50 items per page, max 100)
- **FR-046**: System MUST validate all barcode scans and display clear error messages for invalid or unknown barcodes
- **FR-047**: System MUST maintain audit trail of all circulation transactions
- **FR-048**: System MUST support backup and restore of complete library database
- **FR-049**: System MUST support clearing old data to prevent database from becoming too large
- **FR-050**: System MUST allow marking items as lost with inventory update
- **FR-051**: System MUST allow marking items as damaged with option to remove from circulation

### Key Entities

- **Borrower** (Emprunteur): Represents a library user (student, teacher, or staff member); attributes include unique borrower ID number, full name, role (student/teacher/staff), class assignment (if student), grade level (if student), barcode number, active/inactive status, contact information (for overdue notices), and current checkout count

- **Bibliographic Record** (Notice bibliographique): Represents the intellectual content/title in the library collection; attributes include ISBN (if applicable), title, author(s), publisher, publication year, subject categories, and summary/description. One bibliographic record can have multiple physical items (copies).

- **Item** (Exemplaire): Represents a physical copy of a bibliographic record; attributes include unique item barcode, reference to bibliographic record, copy number, physical condition status (available, on loan, damaged, lost), location/shelf information, and acquisition date. Each item is independently circulated.

- **Circulation Transaction** (Transaction de Prêt): Represents a checkout event linking a borrower to an item; attributes include borrower reference, item reference, bibliographic record reference (for reporting), checkout date, due date, return date (null if not yet returned), overdue flag, and renewal count

- **Class** (Classe): Represents an organizational unit for students; attributes include class name, grade level, academic year, and assigned teacher/homeroom

- **Hold/Reservation** (Réservation): Represents a borrower's request for an item currently on loan; attributes include borrower reference, bibliographic record reference, request date, notification status, and expiration date

- **System Settings** (Paramètres Système): Represents configurable parameters; attributes include checkout limit per borrower, loan duration in days, academic year start date, and barcode format preferences

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Librarian can complete a checkout transaction (scan borrower, scan 2 items, confirm) in under 30 seconds
- **SC-002**: Librarian can process a return transaction (scan 5 items) in under 20 seconds
- **SC-003**: Adding a new bibliographic record to the catalog using ISBN lookup takes less than 1 minute including item creation and confirmation
- **SC-004**: System supports 500 borrowers and 5,000 items without performance degradation
- **SC-005**: Search results appear within 2 seconds for queries on collection of 5,000 bibliographic records
- **SC-006**: Import of 100 borrower records from CSV file completes in under 30 seconds with validation report
- **SC-007**: System uptime exceeds 99% during school hours (8am-5pm on school days)
- **SC-008**: Users can complete common tasks (search, check availability, view circulation history) in under 3 clicks from main screen
- **SC-009**: Generated barcodes have 99.9% successful scan rate with standard barcode readers
- **SC-010**: System handles 500 circulation transactions per week without performance issues
- **SC-011**: System performs well for 1 full academic year with weekly data compaction
- **SC-012**: Data compaction operation completes in under 5 minutes and maintains system responsiveness
- **SC-013**: Overdue report for entire school (10-15 classes) generates in under 10 seconds

### Assumptions

- School has standard barcode scanners compatible with Code 39 or Code 128 formats
- Internet connection available for BNF SRU API access during cataloging (offline mode available for circulation operations)
- Librarian has basic computer literacy and can operate barcode scanner
- Library collection is primarily French-language materials cataloged in BNF database accessible via SRU API
- Borrower barcodes will be printed on ID cards or stickers that borrowers carry
- Library operates on standard 2-week loan period with 2-item checkout limit per borrower (both configurable)
- School uses class-based organization for students (grade levels divided into class sections)
- System will run on existing school computers (minimum: dual-core CPU, 4GB RAM, Windows/Linux)
- Barcode labels will be printed on standard label sheets using regular office printer
- Borrower and bibliographic/item records will be maintained across academic years with periodic data compaction
- Academic year runs approximately 36 weeks with ~500 circulation transactions per week (~18,000 transactions per year)
- BNF SRU API returns bibliographic data in UNIMARC format (UnimarcXchange)
