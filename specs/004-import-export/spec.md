# Feature Specification: Library Data Import/Export with Standards Compatibility

**Feature Branch**: `004-import-export`
**Created**: 2026-02-06
**Status**: Draft
**Input**: User description: "Create specification for library data import/export with BCDI and international standards compatibility"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export Borrowers for Data Migration (Priority: P1)

A librarian needs to export all borrower (student) data to a CSV file for backup, migration to another system, or integration with the school's administrative system. The librarian selects export filters (all borrowers, specific class, active only, or blocked only), chooses which fields to include, and downloads a CSV file that is compatible with BCDI and other French school library systems.

**Why this priority**: Data export is the most critical missing feature. Without it, librarians cannot backup data, migrate to other systems, or integrate with school administrative databases. This is a blocker for schools considering adoption and a compliance requirement for data portability.

**Independent Test**: Can be fully tested by exporting borrowers to CSV, opening in Excel/LibreOffice, and verifying all data is present and correctly formatted. Re-importing the file into a fresh BCD instance should recreate all borrowers without data loss.

**Acceptance Scenarios**:

1. **Given** librarian is on borrowers page, **When** they click "Export Borrowers" button, **Then** system displays export dialog with filter options (class, role, active status)
2. **Given** librarian selects "Export all active students in class CP-A", **When** they click "Download CSV", **Then** system generates CSV file with borrower_id, first_name, last_name, class_name, role, active, date_of_birth, gender columns
3. **Given** exported CSV contains 50 borrowers, **When** librarian opens file in Excel, **Then** all French characters (é, è, à) display correctly (UTF-8 encoding)
4. **Given** librarian exports borrowers with BCDI-compatible format option selected, **When** CSV is generated, **Then** column headers match BCDI standard (StudentID, FirstName, LastName, Class, Role, Active)
5. **Given** librarian exports 500 borrowers, **When** download completes, **Then** file size is under 1MB and downloads in under 3 seconds
6. **Given** librarian selects "Include all fields" option, **When** CSV is generated, **Then** file includes email, phone, notes, blocked_reason, and class_name columns
7. **Given** librarian exports blocked borrowers only, **When** filter applied, **Then** CSV contains only borrowers where active=false and includes blocked_reason column

---

### User Story 2 - Export Catalog for External Systems (Priority: P1)

A librarian needs to export bibliographic records and items from the catalog to share with other library systems, create backups, or submit to regional library catalogs. The librarian chooses export format (Dublin Core standard or BCDI-native), applies filters (category, availability, date range), and downloads a CSV file with both bibliographic metadata and item inventory data.

**Why this priority**: Catalog export enables interoperability with BCDI (used by 80% of French school libraries) and international systems. Without this, the BCD system becomes a data silo, blocking adoption by schools that need to share catalog data with regional networks.

**Independent Test**: Export catalog to Dublin Core CSV, validate against Dublin Core metadata schema, and verify re-import creates identical records. Export to BCDI format and verify compatibility with Canopé's BCDI import tool.

**Acceptance Scenarios**:

1. **Given** librarian is on catalog page, **When** they click "Export Catalog" button, **Then** system displays export dialog with format choice (Dublin Core, BCDI-native, Simple CSV)
2. **Given** librarian selects "Dublin Core" format and clicks export, **When** CSV is generated, **Then** file includes columns: dc.title, dc.identifier, dc.creator, dc.subject, dc.publisher, dc.date, dc.type, dc.language, item.id, item.callNumber
3. **Given** catalog has 1000 bibliographic records with 1200 items, **When** librarian exports to Dublin Core, **Then** CSV has 1200 rows (one per item) with bibliographic data repeated for multiple copies
4. **Given** librarian exports with BCDI-native format, **When** CSV is generated, **Then** column headers match BCDI standard (ISBN, Titre, Auteur, Editeur, Annee, Support, Inventaire, Cote, Date achat)
5. **Given** librarian filters by "Available items only" before export, **When** export completes, **Then** CSV contains only items with status="available"
6. **Given** librarian exports catalog with special characters (œ, ç, é in French titles), **When** file opened in Excel, **Then** all characters display correctly (UTF-8 encoding verified)
7. **Given** catalog has hybrid medium types ("Livre CD-Audio"), **When** exported to BCDI format, **Then** Support column contains "Livre-CD" (BCDI-compatible variant)

