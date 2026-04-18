# Feature Specification: CSV Import/Export for Catalog and Borrowers

**Feature Branch**: `005-csv-import`
**Created**: 2026-02-06
**Updated**: 2026-02-06
**Status**: Draft
**Input**: CSV import/export with Dublin Core standard format for catalog (bibliographic records) and standardized CSV format for borrowers (students, teachers, staff). Includes conversion scripts for BCDI compatibility. Medium types stored as plain text without normalization.

## Clarifications

### Session 2026-02-06

- Q: FR-005 states "dc.title and dc.identifier minimum" but existing implementation validates "dc.title AND (dc.identifier OR item.id)". Which validation rule is correct for CSV import? → A: Require dc.title AND at least one identifier (dc.identifier OR item.id) - matches existing implementation
- Q: How should performance targets SC-001 (5s export) and SC-002 (10s import) be validated during development? → A: Performance targets are aspirational goals (no formal automated validation required)
- Q: What does "successfully converts" mean for SC-005 (BCDI conversion from 3 French schools)? → A: Success = >95% of rows converted without errors (allow some failures for malformed data)
- Q: What happens when a CSV row has dc.title but BOTH dc.identifier (ISBN) AND item.id (inventory number) are empty? → A: Reject the row with validation error (both identifiers missing = invalid)
- Q: When multiple CSV rows have the same ISBN (dc.identifier), how should they be imported? → A: Create ONE bibliographic record (notice) and MULTIPLE items (exemplaires) - one item per row with unique item.id
- Q: How should SC-006 (90%+ column detection accuracy) be measured for French CSV conversion? → A: SC-006 is aspirational goal (no formal validation needed)
- Q: What barcode format should be auto-generated for borrowers without barcodes? → A: Sequential numeric with prefix (e.g., "BCD000001", "BCD000002")
- Q: Should class name matching be case-sensitive or case-insensitive during borrower import? → A: Normalize on import - convert all class names to uppercase before matching
- Q: When some CSV rows fail validation, should successful rows be committed to the database? → A: Commit successful rows, report failures - partial import succeeds with warnings
- Q: What information should be included in error messages for failed CSV rows? → A: Row number, field name, error reason (e.g., "Row 15: missing required field 'first_name'")
- Q: How should conversion scripts detect the CSV delimiter when data contains separator characters? → A: Require explicit --delimiter flag - no auto-detection, user specifies delimiter

## User Scenarios & Testing

### User Story 1 - Export Catalog to CSV (Priority: P1)

Librarians need to export their catalog for backup, sharing with other schools, or migration to other systems. The export must preserve all data in a standard, widely-recognized format.

**Why this priority**: Core functionality for data portability and backup. Schools must be able to get their data out at any time.

**Independent Test**: Can be fully tested by creating sample catalog records, clicking export, downloading CSV, and verifying all fields are present and correctly formatted.

**Acceptance Scenarios**:

1. **Given** catalog has 250 bibliographic records, **When** librarian clicks "Export Catalog", **Then** system downloads CSV file with all 250 records in Dublin Core format
2. **Given** catalog has French characters (é, è, à, ç), **When** librarian exports and reopens in Excel, **Then** all French characters display correctly (UTF-8 encoding preserved)
3. **Given** catalog has records with missing optional fields (publisher, dewey_decimal), **When** librarian exports, **Then** CSV includes empty columns for missing fields without errors

---

### User Story 2 - Import Catalog from Dublin Core CSV (Priority: P1)

Librarians need to import catalog data from other systems, previous backups, or bulk data entry done in Excel. The import must accept standard Dublin Core CSV format.

**Why this priority**: Essential for initial setup, data migration, and bulk updates. Without import, users would need to manually enter hundreds of records.

**Independent Test**: Can be tested by preparing a Dublin Core CSV file (using template), uploading via web UI, and verifying records appear in catalog with correct values.

**Acceptance Scenarios**:

1. **Given** librarian has Dublin Core CSV with 100 records, **When** they upload file via web UI, **Then** system imports all 100 records successfully
2. **Given** CSV file has 5 records with missing ISBN (dc.identifier empty) but valid item.id values, **When** librarian imports, **Then** system imports all records successfully (item.id satisfies identifier requirement)
3. **Given** CSV file has 2 records with dc.title but BOTH dc.identifier AND item.id empty, **When** librarian imports, **Then** system rejects those 2 rows and shows error: "2 rows rejected: missing required identifier (dc.identifier or item.id required)"
4. **Given** CSV file has incorrect column names (e.g., "Title" instead of "dc.title"), **When** librarian uploads, **Then** system shows error: "Expected Dublin Core format. Columns found: [list]. Expected: dc.identifier, dc.title, etc. Use conversion scripts for non-Dublin Core files."

---

