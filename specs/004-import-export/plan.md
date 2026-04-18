# Implementation Plan: Library Data Import/Export with Standards Compatibility

**Branch**: `004-import-export` | **Date**: 2026-02-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-import-export/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement CSV import/export functionality with configurable medium type taxonomy and BCDI/Dublin Core compatibility. System must support:

1. **Export**: Borrowers and catalog to CSV (Standard/BCDI/Dublin Core formats) with UTF-8 encoding and round-trip fidelity
2. **Import**: Fuzzy column mapping and value normalization with configurable mapping rules (80-90% auto-detection success rate)
3. **Configurable Taxonomy**: Admin-managed medium types stored as foreign key lookups (not hardcoded enums) with bilingual display names (en/fr)
4. **Data Migration**: Migrate existing French enum values (Livre, Périodique) to generic codes (book, periodical) via one-time migration script
5. **BCDI Interoperability**: Support French school library standard (80% market share) with import/export mappings

**Technical Approach** (from research.md):
- Use Koha-style foreign key lookup tables for medium types (`medium_types` + `medium_type_mappings`)
- Multi-stage normalization pipeline: text cleaning → abbreviation expansion → synonym matching (rapidfuzz library with 80% threshold)
- Three-phase database migration pattern with temporary columns for zero data loss
- Admin UI with inline-editable tables and drag-and-drop reordering (React-Admin/Ant Design patterns)
- CSV parsing via built-in csv module (UTF-8/Latin-1/Windows-1252 auto-detection), export via RFC 4180 compliant formatting

## Technical Context

**Language/Version**: Python 3.11+ (matches existing BCD codebase)
**Primary Dependencies**:
- FastAPI (existing REST API framework)
- SQLAlchemy ORM (existing database layer)
- Alembic (existing migration tool)
- Vue 3 (existing web UI framework via CDN)
- rapidfuzz (NEW - fuzzy string matching for import normalization, pure Python, no C dependencies)
- chardet (NEW - encoding auto-detection for CSV imports, optional fallback to charset-normalizer)

**Storage**: SQLite (development), PostgreSQL-ready (production) - existing database
**Testing**: pytest (existing test framework), service-layer integration tests required (80%+ coverage per constitution)
**Target Platform**: Linux server (primary), Windows (cross-platform requirement per constitution), web browsers (Chrome/Firefox/Safari/Edge latest 2 versions for UI)

**Project Type**: Web application (existing FastAPI backend + Vue 3 CDN-based frontend)

**Performance Goals**:
- Export: 1000 records in <5 seconds (spec SC-001/SC-002)
- Import: 1000 rows in <10 seconds (spec SC-006)
- CSV parsing: 10,000 rows without memory errors (spec SC-009)
- Admin UI: Medium type add/edit in <5 minutes (spec SC-013)
- Fuzzy matching: 80-90% auto-detection success rate (research.md)

**Constraints**:
- Round-trip fidelity: Export → Import → Export produces identical CSV (spec FR-064 to FR-070)
- UTF-8 encoding: French characters (é, è, à, ç, œ) survive round-trip (spec FR-069)
- Browser compatibility: No build tools, CDN-based Vue 3 (existing constraint from 003-web-ui)
- Legacy hardware: Must work on 5+ year old computers (constitution Principle VI)
- Import limit: 10,000 rows per file (spec FR-062) to prevent memory exhaustion
- Transaction safety: Rollback on error, no partial imports (spec FR-063)

**Scale/Scope**:
- Target schools: 10-5000 borrowers, 500-10,000 catalog items (spec assumptions)
- Medium types: 9 default types + unlimited custom types (spec FR-033)
- Import mappings: ~100 entries (BCDI + Dublin Core + UNIMARC variants) (spec assumptions)
- File size: <2MB for typical school (1000 borrowers, 5000 items) (spec assumptions)
- Export formats: 3 formats (Standard/BCDI/Dublin Core)
- Import formats: Auto-detect via fuzzy matching (BCDI, Pronote, Excel, Dublin Core)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Code Quality & DRY
- **Compliant**: CSV parsing logic centralized in single service module
- **Compliant**: Import mapping rules stored in database (not duplicated across code)
- **Compliant**: Normalization functions shared between import and validation preview

### ✅ II. Library-First Approach
- **Compliant**: Use rapidfuzz library for fuzzy matching (battle-tested, 4.5k+ GitHub stars, active maintenance)
- **Compliant**: Use chardet for encoding detection (industry standard, used by requests library)
- **Compliant**: Use Python csv module (stdlib) for parsing (RFC 4180 compliant)
- **Compliant**: No custom CSV parser, no custom fuzzy matching algorithm