---

### User Story 3 - Import Borrowers with Flexible Mapping (Priority: P2)

A librarian needs to import student data from the school's administrative system or BCDI export into BCD. The source CSV may use different column names, terminology, or value formats. The system provides intelligent mapping (auto-detection of common variations) and allows librarian to review/correct mappings before import. Import handles missing optional fields gracefully and reports errors clearly.

**Why this priority**: Import flexibility is essential for adoption. Schools export from various systems (Pronote, BCDI, Excel rosters) with different formats. Without fuzzy matching, librarians must manually reformat CSV files, creating friction and errors.

**Independent Test**: Import borrowers from BCDI export (French column names), Pronote export (different role values), and Excel roster (minimal fields). Verify all three succeed with auto-detected mappings and produce identical database records.

**Acceptance Scenarios**:

1. **Given** librarian uploads CSV with columns "StudentID, FirstName, LastName, Class", **When** import wizard opens, **Then** system auto-maps StudentID→borrower_id, FirstName→first_name, LastName→last_name, Class→class_name
2. **Given** CSV contains role value "élève" (French for student), **When** import processes rows, **Then** system maps "élève" to "student" using built-in translation table
3. **Given** CSV has column "Date de naissance" (French), **When** import wizard displays mapping preview, **Then** system auto-detects and maps to date_of_birth field
4. **Given** CSV contains class name "CP A" (space) but database has "CP-A" (hyphen), **When** import processes row, **Then** system uses fuzzy matching to find correct class
5. **Given** CSV missing optional columns (email, phone, date_of_birth), **When** import executes, **Then** system creates borrowers successfully with NULL values for missing fields
6. **Given** CSV row has invalid borrower_id (empty), **When** import processes row, **Then** system skips row, logs error "Row 5: Missing required field 'borrower_id'", continues processing other rows
7. **Given** CSV contains 200 borrowers and 5 have duplicate IDs, **When** import completes, **Then** system displays summary "195 imported, 5 skipped (duplicates)" with clickable error details
8. **Given** CSV has gender values "M/F" but some rows have "Masculin/Féminin", **When** import processes, **Then** system normalizes both formats to "M/F" using fuzzy matching

---

### User Story 4 - Import Catalog with Medium Type Normalization (Priority: P2)

A librarian needs to import bibliographic records from BCDI, another BCD instance, or external catalog sources. The source CSV may use different medium type terminology (e.g., "Book" vs "Livre", "CD-Audio" vs "CD"). The system normalizes medium types to generic English codes using a configurable mapping table and displays mapping preview before import. Invalid types default to "other" with warnings.

**Why this priority**: Medium type incompatibility is the #1 cause of catalog import failures (60-80% failure rate without normalization). French libraries use BCDI exports with formats like "DVD-vidéo", "Livre-CD", which must map to generic database codes. Configurable mappings allow schools to handle custom formats without code changes.

**Independent Test**: Import catalogs from BCDI export (French medium types), Dublin Core export (English types), and UNIMARC export (French descriptive types). Verify all succeed with auto-normalized medium types mapping to generic codes (book, cd, dvd) with no rejected rows.

**Acceptance Scenarios**:

1. **Given** librarian uploads Dublin Core CSV with dc.type="Book", **When** import processes row, **Then** system maps "Book" → code:"book" using mapping table (database stores generic "book", UI displays localized "Livre" in French)
2. **Given** CSV contains dc.type="CD-Audio" (BCDI format), **When** import processes, **Then** system maps "CD-Audio" → code:"cd" and logs info "Normalized medium type: CD-Audio → cd"
3. **Given** CSV has medium type "Livre CD-Audio", **When** import wizard displays preview, **Then** system shows mapping "Livre CD-Audio → audiobook" and highlights as auto-detected
4. **Given** CSV contains unknown medium type "Kit pédagogique", **When** import processes, **Then** system maps to code:"other" and logs warning "Row 12: Unknown medium type 'Kit pédagogique' defaulted to 'other' - consider adding to mapping table"
5. **Given** CSV has mixed English/French types ("Book", "Livre", "DVD"), **When** import completes, **Then** all normalize correctly to generic codes (book, book, dvd) and import succeeds
6. **Given** librarian reviews mapping preview before import, **When** they see "E-Book → other", **Then** they can manually override mapping to code:"ebook" before confirming import
7. **Given** BCDI export with Support="Enregistrement sonore", **When** import processes, **Then** system maps to code:"cd" using BCDI-specific mapping rule