### User Story 3 - Convert BCDI Export to Dublin Core (Priority: P2)

French schools using BCDI library software need to migrate their data to BCD. BCDI exports use French column names (ISBN, Titre, Auteur, Support, Cote) and Windows-1252 encoding.

**Why this priority**: BCDI is the dominant French school library system (80% market share). Supporting BCDI conversion is essential for French market adoption.

**Independent Test**: Can be tested by obtaining sample BCDI export, running conversion script, and verifying output matches Dublin Core format with correct encoding.

**Acceptance Scenarios**:

1. **Given** librarian has BCDI export with columns "ISBN,Titre,Auteur,Support,Cote", **When** they run `python scripts/convert/bcdi_to_dublin_core.py bcdi_export.csv catalog.csv`, **Then** script creates Dublin Core CSV with columns "dc.identifier,dc.title,dc.creator,dc.type,dc.subject"
2. **Given** BCDI file has Windows-1252 encoding with French characters, **When** librarian runs conversion script, **Then** output file uses UTF-8 encoding and all French characters preserved
3. **Given** BCDI file has "Support" column with values "Livre", "CD Audio", "DVD Vidéo", **When** conversion runs, **Then** dc.type column contains original values as plain text (no normalization)

---

### User Story 4 - Convert Generic French CSV to Dublin Core (Priority: P3)

Schools export data from Excel or other systems with custom French column names (e.g., "Titre du livre", "Nom de l'auteur", "Type de média"). They need an automated way to convert these to Dublin Core.

**Why this priority**: Reduces manual work for data migration from various sources. Nice-to-have for broader adoption but not critical for MVP.

**Independent Test**: Can be tested by creating CSV with various French column name variations, running conversion script, and verifying automatic column detection works.

**Acceptance Scenarios**:

1. **Given** CSV has columns "Titre,Auteur,Type,ISBN", **When** librarian runs `python scripts/convert/french_csv_to_dublin_core.py custom.csv catalog.csv`, **Then** script auto-detects columns and outputs Dublin Core CSV
2. **Given** CSV has column "Titre du livre", **When** conversion script runs, **Then** script detects "titre" keyword and maps to dc.title
3. **Given** CSV has unmapped columns "Notes,Prix d'achat", **When** conversion runs, **Then** script warns "Unmapped columns (will be ignored): Notes, Prix d'achat" and proceeds without error

---

### User Story 5 - Export Borrower List to CSV (Priority: P1)

Librarians need to export their borrower list (students, teachers, staff) for backup, sharing with school administration, or migration to other systems. The export must include all borrower information in a standardized format.

**Why this priority**: Core functionality for data portability and compliance. Schools must be able to extract student data for reporting, transfers, or system migration. Critical for GDPR/data export requests.

**Independent Test**: Can be fully tested by creating sample borrowers, clicking export, downloading CSV, and verifying all fields are present and correctly formatted.

**Acceptance Scenarios**:

1. **Given** school has 150 students, 8 teachers, and 3 staff members, **When** librarian clicks "Export Borrowers", **Then** system downloads CSV file with all 161 borrower records
2. **Given** borrower list has French characters in names (François, Geneviève), **When** librarian exports and reopens in Excel, **Then** all French characters display correctly (UTF-8 encoding preserved)
3. **Given** borrower has blocked status with reason "Lost library card", **When** librarian exports, **Then** CSV includes blocked status and reason in separate columns
4. **Given** borrower has optional fields empty (email, phone, notes), **When** librarian exports, **Then** CSV includes empty columns for missing fields without errors

---

### User Story 6 - Import Borrowers from CSV (Priority: P1)

Librarians need to import borrower data from school administration systems (ONDE), previous library systems (BCDI, Hibouthèque, Waterbear), or bulk data entry done in Excel. The import must accept a standardized CSV format.

**Why this priority**: Essential for initial setup, annual student list updates, and data migration. Without import, librarians would need to manually enter hundreds of students each year.

**Independent Test**: Can be tested by preparing a borrower CSV file (using template), uploading via web UI, and verifying borrowers appear in system with correct values.

**Acceptance Scenarios**:

1. **Given** librarian has borrower CSV with 120 students, **When** they upload file via web UI, **Then** system imports all 120 borrowers successfully
2. **Given** CSV file has 3 borrowers with required fields (borrower_id, first_name, last_name, class) but missing optional fields (email, phone), **When** librarian imports, **Then** system imports all records successfully with empty optional fields
3. **Given** CSV file has 2 records with missing required field (first_name empty), **When** librarian imports, **Then** system rejects those 2 rows and shows error: "2 rows rejected: missing required field 'first_name'"
4. **Given** CSV file has borrower_id that already exists in database, **When** librarian imports, **Then** system updates existing borrower with new data from CSV (upsert behavior)
5. **Given** CSV file has incorrect column names (e.g., "StudentID" instead of "borrower_id"), **When** librarian uploads, **Then** system shows error: "Expected columns: borrower_id, first_name, last_name, class, role. Found: StudentID, FirstName, LastName, Class. Use conversion scripts if needed."