### ✅ III. Comprehensive Testing Standards
- **Compliant**: Service-layer integration tests required (import_service.py, export_service.py)
- **Compliant**: Test round-trip fidelity (export → import → export identical)
- **Compliant**: Test BCDI/Dublin Core compatibility with sample files
- **Compliant**: Test fuzzy matching edge cases (accents, case, whitespace, synonyms)
- **Target**: 90%+ coverage for import/export services (spec SC-010: <5% error rate requires extensive testing)

### ✅ IV. User Experience Consistency
- **Compliant**: Import wizard follows existing multi-step pattern (upload → preview → map → confirm)
- **Compliant**: Export dialog matches existing modal patterns (filters → format → download)
- **Compliant**: Admin UI uses existing settings page layout (tabs for Medium Types and Import Mappings)
- **Compliant**: Error messages follow existing pattern (row-level errors with downloadable CSV log)

### ✅ V. Click Minimization
- **Compliant**: Export in ≤2 clicks (Export button → Download)
- **Compliant**: Import auto-detection reduces manual mapping from 100% to 10-20% (spec SC-012: 90% auto-mapped)
- **Compliant**: Smart defaults: Remember last export format choice, pre-select all filters
- **Compliant**: Batch operations: Export filtered subset, import 10,000 rows at once

### ✅ VI. Performance for Legacy Hardware
- **Compliant**: CSV export generates file in-memory then streams (no temp files)
- **Compliant**: Import processes batches of 1000 rows to avoid memory spike
- **Compliant**: Fuzzy matching uses cached normalization (precompute lowercase/accent-stripped versions)
- **Compliant**: Admin UI pagination (100 medium types per page, though typically <20 types)
- **Target**: <5 seconds export for 1000 records, <10 seconds import (spec SC-001/SC-002/SC-006)

### ✅ VII. Database Schema Versioning & Migrations
- **Compliant**: Alembic migration for medium_types and medium_type_mappings tables (new)
- **Compliant**: Alembic migration for bibliographic_record.medium_type_id foreign key conversion (breaking change)
- **Compliant**: Data migration script (one-time) to populate default types and mappings
- **Compliant**: Migration script to convert existing enum values → foreign keys
- **⚠️ Risk**: Breaking change requires downtime during migration (estimated 1-5 minutes for 10k records)

### ✅ VIII. Research-First Feature Design
- **Compliant**: Researched Koha, Evergreen, Alma for configurable taxonomy patterns
- **Compliant**: Researched CSVBox, Dromo, Flatfile for modern import UX
- **Compliant**: Researched BCDI documentation for French library compatibility
- **Compliant**: Researched UNIMARC standard for bibliographic exchange format
- **Output**: research.md with 23 cited sources and concrete implementation patterns

### ✅ IX. Design-First Implementation
- **Compliant**: Import wizard mockup defined in spec.md (4-step flow with screenshots reference)
- **Compliant**: Export dialog mockup defined in spec.md (filter + format selection)
- **Compliant**: Admin UI mockup referenced in research.md (inline-editable table pattern)
- **Pending**: Vue components mockup (to be created in Phase 1: quickstart.md with HTML examples)

### ✅ X. Internationalization (i18n)
- **Compliant**: No hardcoded French in database (generic English codes: book, cd, dvd)
- **Compliant**: UI displays localized names via medium_types.display_name_fr (i18n via database)
- **Compliant**: All error messages externalized to locales/en.json and locales/fr.json
- **Compliant**: Import wizard labels, export dialog labels, admin UI labels all in translation files
- **Critical**: This feature FIXES existing i18n violation (hardcoded MediumType.LIVRE in database → generic code)

### ✅ XI. Quality Gate Process
- **Pre-Implementation Gate**: Run `/speckit.analyze` before `/speckit.implement` (spec already validated)
- **Post-Implementation Gate**: Run `/speckit.review` before merge (constitution re-validation + architecture review)
- **Automated Validation**: pytest coverage ≥80%, zero TODO/FIXME, zero hardcoded French strings in database
- **Severity Tracking**: Document MEDIUM findings (e.g., migration downtime) and mitigation plan

### 🟡 Complexity Tracking

**No violations requiring justification** - All principles compliant.