---

### User Story 5 - Round-Trip Import/Export Validation (Priority: P3)

A librarian needs to verify data integrity by exporting data, modifying it externally, and re-importing. The system ensures round-trip fidelity (export → import → export produces identical CSV) and provides validation tools to detect data loss or corruption.

**Why this priority**: Round-trip capability ensures data portability and trustworthiness. Librarians need confidence that exported data can be safely edited in Excel and re-imported without silent data loss.

**Independent Test**: Export 100 borrowers → modify 10 rows in Excel → re-import → verify changes applied correctly and unmodified rows unchanged. Export catalog → import to fresh database → export again → verify byte-identical CSV (excluding timestamps).

**Acceptance Scenarios**:

1. **Given** librarian exports 100 borrowers to CSV, **When** they re-import same file without changes, **Then** system reports "100 skipped (duplicates), 0 imported" (no duplicate creation)
2. **Given** librarian exports catalog, edits 5 titles in Excel, and re-imports, **When** import completes, **Then** system updates 5 existing records and reports "5 updated, 0 new"
3. **Given** librarian exports borrowers with all fields, **When** they compare exported CSV to database data, **Then** all field values match exactly (no truncation, encoding issues, or NULL vs empty string differences)
4. **Given** librarian exports catalog in Dublin Core format and re-imports, **When** comparing original and re-imported records, **Then** multi-valued fields (authors, keywords) preserve order and values
5. **Given** export includes date fields (date_of_birth, acquisition_date), **When** re-imported, **Then** dates parse correctly regardless of locale (handles both DD/MM/YYYY and YYYY-MM-DD formats)

---

### User Story 6 - Configure Medium Types and Import Mappings (Priority: P2)

A librarian or system administrator needs to customize the list of material types supported by their library (e.g., add "Educational Kit", "Game", "Software") and configure how imported CSV data maps to these types. The admin accesses a settings page to add/edit/deactivate medium types and manage import mapping rules without requiring code changes or technical support.

**Why this priority**: Different schools have different collections. A Montessori school may need "Manipulative" type, a bilingual school may need "Dual-Language Book", and a technology-focused school may need "Robotics Kit". Hardcoded types force all schools into same taxonomy. Configurable types enable customization while maintaining data integrity.

**Independent Test**: Admin adds new medium type "Educational Kit" with French translation "Kit pédagogique", creates import mapping "Kit pédagogique" → "educational_kit", imports BCDI CSV with that type, verifies it maps correctly and displays localized name in French UI.

**Acceptance Scenarios**:

1. **Given** admin is on settings page, **When** they click "Manage Medium Types" tab, **Then** system displays list of active medium types with columns: Code, English Name, French Name, Active Status
2. **Given** admin clicks "Add Medium Type" button, **When** they enter code:"educational_kit", display_name_en:"Educational Kit", display_name_fr:"Kit pédagogique", **Then** system validates code is unique and alphanumeric, saves new type, displays success message
3. **Given** system ships with default types (book, audiobook, cd, dvd, periodical, ebook, other), **When** fresh installation occurs, **Then** database pre-populates these 9 default types with English and French translations
4. **Given** admin deactivates medium type "VHS" (legacy format), **When** they toggle active status to false, **Then** system hides type from UI dropdowns but preserves existing catalog records using that type
5. **Given** admin is on "Import Mappings" tab, **When** they click "Add Mapping", **Then** system displays form with fields: Source Value (e.g., "Livre-CD"), Target Medium Type (dropdown of active types)
6. **Given** admin adds mapping "Livre-CD" → "audiobook", **When** librarian imports CSV with "Livre-CD" values, **Then** system automatically maps to code:"audiobook" without manual intervention
7. **Given** admin views mapping table sorted by target type, **When** they filter by "book" type, **Then** system displays all source variations: "Book", "Livre", "Texte imprimé", "livre", "BOOK" (case-insensitive)
8. **Given** librarian using French UI views catalog, **When** they see item with medium_type_code:"book", **Then** system displays "Livre" (not "Book") using i18n translation from display_name_fr column
9. **Given** admin deletes medium type that has existing catalog items, **When** they attempt delete, **Then** system displays error "Cannot delete medium type 'VHS' - 12 items still use this type. Deactivate instead or reassign items first"

