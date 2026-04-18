# Implementation Plan: CSV Import/Export for Catalog and Borrowers

**Branch**: `005-csv-import` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-csv-import/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable librarians to import and export catalog (bibliographic records + items) and borrower data via CSV files. Support Dublin Core standard format for catalog exports, standardized CSV format for borrower data, and provide conversion scripts for BCDI (catalog) and ONDE (borrowers) formats commonly used in French schools. This feature enables data portability, backup/restore, migration from legacy systems, and compliance with data export regulations (GDPR).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- FastAPI (existing API framework)
- SQLAlchemy (existing ORM)
- Python csv module (stdlib - CSV parsing)
- charset-normalizer (encoding detection for BCDI/ONDE files - faster alternative to chardet)
- Pydantic (request/response validation)

**Storage**: SQLite (development), PostgreSQL-ready (production) - existing database
**Testing**: pytest (existing test framework)
**Target Platform**: Linux (primary) + Windows (cross-platform support required)
**Project Type**: Single project (web application with API backend)
**Performance Goals**:
- Export 1,000 catalog records in <5 seconds
- Import 1,000 catalog records in <10 seconds
- Export 500 borrowers in <3 seconds
- Import 500 borrowers in <8 seconds
- Conversion scripts process files in <2 seconds

**Constraints**:
- Legacy hardware support (5+ year old computers with HDD, 4GB RAM)
- UTF-8 encoding mandatory for exports
- Round-trip fidelity (export → import → export produces identical CSV)
- File size limits: 10,000 rows (catalog), 5,000 rows (borrowers)
- Best-effort partial imports (commit valid rows, report failures)

**Scale/Scope**:
- Catalog: Up to 5,000 bibliographic records per school
- Borrowers: Up to 500 students/staff per school
- 4 conversion scripts (BCDI→Dublin Core, French CSV→Dublin Core, ONDE→BCD, generic CSV→BCD)
- 2 web UI pages with import/export buttons (catalog page, borrower page)
- ~8-10 new service functions across import/export/conversion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality & DRY
- ✅ **PASS**: CSV parsing logic will be centralized in service layer (no duplication)
- ✅ **PASS**: Column mapping patterns shared across conversion scripts
- ✅ **PASS**: Encoding detection abstracted into reusable function

### II. Library-First Approach
- ✅ **PASS**: Using Python stdlib `csv` module (RFC 4180 compliant)
- ✅ **PASS**: Using `chardet` library for encoding detection (proven solution)
- ⚠️ **REVIEW**: Consider using `pandas` for CSV operations vs. manual parsing
  - **Decision**: Use stdlib `csv` module - pandas adds 30MB+ dependency for simple CSV operations
  - **Justification**: Feature only needs basic CSV read/write, not data analysis

### III. Comprehensive Testing Standards
- ✅ **PASS**: Service-layer integration tests planned for import/export functions
- ✅ **PASS**: Round-trip fidelity tests (export → import → verify identical)
- ✅ **PASS**: Encoding tests (UTF-8, Latin-1, Windows-1252)
- ✅ **PASS**: Edge case tests (empty files, malformed CSV, duplicate identifiers)
- ✅ **PASS**: Cross-platform tests (Linux & Windows path handling)

### IV. User Experience Consistency
- ✅ **PASS**: Import/export buttons follow existing UI patterns (Bootstrap 5)
- ✅ **PASS**: Error messages follow structured exception pattern with error codes
- ✅ **PASS**: Success messages consistent format: "Successfully imported X records (Y new, Z updated)"
- ✅ **PASS**: File upload dialog follows existing file picker patterns

### V. Click Minimization
- ✅ **PASS**: Export = single button click → immediate download (no intermediate screens)
- ✅ **PASS**: Import = single file picker → upload → feedback
- ✅ **PASS**: Template download available from import dialog (no navigation required)
- ✅ **PASS**: Conversion scripts run from command line (no GUI needed)