**Notes**:
- Migration risk (Principle VII): Breaking change requires careful planning and rollback strategy (documented in data-model.md)
- New dependencies (Principle II): rapidfuzz and chardet justified as library-first approach (reduces custom code by 90%)
- Performance targets (Principle VI): Require batch processing and caching optimizations (detailed in data-model.md)

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
├── bcd_api/
│   ├── models/
│   │   ├── medium_type.py           # NEW: MediumType model
│   │   ├── medium_type_mapping.py   # NEW: MediumTypeMapping model
│   │   └── bibliographic_record.py  # MODIFIED: Change medium_type to FK
│   ├── services/
│   │   ├── export_service.py        # NEW: CSV export logic
│   │   ├── import_service.py        # MODIFIED: Add fuzzy matching, extend normalization
│   │   ├── medium_type_service.py   # NEW: Admin CRUD for medium types
│   │   └── catalog_service.py       # MODIFIED: Use FK lookup for medium types
│   ├── schemas/
│   │   ├── medium_type.py           # NEW: Pydantic schemas for admin API
│   │   ├── import_export.py         # NEW: Import/export request/response schemas
│   │   └── bibliographic_record.py  # MODIFIED: Remove MediumType enum validation
│   ├── api/v1/
│   │   ├── export.py                # NEW: Export endpoints (borrowers, catalog)
│   │   ├── import_legacy.py         # RENAMED: borrowers.py import endpoint (exists)
│   │   ├── catalog.py               # MODIFIED: Add medium type admin endpoints
│   │   └── settings.py              # NEW or MODIFIED: Medium type admin UI endpoints
│   └── utils/
│       ├── csv_utils.py             # NEW: RFC 4180 CSV formatting, encoding detection
│       └── fuzzy_matcher.py         # NEW: rapidfuzz wrapper for column/value matching
│
├── bcd_web_vue/
│   ├── js/
│   │   ├── components/
│   │   │   ├── borrowers/
│   │   │   │   ├── BorrowerExport.js         # NEW: Export borrowers modal
│   │   │   │   └── BorrowerImport.js         # EXISTS: Extend with mapping preview
│   │   │   ├── catalog/
│   │   │   │   ├── CatalogExport.js          # NEW: Export catalog modal
│   │   │   │   └── CatalogImport.js          # EXISTS: Extend with fuzzy matching
│   │   │   └── settings/
│   │   │       ├── MediumTypesTab.js         # NEW: Admin medium types management
│   │   │       └── ImportMappingsTab.js      # NEW: Admin import mappings management
│   │   ├── composables/
│   │   │   ├── useCSVExport.js               # NEW: CSV generation composable
│   │   │   ├── useCSVImport.js               # MODIFIED: Add fuzzy matching UI logic
│   │   │   └── useMediumTypes.js             # NEW: Medium type admin composable
│   │   └── pages/
│   │       ├── BorrowersPage.js              # MODIFIED: Add Export button
│   │       ├── CatalogPage.js                # MODIFIED: Add Export button
│   │       └── SettingsPage.js               # MODIFIED: Add Medium Types tab
│   └── locales/
│       ├── en.json                           # MODIFIED: Add export/import/admin keys
│       └── fr.json                           # MODIFIED: Add export/import/admin keys
│
├── shared/
│   └── constants.py                          # MODIFIED: Remove MediumType enum (breaking change)
│
└── migrations/
    └── versions/
        ├── YYYYMMDD_HHMMSS_add_medium_types_tables.py    # NEW: Create tables
        └── YYYYMMDD_HHMMSS_migrate_medium_type_fk.py     # NEW: Convert enum to FK

tests/
├── integration/
│   ├── test_export_service.py                # NEW: Round-trip tests, encoding tests
│   ├── test_import_service.py                # MODIFIED: Add fuzzy matching tests
│   ├── test_medium_type_service.py           # NEW: Admin CRUD tests
│   └── test_migration_medium_type.py         # NEW: Migration safety tests
└── unit/
    ├── test_csv_utils.py                     # NEW: CSV formatting, encoding tests
    └── test_fuzzy_matcher.py                 # NEW: Fuzzy matching algorithm tests

data/
└── sample_imports/                           # MODIFIED: Add BCDI/Dublin Core samples
    ├── bcdi_catalog.csv                      # NEW: Sample BCDI export
    ├── dublin_core_catalog.csv               # NEW: Sample Dublin Core export
    └── borrowers_bcdi.csv                    # NEW: Sample BCDI borrower export
```

**Structure Decision**:

This is a **web application** (Option 2) with FastAPI backend and Vue 3 CDN-based frontend. The feature extends the existing 3-layer architecture:

1. **Models Layer** (src/bcd_api/models/): Add medium_type.py, medium_type_mapping.py, modify bibliographic_record.py
2. **Services Layer** (src/bcd_api/services/): Add export_service.py, medium_type_service.py, modify import_service.py
3. **API Layer** (src/bcd_api/api/v1/): Add export.py, modify catalog.py for admin endpoints
4. **UI Layer** (src/bcd_web_vue/): Add export/admin components, modify existing pages

**Key Changes**:
- **NEW files**: 17 new files (services, models, UI components, migrations)
- **MODIFIED files**: 10 modified files (existing services, schemas, pages, constants)
- **BREAKING CHANGE**: shared/constants.py removes MediumType enum → requires migration
- **Database migrations**: 2 Alembic migrations (create tables, convert FK)
- **Sample data**: 3 new sample CSV files for testing BCDI/Dublin Core compatibility

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