---

### Edge Cases

- What happens when CSV file is empty (zero rows)? System displays error "CSV file is empty, no data to import" and prevents import.
- What happens when CSV has only header row (no data rows)? System displays warning "CSV contains headers but no data rows" and cancels import.
- What happens when CSV file exceeds 10MB (10,000+ records)? System displays progress bar during import and processes in batches to avoid memory issues.
- What happens when CSV contains malformed UTF-8 (encoding errors)? System attempts auto-detection (UTF-8, Latin-1, Windows-1252) and prompts user to select encoding if detection fails.
- What happens when CSV has duplicate column headers? System displays error "Duplicate column name 'FirstName' at columns 3 and 5" and prevents import.
- What happens when exported file name conflicts with existing download? Browser adds (1), (2) suffix automatically; system uses timestamp in filename to reduce collisions (e.g., borrowers_2026-02-06_143022.csv).
- What happens when librarian cancels import mid-process? System rolls back transaction (no partial imports) and displays "Import cancelled, no changes made".
- What happens when CSV has more columns than expected? System ignores unmapped columns and logs warning "Unknown columns ignored: Column1, Column2".
- What happens when date values use ambiguous format (01/02/2025 - could be Jan 2 or Feb 1)? System uses locale-based parsing (FR locale assumes DD/MM/YYYY) and displays warning if ambiguous.
- What happens when CSV has row with extra commas (field count mismatch)? CSV parser handles extra commas as empty fields; if beyond expected columns, ignores trailing empty values.
- What happens when medium type normalization has multiple possible matches? System uses first match in priority order (exact > partial > fuzzy) and logs decision "Ambiguous type 'Audio' matched to code 'cd' (priority 1)".
- What happens when class name in CSV doesn't exist in database? System creates borrower with class_id=NULL and logs warning "Row 15: Class 'CP-C' not found, borrower created without class assignment".
- What happens when admin adds medium type with duplicate code? System displays validation error "Code 'book' already exists. Choose a unique code." and prevents save.
- What happens when admin tries to add medium type code with spaces or special characters? System displays validation error "Code must be alphanumeric lowercase with underscores only (e.g., 'educational_kit')" and prevents save.
- What happens when admin deactivates medium type but catalog has items using it? System allows deactivation (items retain inactive type) but hides type from UI dropdowns for new items.
- What happens when admin adds import mapping with source value that already exists? System displays error "Mapping for 'Livre' already exists → book. Delete existing mapping first or choose different source value."
- What happens when export to BCDI format encounters medium type with no French translation? System uses English display name as fallback and logs warning "Medium type 'robotics_kit' has no French translation, using English 'Robotics Kit' in BCDI export".
- What happens when database has medium_type_code="book" but medium_types table is missing that row? System displays error "Invalid medium type reference 'book' - database integrity issue" and prevents catalog display until admin restores missing type.
- What happens when admin imports medium types configuration from another school? System provides import/export for medium_types and medium_type_mappings tables via CSV (admin feature for sharing configurations).

## Requirements *(mandatory)*

### Functional Requirements

**Export Core Functionality**