---

### User Story 7 - Convert ONDE Export to BCD Borrower Format (Priority: P2)

French schools use ONDE (Outil Numérique pour la Direction d'École - the national student database) to manage student enrollment. Librarians need to import student lists from ONDE into BCD without manual data entry.

**Why this priority**: ONDE is the official French national student database used by all French elementary schools. Supporting ONDE conversion is essential for French market adoption and reduces manual data entry errors.

**Independent Test**: Can be tested by obtaining sample ONDE CSV export, running conversion script, and verifying output matches BCD borrower format with correct encoding and field mapping.

**Acceptance Scenarios**:

1. **Given** librarian has ONDE export with columns "Nom;Prénom;Date de naissance;INE;Identifiant Classe", **When** they run `python scripts/convert/onde_to_bcd_borrowers.py onde_export.csv borrowers.csv`, **Then** script creates BCD borrower CSV with columns "borrower_id,first_name,last_name,class,role" (semicolon delimiter is default)
2. **Given** ONDE file uses semicolon separator (French CSV standard), **When** librarian runs conversion script, **Then** script correctly parses semicolon-delimited columns (or can override with --delimiter=";" flag explicitly)
3. **Given** ONDE file has UTF-8 encoding with French characters (François, Geneviève), **When** conversion runs, **Then** output file preserves all French characters correctly
4. **Given** ONDE file contains "Identifiant Classe" values like "CP-A", "CE1-B", **When** conversion runs, **Then** script maps these to BCD class names
5. **Given** ONDE file contains INE (student national ID), **When** conversion runs, **Then** script uses INE as borrower_id value

---

### Edge Cases

#### Catalog Import/Export
- **What happens when imported CSV has duplicate ISBNs?** System creates ONE bibliographic record and multiple items - one item per CSV row with unique item.id. Example: 2 rows with ISBN 2884453229 → 1 bibliographic record "La naissance" + 2 items (IDs 793, 794)
- **What happens when CSV row has dc.title but both dc.identifier AND item.id are empty?** System rejects the row with validation error (at least one identifier required for tracking)
- **What happens when CSV file exceeds 10,000 rows?** System shows error "File too large. Maximum 10,000 rows supported. Split file and import in batches."
- **What happens when CSV has columns in wrong order?** Column order doesn't matter - system matches by column name (dc.title, dc.creator, etc.)
- **What happens when medium_type contains values with special characters?** Stored as-is (plain text field, no validation) - e.g., "CD/DVD", "Livre + CD"
- **What happens when user exports then immediately re-imports?** Round-trip produces identical data (export → import → export yields same CSV)
- **What happens when BCDI file has encoding that's not Windows-1252?** Conversion script auto-detects encoding (tries UTF-8, Latin-1, Windows-1252 in order)
- **What happens when BCDI file uses semicolon delimiter instead of comma?** User must run script with --delimiter=";" flag to override default comma delimiter
- **What happens when conversion script encounters unknown BCDI "Support" value?** Stores original value as-is in dc.type (no mapping table, no validation)
- **What happens when importing CSV with BOM (Byte Order Mark)?** CSV parser handles BOM automatically (Python csv module strips UTF-8 BOM)
- **What happens when exporting empty catalog?** System creates CSV with headers only (no data rows)
- **What happens when CSV has multiline values (title with line break)?** CSV parser handles quoted multiline fields correctly per RFC 4180
- **What happens when 10% of CSV rows fail validation during import?** System commits all valid rows and shows summary: "Successfully imported 90 records. 10 rows failed - see errors below" with detailed error list showing "Row {number}: {error}" for each failure

#### Borrower Import/Export
- **What happens when imported borrower CSV has duplicate borrower_id?** System updates existing borrower with CSV data (upsert: update if exists, insert if new)
- **What happens when borrower CSV has borrower_id in wrong format?** System validates format during import - must be 1-20 alphanumeric characters
- **What happens when class name in CSV doesn't exist in database?** System creates warning but imports borrower with class_id=NULL (can be fixed later)
- **What happens when CSV has class name in lowercase (e.g., "cp-a")?** System normalizes to uppercase ("CP-A") before lookup, matches if "CP-A" exists in database
- **What happens when borrower has no class (teacher/staff)?** Class field is empty/NULL - perfectly valid for non-student roles
- **What happens when exporting borrowers with blocked status?** CSV includes 'active' column (True/False) and 'blocked_reason' column with text explanation
- **What happens when importing borrower with invalid email format?** System accepts any text in email field (no validation) - stores as-is
- **What happens when exporting borrowers and database has 0 borrowers?** System creates CSV with headers only (no data rows)
- **What happens when borrower CSV row has role="Student" but no class?** System imports with warning: "Student without class assignment" but allows import
- **What happens when borrower first_name or last_name contains special characters?** Stored as-is (plain text field) - e.g., "Jean-Pierre", "O'Connor", "François"
- **What happens when re-importing previously exported borrower CSV?** Round-trip produces identical data (export → import → export yields same CSV)
- **What happens when auto-generated barcode collides with existing barcode?** System increments sequential counter until finding unused barcode (e.g., if BCD000005 exists, skip to BCD000006)
- **What happens when 5 out of 120 borrower rows fail validation during import?** System commits 115 valid borrowers and shows: "Successfully imported 115 borrowers (85 new, 30 updated). 5 rows failed - see errors below" with detailed error list showing "Row {number}: {error}" for each failure (e.g., "Row 47: missing required field 'first_name'")

#### ONDE Conversion
- **What happens when ONDE file uses semicolon separator?** Conversion script uses semicolon as default delimiter (or user can specify with --delimiter=";" flag)
- **What happens when ONDE file uses comma separator instead of semicolon?** User must run script with --delimiter="," flag to override default semicolon delimiter
- **What happens when ONDE file has no INE column?** Script generates borrower_id using format "STUDENT-001", "STUDENT-002", etc.
- **What happens when ONDE file has duplicate INE values?** Script warns about duplicates and keeps only first occurrence
- **What happens when ONDE class name format is non-standard?** Script stores class name as-is without validation (e.g., "Classe de CP", "CP/CE1")
- **What happens when ONDE file has encoding issues?** Script tries UTF-8 first, falls back to Latin-1, then Windows-1252
- **What happens when ONDE file has extra columns not in mapping?** Script ignores unmapped columns and processes only known fields
- **What happens when ONDE file has column names in different case?** Script does case-insensitive column matching ("nom" = "Nom" = "NOM")
- **What happens when ONDE file has no header row?** Script fails with error: "CSV header not found. Expected columns: Nom, Prénom, INE"
- **What happens when converting ONDE file with 0 students?** Script creates output CSV with headers only and warns "No student records found"
- **What happens when multiple rows fail for different reasons?** Each failed row gets its own error line: "Row 5: missing required field 'dc.title'", "Row 12: invalid borrower_id format", "Row 23: missing required field 'first_name'"
- **What happens when user specifies wrong delimiter for conversion script?** Script fails with error: "Unable to parse CSV. Expected columns not found. Check --delimiter flag (use ';' for French CSV, ',' for standard CSV)"

## Requirements

### Functional Requirements

#### Core Import/Export

- **FR-001**: System MUST export catalog to Dublin Core CSV format with columns: dc.identifier, dc.title, dc.creator, dc.publisher, dc.type, dc.subject, dc.date
- **FR-002**: System MUST import catalog from Dublin Core CSV format with same column structure
- **FR-003**: System MUST preserve UTF-8 encoding in exported CSV files
- **FR-004**: System MUST detect and handle UTF-8, Latin-1, and Windows-1252 encodings when importing CSV files
- **FR-005**: System MUST validate that uploaded CSV contains required column dc.title AND at least one identifier (dc.identifier OR item.id)
- **FR-006**: System MUST show clear error message when CSV column names don't match Dublin Core format, directing users to conversion scripts
- **FR-007**: System MUST support CSV files up to 10,000 rows
- **FR-008**: System MUST reject CSV files exceeding 10,000 rows with error message
- **FR-009**: System MUST handle empty/missing values in optional CSV fields (dc.publisher, dc.subject, dc.date)
- **FR-010**: System MUST preserve exact values from CSV during import (no trimming whitespace, no case changes, no normalization)
- **FR-010a**: When CSV contains validation errors, system MUST commit all valid rows to database and report failed rows with specific error messages (partial import with warnings)
- **FR-010b**: Error messages for failed rows MUST include row number, field name, and error reason (e.g., "Row 15: missing required field 'first_name'" or "Row 23: invalid borrower_id format")

#### Import Deduplication

- **FR-044**: When multiple CSV rows share the same dc.identifier (ISBN), system MUST create ONE bibliographic record (notice) and MULTIPLE items (exemplaires) - one item per row
- **FR-045**: Each item MUST have a unique item.id (inventory/barcode number) from the CSV row
- **FR-046**: If rows with same ISBN have conflicting bibliographic data (different title, author, etc.), system MUST use values from first occurrence and log warning

#### Round-Trip Fidelity

- **FR-011**: Exported CSV re-imported MUST produce identical records (export → import → export yields same CSV)
- **FR-012**: System MUST preserve special characters in CSV values (commas, quotes, line breaks) using RFC 4180 quoting
- **FR-013**: System MUST preserve French accented characters (é, è, à, ç, œ) in round-trip export/import

#### Medium Type Handling

- **FR-014**: System MUST store medium_type as plain text VARCHAR field (no foreign keys, no normalization)
- **FR-015**: System MUST accept any string value in dc.type field during import (e.g., "Livre", "Book", "Libro", "Text", "CD Audio")
- **FR-016**: System MUST preserve exact dc.type values in database without transformation (case-sensitive storage)
- **FR-017**: System MUST export medium_type values exactly as stored in database

#### User Interface

- **FR-018**: Web UI MUST provide "Export Catalog" button on catalog page
- **FR-019**: Export button MUST trigger immediate CSV file download without intermediate screens
- **FR-020**: Web UI MUST provide "Import Catalog" button on catalog page
- **FR-021**: Import button MUST open file upload dialog accepting .csv files only
- **FR-022**: System MUST show progress indicator during import processing
- **FR-023**: System MUST show success message with count of imported records: "Successfully imported 250 records" (or "Successfully imported 245 records. 5 rows failed - see errors below" for partial imports)
- **FR-024**: System MUST show error message with specific issue when import fails completely (0 rows imported)
- **FR-024a**: For partial imports with failures, system MUST display error list with format: "Row {number}: {error description}" for each failed row
- **FR-025**: System MUST provide download link for Dublin Core CSV template from import dialog

#### BCDI Conversion Script

- **FR-026**: Conversion script MUST accept arguments: input BCDI CSV path, output Dublin Core CSV path, and optional --delimiter flag (defaults to comma for BCDI)
- **FR-027**: Script MUST map BCDI columns to Dublin Core: ISBN→dc.identifier, Titre→dc.title, Auteur→dc.creator, Editeur→dc.publisher, Support→dc.type, Cote→dc.subject, Année→dc.date
- **FR-028**: Script MUST read BCDI files with Windows-1252 encoding by default
- **FR-029**: Script MUST output Dublin Core files with UTF-8 encoding
- **FR-030**: Script MUST preserve BCDI "Support" values as plain text in dc.type (no mapping to English terms)
- **FR-031**: Script MUST add "isbn:" prefix to dc.identifier values if not already present
- **FR-032**: Script MUST print success message showing input file, output file, and encoding conversion

#### French CSV Conversion Script

- **FR-033**: Script MUST auto-detect CSV encoding (UTF-8, Latin-1, or Windows-1252)
- **FR-034**: Script MUST map common French column name variations to Dublin Core fields using case-insensitive matching
- **FR-035**: Script MUST recognize these French column patterns:
  - ISBN variations: "isbn", "isbn13", "numéro isbn", "numero isbn" → dc.identifier
  - Title variations: "titre", "title", "nom" → dc.title
  - Author variations: "auteur", "author", "créateur", "createur" → dc.creator
  - Publisher variations: "éditeur", "editeur", "publisher", "maison d'édition" → dc.publisher
  - Type variations: "type", "support", "format", "média", "media" → dc.type
  - Subject variations: "cote", "dewey", "classification", "sujet" → dc.subject
  - Date variations: "année", "annee", "date", "date de publication" → dc.date
- **FR-036**: Script MUST print detected column mappings before conversion: "ISBN → dc.identifier, Titre → dc.title"
- **FR-037**: Script MUST warn about unmapped columns: "Unmapped columns (will be ignored): Notes, Prix"
- **FR-038**: Script MUST add "isbn:" prefix to dc.identifier if value doesn't already start with prefix

#### Documentation & Templates

- **FR-039**: System MUST provide Dublin Core CSV template file at data/templates/catalog_dublin_core.csv
- **FR-040**: Template MUST include sample row with realistic data showing correct format
- **FR-041**: Conversion scripts MUST include usage instructions in docstring at top of file, including --delimiter flag usage
- **FR-042**: README.md MUST document how to use conversion scripts with examples showing both default delimiter and --delimiter flag override
- **FR-043**: README.md MUST explain Dublin Core column meanings (dc.identifier = ISBN, dc.title = title, etc.)

#### Borrower Import/Export

- **FR-047**: System MUST export borrowers to CSV format with columns: borrower_id, first_name, last_name, role, class, grade_level, barcode, active, blocked_reason, email, phone, notes
- **FR-048**: System MUST import borrowers from CSV format with same column structure
- **FR-049**: System MUST preserve UTF-8 encoding in exported borrower CSV files
- **FR-050**: System MUST detect and handle UTF-8, Latin-1, and Windows-1252 encodings when importing borrower CSV files
- **FR-051**: System MUST validate that uploaded borrower CSV contains required columns: borrower_id, first_name, last_name, role
- **FR-052**: System MUST show clear error message when borrower CSV column names don't match expected format
- **FR-053**: System MUST support borrower CSV files up to 5,000 rows (sufficient for largest elementary schools)
- **FR-054**: System MUST reject borrower CSV files exceeding 5,000 rows with error message
- **FR-055**: System MUST handle empty/missing values in optional borrower CSV fields (class, grade_level, email, phone, notes, blocked_reason)
- **FR-056**: System MUST validate role field contains only valid values: "student", "teacher", "staff" (case-insensitive)
- **FR-057**: System MUST generate unique barcode for borrower if barcode column is empty during import using sequential numeric format with "BCD" prefix (e.g., "BCD000001", "BCD000002", zero-padded to 6 digits)
- **FR-057a**: When auto-generating barcodes, system MUST check for collisions with existing barcodes and increment sequential counter until finding unused barcode
- **FR-058**: System MUST set active=True by default if active column is empty during import
- **FR-059**: Borrower import MUST use upsert behavior: update existing borrower if borrower_id exists, insert new borrower if not
- **FR-060**: System MUST preserve exact values from borrower CSV during import (no trimming whitespace, no case changes for names)
- **FR-061**: System MUST auto-populate full_name field during import by concatenating first_name + " " + last_name
- **FR-062**: System MUST validate borrower_id format during import: 1-20 alphanumeric characters, no special characters except dash/underscore
- **FR-063**: When borrower CSV references class name, system MUST normalize class name to uppercase before lookup; if normalized name not in database, system MUST import borrower with class_id=NULL and log warning
- **FR-064**: Web UI MUST provide "Export Borrowers" button on borrower management page
- **FR-065**: Export button MUST trigger immediate CSV file download without intermediate screens
- **FR-066**: Web UI MUST provide "Import Borrowers" button on borrower management page
- **FR-067**: Import button MUST open file upload dialog accepting .csv files only
- **FR-068**: System MUST show success message with count of imported/updated borrowers: "Successfully imported 120 borrowers (90 new, 30 updated)" (or "Successfully imported 115 borrowers (85 new, 30 updated). 5 rows failed - see errors below" for partial imports)
- **FR-069**: System MUST show error message with specific issue when borrower import fails completely (0 rows imported)
- **FR-069a**: For partial borrower imports with failures, system MUST display error list with format: "Row {number}: {error description}" for each failed row
- **FR-070**: System MUST provide download link for borrower CSV template from import dialog
- **FR-071**: Exported borrower CSV re-imported MUST produce identical records (export → import → export yields same CSV)
- **FR-072**: System MUST preserve French accented characters (é, è, à, ç, œ) in borrower names during round-trip export/import

#### ONDE Conversion Script

- **FR-073**: Conversion script MUST accept arguments: input ONDE CSV path, output BCD borrower CSV path, and optional --delimiter flag (defaults to semicolon for ONDE)
- **FR-074**: Script MUST map ONDE columns to BCD borrower format: Nom→last_name, Prénom→first_name, INE→borrower_id, Identifiant Classe→class
- **FR-075**: Script MUST support --delimiter flag to specify CSV separator character (e.g., --delimiter=";" for semicolon, --delimiter="," for comma); default to semicolon for ONDE files
- **FR-076**: Script MUST read ONDE files with UTF-8 encoding by default
- **FR-077**: Script MUST output BCD borrower files with UTF-8 encoding and comma separator
- **FR-078**: Script MUST set role="student" for all records from ONDE (student database)
- **FR-079**: Script MUST handle ONDE column variations: "Nom" or "Nom de l'élève", "Prénom" or "Prénom de l'élève"
- **FR-080**: Script MUST preserve French accented characters during conversion (François, Geneviève, etc.)
- **FR-081**: Script MUST generate unique borrower_id if INE column is empty, using format "STUDENT-{sequential_number}"
- **FR-082**: Script MUST extract grade level from class name if possible (e.g., "CP-A" → grade_level="CP")
- **FR-083**: Script MUST print success message showing input file, output file, and record count
- **FR-084**: Script MUST handle ONDE exports with or without header row (auto-detect based on first row content)
- **FR-085**: Script MUST warn if ONDE file contains duplicate INE values (same student appears multiple times)

### Key Entities

- **BibliographicRecord**: Represents a book, periodical, CD, or other library material
  - isbn (dc.identifier): International Standard Book Number or other identifier
  - title (dc.title): Main title of the work
  - author (dc.creator): Primary creator/author
  - publisher (dc.publisher): Publishing organization
  - medium_type (dc.type): Type of physical medium - **stored as plain text VARCHAR**, not normalized
  - dewey_decimal (dc.subject): Dewey Decimal Classification code
  - publication_year (dc.date): Year of publication

- **Borrower**: Represents a library user (student, teacher, or staff member)
  - borrower_id: Unique identifier (student ID, staff ID)
  - first_name: Given name
  - last_name: Family name
  - full_name: Concatenated full name (auto-populated)
  - role: User type (student, teacher, staff)
  - class: Class assignment (CP-A, CE1-B, etc.) - optional for non-students
  - grade_level: Grade level (CP, CE1, etc.) - optional
  - barcode: Library card barcode - auto-generated if not provided
  - active: Account status (true/false)
  - blocked_reason: Explanation if account blocked
  - email: Contact email - optional
  - phone: Contact phone - optional
  - notes: Free-form notes - optional

## Terminology

This specification uses English terms consistently. For reference, here are French equivalents used in the library domain:

| English Term | French Term | Usage |
|--------------|-------------|-------|
| Bibliographic Record | Notice | The catalog entry describing a book/item |
| Item | Exemplaire | Physical copy of a work (identified by barcode) |
| Borrower | Emprunteur | Library user (student, teacher, staff) |
| Checkout | Emprunter | Lending an item to a borrower |
| Return | Retourner | Returning a borrowed item |

**Note**: Internal documentation and code use English terms exclusively. French terms appear only in:
- User-facing UI (via i18n locale files)
- BCDI/ONDE import data (source systems use French)
- Edge case descriptions referencing French school contexts

## Success Criteria

### Measurable Outcomes

#### Catalog Import/Export
- **SC-001**: Librarian can export catalog of 1000 records in under 5 seconds (aspirational goal - no formal validation)
- **SC-002**: Librarian can import CSV of 1000 records in under 10 seconds (aspirational goal - no formal validation)
- **SC-003**: Round-trip catalog export/import produces byte-identical CSV files (100% fidelity)
- **SC-004**: 100% of French characters (é, è, à, ç, œ) survive catalog round-trip without corruption
- **SC-005**: BCDI conversion script converts >95% of rows without errors from sample files from 3 different French schools
- **SC-006**: French CSV conversion script auto-detects columns with 90%+ accuracy on test files with common French names (aspirational goal - no formal validation)
- **SC-007**: Catalog import error messages are clear enough that 80% of users can self-correct without support
- **SC-008**: Librarians complete full catalog import workflow (download template → fill data → import) in under 15 minutes
- **SC-009**: Zero data loss during catalog import/export (all non-empty fields preserved exactly)
- **SC-010**: System handles catalog CSV files up to 10,000 rows without memory errors or timeouts

#### Borrower Import/Export
- **SC-011**: Librarian can export borrower list of 500 users in under 3 seconds (aspirational goal - no formal validation)
- **SC-012**: Librarian can import borrower CSV of 500 users in under 8 seconds (aspirational goal - no formal validation)
- **SC-013**: Round-trip borrower export/import produces byte-identical CSV files (100% fidelity)
- **SC-014**: 100% of French characters (é, è, à, ç, œ) in borrower names survive round-trip without corruption
- **SC-015**: Borrower import error messages are clear enough that 80% of users can self-correct without support
- **SC-016**: Librarians complete full borrower import workflow (download template → fill data → import) in under 10 minutes
- **SC-017**: Zero data loss during borrower import/export (all non-empty fields preserved exactly)
- **SC-018**: System handles borrower CSV files up to 5,000 rows without memory errors or timeouts
- **SC-019**: Upsert behavior correctly updates 100% of existing borrowers when re-importing with changed data
- **SC-020**: Barcode auto-generation produces unique sequential barcodes (BCD000001 format) for 100% of imported borrowers with empty barcode field
- **SC-021**: ONDE conversion script converts >95% of rows without errors from sample ONDE exports from 3 different schools
- **SC-022**: ONDE conversion workflow (export from ONDE → run script → import to BCD) completes in under 5 minutes for 200 students

## Scope

### In Scope

#### Catalog Import/Export
- ✅ Export catalog to Dublin Core CSV
- ✅ Import catalog from Dublin Core CSV
- ✅ BCDI → Dublin Core conversion script (Python)
- ✅ French CSV → Dublin Core conversion script (Python)
- ✅ UTF-8 encoding handling for catalog
- ✅ Catalog CSV template file
- ✅ Plain text storage for medium_type field
- ✅ Catalog import/export web UI (upload/download buttons)

#### Borrower Import/Export
- ✅ Export borrowers to standardized CSV
- ✅ Import borrowers from standardized CSV
- ✅ ONDE → BCD borrower conversion script (Python)
- ✅ UTF-8 encoding handling for borrower data
- ✅ Semicolon-delimited CSV support for ONDE files
- ✅ Borrower CSV template file
- ✅ Borrower import/export web UI (upload/download buttons)
- ✅ Upsert behavior (update existing, insert new)
- ✅ Auto-generation of barcodes for borrowers without barcode
- ✅ Validation of required borrower fields
- ✅ Support for optional borrower fields (email, phone, notes)

#### Common
- ✅ Documentation and usage examples
- ✅ Error messages for validation failures

### Out of Scope

- ❌ Fuzzy column matching (require exact Dublin Core column names)
- ❌ Auto-detection of CSV format (user runs conversion script if needed)
- ❌ Multi-step import wizard with preview (simple upload → import)
- ❌ Medium type normalization or validation
- ❌ Foreign key lookup tables for medium types
- ❌ Admin UI for managing medium type mappings
- ❌ Export format selection (Dublin Core only for catalog)
- ❌ Import from non-CSV formats (JSON, XML, Excel binary)
- ❌ Filtering export by criteria (exports entire catalog/borrower list)
- ❌ Incremental/delta imports (full imports only)
- ❌ Import validation preview before committing
- ❌ Rollback on partial import failure (best-effort import, show errors)

## Assumptions

### Catalog Import/Export
1. **Dublin Core is sufficient**: Dublin Core 15 core elements cover school library needs (title, creator, publisher, type, subject, identifier, date)
2. **Schools can run Python scripts**: IT staff or tech-savvy librarians can run command-line conversion scripts
3. **Plain text medium types acceptable**: Schools don't need normalized/standardized medium type codes; plain text like "Livre", "Book", "CD Audio" is sufficient
4. **10,000 row limit reasonable**: Largest French elementary school has ~5,000 catalog items; 10,000 limit provides 2x headroom
5. **Single catalog export acceptable**: Schools don't need to filter exports (e.g., by Dewey range, medium type); full catalog export is sufficient
6. **No catalog import preview needed**: Librarians trust their catalog data; they don't need to preview import before committing (can export immediately after to verify)
7. **Best-effort catalog import acceptable**: If some rows fail validation, system commits successful rows to database and reports errors for failed rows (no atomic all-or-nothing rollback)
8. **BCDI column names stable**: BCDI CSV export format uses standard column names (ISBN, Titre, Auteur, Support, Cote) across all versions
9. **Manual script execution acceptable**: Users can handle two-step process: (1) run conversion script, (2) import via web UI
10. **Catalog import is additive**: Importing CSV adds new records; doesn't update existing records by ISBN (future feature)

### Borrower Import/Export
11. **Standard CSV format acceptable**: No need to support proprietary formats from Hibouthèque, Waterbear, or BCDI - users can export to CSV from those systems or use Excel
12. **5,000 borrower row limit reasonable**: Largest French elementary school has ~500 students + staff; 5,000 limit provides 10x headroom for multi-school deployments
13. **UTF-8 as default**: Modern Excel/LibreOffice handle UTF-8 CSV correctly; no need for legacy Latin-1 exports
14. **No versioning needed**: CSV format won't change; no need to version schema or handle migrations
15. **Upsert behavior acceptable**: Re-importing borrowers updates existing records by borrower_id; schools expect this for annual student list updates
16. **No borrower import preview needed**: Librarians trust their borrower data; they don't need to preview import before committing
17. **Best-effort borrower import acceptable**: If some rows fail validation, system commits successful rows to database and reports errors for failed rows (no atomic all-or-nothing rollback)
18. **Auto-generated barcodes sufficient**: System-generated barcodes (incremental or random) are acceptable when borrower CSV doesn't include barcodes
19. **Class name matching by string**: When CSV references class name, system normalizes to uppercase then looks up by exact match; if not found, sets class_id=NULL with warning (e.g., "cp-a" → "CP-A" before lookup)
20. **No borrower deduplication beyond borrower_id**: System doesn't check for duplicate names or emails; borrower_id is the sole unique identifier
21. **Single borrower export acceptable**: Schools don't need to filter exports (e.g., by role, class); full borrower list export is sufficient
22. **Role validation sufficient**: Three roles (student, teacher, staff) cover all school library user types; no need for custom roles
23. **ONDE export format stable**: ONDE CSV exports use standard column names (Nom, Prénom, INE, Identifiant Classe) across all French schools
24. **ONDE semicolon separator standard**: All ONDE exports use semicolon (;) as field separator, following French CSV conventions
25. **INE as unique identifier acceptable**: French national student ID (INE) is unique and persistent across student's schooling; suitable as borrower_id
26. **ONDE contains only students**: ONDE is student database; teachers/staff must be added separately (not included in ONDE exports)
27. **Manual ONDE conversion acceptable**: Librarians can handle two-step process: (1) export from ONDE, (2) run conversion script, (3) import via web UI
28. **No Educ'Horus support needed**: Educ'Horus has been discontinued; no need to support legacy formats from abandoned software