### VI. Performance for Legacy Hardware
- ✅ **PASS**: Batch operations for large imports (bulk insert mappings)
- ✅ **PASS**: Server-side pagination on list views (existing pattern)
- ✅ **PASS**: Progress indicators for long operations (import processing)
- ✅ **PASS**: File size limits prevent memory exhaustion (10k/5k row limits)
- ⚠️ **ACTION**: Implement batch commit strategy (see Performance Patterns #10)

### VII. Database Schema Versioning & Migrations
- ✅ **PASS**: No schema changes required (uses existing models)
- ✅ **N/A**: Feature reads/writes existing tables only

### VIII. Research-First Feature Design
- ✅ **PASS**: Research ONDE, BCDI, Hibouthèque, Waterbear formats completed
- ✅ **PASS**: Dublin Core standard identified and documented
- ✅ **PASS**: Industry standards reviewed (NCIP, SIP2, CSV conventions)
- ⚠️ **PENDING**: Phase 0 research to finalize CSV library choice

### IX. Design-First Implementation
- ⚠️ **PENDING**: Phase 1 mockups for import/export UI (web pages)
- ⚠️ **PENDING**: CLI command structure for conversion scripts
- ⚠️ **PENDING**: Sample CSV templates (Dublin Core, BCD borrower format)

### X. Internationalization (i18n)
- ✅ **PASS**: All UI text must use i18n keys (no hard-coded strings)
- ✅ **PASS**: Error messages follow error_code + context pattern (existing pattern)
- ✅ **PASS**: Success messages externalized to locale files
- ⚠️ **ACTION**: Add French translations for import/export errors
- ⚠️ **ACTION**: Conversion script help text in English (acceptable for CLI tools)

### XI. Quality Gate Process
- ✅ **PASS**: Pre-implementation gate - `/speckit.analyze` will run before `/speckit.implement`
- ✅ **PASS**: Post-implementation gate - `/speckit.review` will validate constitution compliance
- ✅ **PASS**: Test coverage target: 80%+ for new import/export services
- ✅ **PASS**: No TODO/FIXME/HACK comments allowed in production code

---

### Gate Status: ✅ **PASS** (pending Phase 0/1 deliverables)

**Issues to Address:**
1. **Phase 0**: Research CSV library choice (stdlib csv vs pandas)
2. **Phase 1**: Create mockups for import/export UI
3. **Phase 1**: Define CLI command structure for conversion scripts
4. **Implementation**: Add i18n translations for new error codes
5. **Implementation**: Implement batch commit strategy for performance

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── bcd_api/                     # Backend API
│   ├── api/v1/
│   │   ├── catalog.py          # ✨ ADD: Export/import endpoints
│   │   └── borrowers.py        # ✨ ADD: Export/import endpoints
│   ├── services/
│   │   ├── import_service.py   # ✨ ADD: CSV import service (catalog + borrowers)
│   │   ├── export_service.py   # ✨ NEW: CSV export service (catalog + borrowers)
│   │   └── dublin_core_import.py # ✨ UPDATE: Extract column mapping logic
│   ├── schemas/
│   │   ├── catalog.py          # ✨ UPDATE: Add import/export request/response schemas
│   │   ├── borrower.py         # ✨ UPDATE: Add import/export request/response schemas
│   │   └── export.py           # ✨ NEW: Export schemas (ExportFormat, ExportResponse)
│   └── core/
│       └── exceptions.py       # ✨ UPDATE: Add CSV validation exceptions
│
├── bcd_web_vue/                # Frontend (Vue 3 CDN-based)
│   ├── js/pages/
│   │   ├── CatalogPage.js     # ✨ UPDATE: Add export/import buttons
│   │   └── BorrowerPage.js     # ✨ UPDATE: Add export/import buttons
│   ├── js/components/
│   │   ├── catalog/
│   │   │   ├── CatalogImport.js   # ✨ NEW: Import dialog component
│   │   │   └── CatalogExport.js   # ✨ NEW: Export button component
│   │   └── borrowers/
│   │       ├── BorrowerImport.js  # ✨ NEW: Import dialog component
│   │       └── BorrowerExport.js  # ✨ NEW: Export button component
│   └── locales/
│       ├── en.json            # ✨ UPDATE: Add import/export translations
│       └── fr.json            # ✨ UPDATE: Add import/export translations (French)
│
└── shared/
    └── constants.py            # ✨ UPDATE: CSV format constants

scripts/
└── convert/                    # ✨ NEW: Conversion scripts directory
    ├── bcdi_to_dublin_core.py        # ✨ NEW: BCDI → Dublin Core converter
    ├── french_csv_to_dublin_core.py  # ✨ NEW: French CSV → Dublin Core converter
    ├── onde_to_bcd_borrowers.py      # ✨ NEW: ONDE → BCD borrower converter
    └── README.md                      # ✨ NEW: Conversion script documentation

data/
└── templates/                  # ✨ NEW: CSV templates
    ├── catalog_dublin_core.csv       # ✨ NEW: Dublin Core template with sample row
    └── borrowers_bcd.csv             # ✨ NEW: BCD borrower template with sample row

tests/
├── integration/
│   ├── test_import_service.py       # ✨ NEW: Import service integration tests
│   ├── test_export_service.py       # ✨ NEW: Export service integration tests
│   ├── test_dublin_core_import.py   # ✨ UPDATE: Add deduplication tests
│   └── test_catalog_api.py          # ✨ UPDATE: Add import/export endpoint tests
└── unit/
    ├── test_bcdi_conversion.py      # ✨ NEW: BCDI conversion script tests
    ├── test_french_csv_conversion.py # ✨ NEW: French CSV conversion tests
    ├── test_onde_conversion.py      # ✨ NEW: ONDE conversion script tests
    └── test_dublin_core_import_unit.py # ✨ NEW: Unit tests for column mapping
```

**Structure Decision**: **Single project (DEFAULT)** - BCD uses a three-layer clean architecture (API/Services/Models) with a Vue 3 CDN-based frontend served from the same origin. No build tools required for frontend. Conversion scripts live in `scripts/convert/` as standalone CLI utilities.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