- **FR-001**: System MUST provide "Export" button on borrowers list page that opens export configuration dialog
- **FR-002**: System MUST provide "Export" button on catalog search page that opens export configuration dialog
- **FR-003**: Export dialog MUST offer format selection: "Standard CSV" (BCD native), "BCDI-compatible", "Dublin Core" (catalog only)
- **FR-004**: System MUST allow filtering export data by: class (borrowers), category/medium type (catalog), active status (borrowers), availability status (catalog)
- **FR-005**: System MUST generate CSV files with UTF-8 encoding and BOM (Byte Order Mark) for Excel compatibility
- **FR-006**: System MUST include column headers in first row of exported CSV files
- **FR-007**: System MUST escape special characters in CSV fields (commas, quotes, newlines) using RFC 4180 standard
- **FR-008**: System MUST generate unique filenames with timestamp format: borrowers_YYYY-MM-DD_HHMMSS.csv
- **FR-009**: System MUST complete export of 1000 records in under 5 seconds for responsive user experience

**Borrower Export Fields**

- **FR-010**: Borrower export MUST include mandatory fields: borrower_id, first_name, last_name, class_name, role, active
- **FR-011**: Borrower export MUST include optional fields when "Include all fields" selected: email, phone, notes, blocked_reason, date_of_birth, gender
- **FR-012**: Borrower export in BCDI-compatible format MUST use column headers: StudentID, FirstName, LastName, Class, Role, Active, DateOfBirth, Gender (matching BCDI standard)
- **FR-013**: Borrower export MUST include class_name (text) instead of class_id (foreign key) for readability and portability
- **FR-014**: Borrower export MUST format boolean values as "true/false" (lowercase) for standard CSV compatibility

**Catalog Export Fields**

- **FR-015**: Catalog export in Dublin Core format MUST include fields: dc.title, dc.identifier, dc.creator, dc.subject, dc.description, dc.publisher, dc.contributor, dc.date, dc.type, dc.format, dc.language, dc.source, dc.relation, dc.coverage, dc.rights
- **FR-016**: Catalog export MUST include item extensions: item.id, item.callNumber, item.acquisitionDate, item.fundingSource
- **FR-017**: Catalog export in BCDI-native format MUST use column headers: ISBN, Titre, Auteur, Illustrateur, Editeur, Annee, Support, Inventaire, Cote, Date achat, Empruntable
- **FR-018**: Catalog export MUST create one CSV row per item (physical copy), repeating bibliographic data for multiple copies of same title
- **FR-019**: Catalog export MUST format multi-valued fields (authors, keywords) as pipe-separated values (e.g., "Author 1|Author 2|Author 3")
- **FR-020**: Catalog export in BCDI format MUST reverse-map generic medium type codes to French display names using medium_types table: code:"book" → "Livre", code:"audiobook" → "Livre CD", code:"periodical" → "Périodique" (uses display_name_fr column)

**Import Core Functionality**

- **FR-021**: System MUST provide "Import" button on borrowers list page that opens file upload dialog
- **FR-022**: System MUST provide "Import" button on catalog page that opens file upload dialog
- **FR-023**: System MUST accept CSV files with .csv extension and reject other file types with clear error message
- **FR-024**: System MUST auto-detect CSV delimiter (comma, semicolon, tab) using first 1KB of file content
- **FR-025**: System MUST auto-detect character encoding (UTF-8, Latin-1, Windows-1252) and display detected encoding to user
- **FR-026**: Import wizard MUST display column mapping preview showing: detected column → target field mappings with confidence level (exact/fuzzy/unmapped)
- **FR-027**: Import wizard MUST allow manual override of auto-detected column mappings via dropdown selection
- **FR-028**: System MUST validate all required fields present before allowing import execution (borrowers: borrower_id, first_name, last_name; catalog: dc.title, item.id)
- **FR-029**: System MUST process import in transaction (all-or-nothing for database integrity) but log individual row errors for partial success reporting
- **FR-030**: System MUST display import progress bar with percentage complete and estimated time remaining for files with 100+ rows

**Medium Type Taxonomy (Database Schema)**

- **FR-031**: System MUST store medium types in database table `medium_types` with columns: id (primary key), code (unique, alphanumeric lowercase with underscores), display_name_en (English label), display_name_fr (French label), active (boolean), created_at, updated_at
- **FR-032**: System MUST store import mappings in database table `medium_type_mappings` with columns: id (primary key), medium_type_id (foreign key to medium_types), source_value (case-insensitive unique), priority (integer for conflict resolution), created_at
- **FR-033**: System MUST ship with default medium types pre-populated on fresh installation: book, audiobook, cd, dvd, periodical, ebook, software, educational_kit, other (9 default types with English and French translations)
- **FR-034**: System MUST ship with default import mappings pre-populated for BCDI compatibility: "Livre/livre/Book/book/Texte imprimé" → code:"book", "CD-Audio/CD audio/Audio CD/Enregistrement sonore" → code:"cd", "DVD-vidéo/DVD Video/Image animée" → code:"dvd", "Livre CD/Livre-CD/Livre CD-Audio/Audiobook" → code:"audiobook", "Périodique/Revue/Periodical/Magazine" → code:"periodical", "Autre/Other" → code:"other"
- **FR-035**: Bibliographic records table MUST store medium type as foreign key reference to medium_types.id (NOT hardcoded enum string) and display via JOIN to get localized display_name based on user's interface language
- **FR-036**: System MUST prevent deletion of medium types that have existing bibliographic records (foreign key constraint) and display error message with count of affected records
- **FR-037**: System MUST allow deactivation of medium types (active=false) to hide from UI dropdowns while preserving historical data integrity for existing catalog items

**Medium Type Administration UI**

- **FR-038**: System MUST provide admin page "Settings → Medium Types" with tabs: "Medium Types" (list all types), "Import Mappings" (configure source value mappings)
- **FR-039**: Medium Types tab MUST display table with columns: Code, English Name, French Name, Active Status, Item Count (number of bibliographic records using this type), Actions (Edit, Deactivate/Activate, Delete)
- **FR-040**: Admin MUST be able to add new medium type via form with fields: Code (validated alphanumeric lowercase with underscores), English Name, French Name, Active (default true)
- **FR-041**: Admin MUST be able to edit medium type display names (English and French) but NOT code (code is immutable to preserve database referential integrity)
- **FR-042**: Import Mappings tab MUST display table with columns: Source Value, Target Medium Type (with localized name), Priority, Actions (Edit, Delete)
- **FR-043**: Admin MUST be able to add import mapping via form with fields: Source Value (case-insensitive), Target Medium Type (dropdown of active types), Priority (default 1)
- **FR-044**: System MUST validate import mapping source values are unique (case-insensitive) and display error "Mapping for 'Livre' already exists" if duplicate detected
- **FR-045**: Admin MUST be able to export/import medium types and mappings configuration as CSV files for sharing between schools or backup purposes

**Import Column Mapping & Normalization**

- **FR-046**: System MUST auto-detect common column name variations using case-insensitive fuzzy matching: "StudentID/borrower_id/ID/Student ID" → borrower_id
- **FR-047**: System MUST normalize borrower role values using translation table: "élève/student/étudiant" → "student", "enseignant/teacher/professeur" → "teacher", "personnel/staff" → "staff"
- **FR-048**: System MUST normalize class names using fuzzy matching: "CP A" (space) matches "CP-A" (hyphen), case-insensitive comparison
- **FR-049**: System MUST normalize medium type values using medium_type_mappings table by querying source_value (case-insensitive match) and returning mapped medium_type_id
- **FR-050**: Medium type import normalization MUST try exact match first, then case-insensitive match, then partial substring match (in priority order), and default to code:"other" if no match found with warning logged
- **FR-051**: System MUST display medium type mapping preview during import wizard showing: "Source Value → Mapped Type (code:display_name)" for librarian review before final import
- **FR-052**: System MUST allow manual override of auto-detected medium type mapping during import wizard via dropdown selector of all active medium types
- **FR-053**: System MUST normalize date formats accepting: YYYY-MM-DD (ISO), DD/MM/YYYY (French), MM/DD/YYYY (US), and display warning for ambiguous dates
- **FR-054**: System MUST normalize boolean values accepting: "true/false", "1/0", "yes/no", "oui/non", "active/actif", "True/False" (case-insensitive)
- **FR-055**: System MUST trim whitespace from all field values before validation and storage

**Import Validation & Error Handling**

- **FR-056**: System MUST validate row-by-row and collect all errors before displaying summary (do not stop at first error)
- **FR-057**: System MUST skip rows with missing required fields and log error with row number and missing field name
- **FR-058**: System MUST skip duplicate records (matching borrower_id or item_id) and count as "skipped" (not errors) with warning message
- **FR-059**: System MUST display import summary with counts: "X imported, Y skipped (duplicates), Z errors" and expandable error details section
- **FR-060**: Error details MUST show row number, error type, and specific error message for each failed row (e.g., "Row 15: Invalid date format '32/13/2025' for date_of_birth")
- **FR-061**: System MUST allow librarian to download error log as CSV file with columns: row_number, error_type, field_name, invalid_value, error_message
- **FR-062**: System MUST limit import to 10,000 rows per file to prevent memory exhaustion and recommend batch imports for larger datasets
- **FR-063**: System MUST rollback database transaction if critical error occurs (file corruption, database connection loss) and display "Import failed, no changes made" message

**Data Integrity & Round-Trip Validation**

- **FR-064**: Export followed by immediate import with no modifications MUST result in 100% "skipped (duplicates)" and 0 new records created
- **FR-065**: Export MUST preserve all field values exactly (no truncation, encoding corruption, or lossy conversions) for round-trip fidelity
- **FR-066**: System MUST handle NULL vs empty string consistently: export NULL as empty CSV field, import empty field as NULL (not empty string)
- **FR-067**: Multi-valued fields (authors, keywords) exported with pipe separator MUST import with identical ordering and whitespace preservation
- **FR-068**: Date fields exported in ISO format (YYYY-MM-DD) MUST import correctly regardless of system locale settings
- **FR-069**: Special characters (French accents: é, è, à, ç, œ) MUST survive round-trip without corruption using UTF-8 encoding
- **FR-070**: Medium type codes MUST survive round-trip: export code:"book" → import maps back to same code:"book" (not variant like "Livre")

**User Interface Requirements**

- **FR-071**: Export dialog MUST display estimated file size and record count before download
- **FR-072**: Import wizard MUST display sample data preview (first 5 rows) after file upload for visual validation
- **FR-073**: Import mapping screen MUST highlight unmapped required fields in red with warning "Required field not mapped"
- **FR-074**: Import confirmation screen MUST display summary: "Ready to import X borrowers/records. Y duplicates will be skipped. Continue?"
- **FR-075**: Export and import operations MUST display success notification with download link (export) or import summary (import)
- **FR-076**: Import error summary MUST provide "Try Again" button to re-upload corrected CSV without losing format settings

### Key Entities

- **Medium Type**: Represents a material format category in the library collection; includes unique code (alphanumeric identifier like "book", "audiobook"), English display name, French display name, active status (for UI filtering), and audit timestamps. Stored in database, NOT hardcoded enum.

- **Medium Type Mapping**: Represents a rule for normalizing import data to standard medium type codes; includes source value (e.g., "Livre", "CD-Audio"), target medium type reference, priority (for resolving conflicts when multiple rules match same source), and audit timestamps. Enables BCDI/Dublin Core compatibility without code changes.

- **CSV Export Configuration**: Represents user-selected export settings; includes format choice (Standard/BCDI/Dublin Core), filters (class, category, status), field selection (all fields vs minimal), output filename, and estimated record count

- **CSV Import Session**: Represents an import operation in progress; includes uploaded file metadata (filename, size, encoding), detected column mappings, validation results (errors per row), and import summary statistics (imported, skipped, errors)

- **Column Mapping**: Represents the relationship between CSV column name and target database field; includes source column name, target field name, mapping confidence level (exact/fuzzy/manual), and normalization rule applied (if any)

- **Import Error**: Represents a validation failure for a specific CSV row; includes row number, error type (missing required field, invalid format, duplicate, constraint violation), field name, invalid value, and suggested correction (if available)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Librarian can export 500 borrowers to CSV file and download in under 5 seconds
- **SC-002**: Librarian can export 1000 catalog records (1200 items) to Dublin Core CSV and download in under 10 seconds
- **SC-003**: Exported CSV files open correctly in Microsoft Excel and LibreOffice Calc with all French characters (é, è, à, ç) displaying without corruption
- **SC-004**: Librarian can import 200 borrowers from BCDI export (French column names) with 100% auto-detected column mappings and zero manual corrections
- **SC-005**: Catalog import from Dublin Core CSV with mixed medium types ("Book", "CD-Audio", "Livre") achieves 100% normalization success rate with zero rejected rows
- **SC-006**: Round-trip test (export 100 borrowers → modify 10 in Excel → re-import) completes with 10 updated, 90 skipped, 0 errors in under 30 seconds total
- **SC-007**: Import validation catches 95% of common errors (missing required fields, invalid dates, duplicate IDs) and displays specific row-level error messages
- **SC-008**: Librarian can complete full export → edit → import workflow without technical support or documentation in under 10 minutes (measured via user testing)
- **SC-009**: System handles CSV files up to 10,000 rows (typical large school size) without memory errors or browser freezing
- **SC-010**: Import error rate for real-world BCDI exports from French schools is under 5% (measured via compatibility testing with sample exports from 10 schools)
- **SC-011**: Export format compatibility: BCDI-format exports successfully import into Canopé BCDI software with zero errors (verified via integration testing)
- **SC-012**: 90% of import sessions complete without requiring manual column mapping overrides (measured via analytics tracking auto-detection success rate)
- **SC-013**: Admin can add new medium type ("Educational Kit") with translations, create 3 import mappings, and verify import works end-to-end in under 5 minutes
- **SC-014**: Database stores medium types as generic English codes (book, cd, dvd) while UI displays localized French names (Livre, CD, DVD) with zero hardcoded French strings in database
- **SC-015**: Migration of existing French data (data folder with "Livre", "Périodique" values) to generic codes completes with 100% success rate using import mappings

### Assumptions

- Schools have existing borrower data in CSV format exported from administrative systems (Pronote, BCDI, Excel) or provided by school administration
- Librarians are familiar with basic spreadsheet operations (Excel, LibreOffice) and understand CSV file concept
- BCDI software is the dominant library system in French elementary schools (80% market share) and interoperability is critical for adoption
- Dublin Core metadata standard is used by international library systems and regional catalog networks for data exchange
- CSV delimiter auto-detection works for 95%+ of files; manual delimiter selection fallback acceptable for edge cases
- Character encoding auto-detection (UTF-8, Latin-1, Windows-1252) covers 99% of French school exports; other encodings rare enough to require manual specification
- Librarians tolerate up to 5% import error rate for noisy real-world data as long as errors are clearly reported and fixable
- Round-trip fidelity (export → import lossless) is mandatory for data backup and migration use cases
- Medium type vocabulary differs significantly between systems; configurable mapping table is essential (hardcoded enums would fail 60-80% of imports and block customization)
- Schools may have 10-5000 borrowers and 500-10,000 catalog items; performance must scale to upper bound
- Librarians prefer web-based import wizard over command-line tools; multi-step wizard (upload → preview → map → confirm → import) is acceptable workflow
- Export file size for typical school (1000 borrowers, 5000 items) will be under 2MB; browser download handling sufficient (no server-side compression needed)
- Import/export operations are infrequent (weekly backups, annual migrations); sub-second performance not critical, 5-10 second latency acceptable
- French schools require both English and French interface language support for import/export labels and error messages
- Database schema uses generic English codes for medium types (language-agnostic) with localized display names stored separately for i18n compliance
- Admin users have sufficient technical literacy to manage medium type configuration (add types, create mappings) via web UI without command-line access
- Default medium types (9 types: book, audiobook, cd, dvd, periodical, ebook, software, educational_kit, other) cover 95% of French elementary school collections
- Schools requiring custom medium types (games, manipulatives, robotics kits) represent <20% of user base but customization capability is critical for these adopters
- Existing BCD installations have French medium type data in database that must be migrated to generic codes via one-time migration script
- Medium type mappings table can grow to 100+ entries (covering BCDI, UNIMARC, Dublin Core, Koha variants) without performance degradation
