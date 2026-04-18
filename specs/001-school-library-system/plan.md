# Implementation Plan: School Library Management System

**Branch**: `001-school-library-system` | **Date**: 2026-01-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-school-library-system/spec.md`

**Note**: This document outlines the technical implementation plan with API-first architecture to support CLI, web, and desktop (Tauri) interfaces.

## Summary

Build a school library management system (BCD - Bibliothèque Centre Documentaire) with **API-first architecture**: a REST API core that will be consumed by a CLI interface initially, then web and desktop (Tauri) interfaces later. The system focuses on circulation operations (checkouts/returns via barcode scanning), cataloging with BNF SRU API integration, borrower management, and reporting. The system supports configurable ID formats (numeric/alphanumeric), configurable barcode types (Code 39/Code 128), and provides bilingual interface (French/English).

## Operational Model

**Librarian-Centric System**: This is a **librarian-operated system** where the librarian acts as the interface between students and the library system. Students do not have direct access to search or manage their accounts.

**Key Operational Constraints**:
- ✅ **Offline-first**: System operates fully offline except for BNF ISBN lookups during cataloging
- ✅ **No fines/fees**: System is completely free - no cost tracking, no overdue fines, no fee management
- ✅ **Librarian-mediated access**: All catalog searches, checkouts, returns, and holds are performed by the librarian
- ✅ **Privilege blocking**: Borrowers with overdue items are blocked from checking out new items (instead of fines)
- ✅ **Printed reports**: Overdue notifications distributed via printed reports (by class) - no email/SMS
- ✅ **Holds via librarian**: Students request holds through librarian who enters them in the system

**Out of Scope** (based on operational model):
- ❌ Student self-service catalog (OPAC)
- ❌ Fine/fee management and payment tracking
- ❌ Budget/acquisitions/purchase order management
- ❌ Email/SMS notifications (offline system)
- ❌ Remote access from student homes
- ❌ Online public catalog portal

## Technical Context

**Language/Version**: Python 3.11+
**Architecture**: API-first (REST API + CLI client)

**Primary Dependencies**:
- **API Layer**:
  - Web framework: FastAPI (async, automatic OpenAPI docs, type hints)
  - Database: SQLite (development) → PostgreSQL (production)
  - ORM: SQLAlchemy 2.0+
  - Migrations: Alembic
  - Validation: Pydantic (built into FastAPI)

- **CLI Client**:
  - CLI framework: Click (mature, well-documented)
  - HTTP client: httpx (async support for future)
  - Output formatting: Rich (tables, colors, progress bars)
  - Barcode scanning: Direct stdin input (hardware agnostic)

- **Shared/Services**:
  - Barcode generation: python-barcode
  - BNF API client: requests + pymarc (UNIMARC parsing)
  - PDF generation: ReportLab (barcode labels, reports)
  - i18n: gettext
  - CSV processing: Built-in csv module + pandas (validation)

**Storage**:
- SQLite (file-based, cross-platform, embedded)
- Migration path to PostgreSQL documented

**Testing**:
- pytest with pytest-cov
- pytest-asyncio (for FastAPI tests)
- Contract tests for BNF SRU API

**Target Platform**:
- Linux (primary) and Windows (secondary)
- Python 3.11+
- API: localhost (development) → network accessible (production)
- CLI: Command-line application

**Project Type**: API-first with CLI client (web/Tauri clients in future)

**Performance Goals**:
- API response time: <100ms for simple queries, <500ms for complex
- Checkout transaction: <30 seconds (2 items, includes barcode scanning)
- Return transaction: <20 seconds (5 items)
- Search: <2 seconds (5000 records)
- CSV import: <30 seconds (100 records)
- Report generation: <10 seconds (15 classes)

**Constraints**:
- Must run on legacy hardware (dual-core 2.0GHz, 4GB RAM, HDD)
- Memory footprint: ≤200MB (API) + ≤50MB (CLI)
- Database: 500 borrowers, 5000 items, 18000 transactions/year
- Offline operation for circulation (local API, no internet dependency)
- BNF API access only for cataloging

**Scale/Scope**:
- 500 borrowers
- 5000 bibliographic records with items
- ~500 circulation transactions/week
- 10-15 classes
- Bilingual (French/English)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality & DRY
**Status**: ✅ PASS (Pending Implementation)
- API and CLI share business logic (no duplication)
- ORM models avoid SQL duplication
- Shared validation in Pydantic models
- Constants in configuration files
- Reusable API endpoints for all clients

### II. Library-First Approach
**Status**: ✅ PASS
- FastAPI (mature async framework, reduces boilerplate by >40%)
- SQLAlchemy (mature ORM, cross-platform)
- Click (mature CLI framework)
- httpx (modern HTTP client)
- Rich (terminal formatting)
- python-barcode, pymarc, ReportLab (all industry standard)
- All libraries cross-platform compatible

### III. Comprehensive Testing Standards
**Status**: ✅ PASS (Pending Implementation)
- pytest for all tests
- 80% coverage target
- API contract tests
- CLI integration tests
- BNF API contract tests
- Cross-platform CI (Linux/Windows)

### IV. User Experience Consistency
**Status**: ✅ PASS (Pending Implementation)
- Consistent API responses (JSON, standard HTTP codes)
- Consistent CLI commands and flags
- Consistent error messages (bilingual)
- Rich terminal output (tables, colors)

### V. Click Minimization
**Status**: ✅ PASS
- Interactive mode with barcode scanner input
- Batch operations (CSV import)
- Smart defaults (configurable settings)
- Keyboard-driven workflows

### VI. Performance for Legacy Hardware
**Status**: ✅ PASS
- SQLite for minimal overhead
- Indexed queries
- Pagination (50/100 records)
- Async FastAPI (non-blocking I/O)
- Target: <250MB total memory

### VII. Database Schema Versioning & Migrations
**Status**: ✅ PASS (Pending Implementation)
- Alembic migrations
- Up/down scripts
- Sample data fixtures

### VIII. Research-First Feature Design
**Status**: ✅ PASS
- BCD/CDI standards researched
- BCDI, Koha, PMB schemas analyzed
- CSV format validated

### IX. Design-First Implementation
**Status**: ✅ PASS
- API contracts (OpenAPI/Swagger)
- CLI commands documented
- Database schema defined

### X. Internationalization
**Status**: ✅ PASS (Pending Implementation)
- gettext for API messages
- CLI output in French/English
- Locale-aware formatting

**Gate Decision**: ✅ **PROCEED** - No violations

## Project Structure

### Documentation (this feature)

```text
specs/001-school-library-system/
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions, BNF API, CSV mapping
├── data-model.md        # Phase 1: Complete database schema
├── quickstart.md        # Phase 1: CLI commands and API usage
├── contracts/           # Phase 1: API contracts
│   ├── api-spec.yaml   # OpenAPI 3.0 specification
│   └── bnf-sru-api.md  # BNF SRU API integration
└── tasks.md             # Phase 2: NOT created by /speckit.plan
```

### Source Code (repository root)

```text
src/
├── bcd_api/                       # API application (FastAPI)
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, CORS, startup
│   ├── api/                      # API endpoints (routers)
│   │   ├── __init__.py
│   │   ├── v1/                   # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── circulation.py   # POST /checkout, /return, /renew
│   │   │   ├── catalog.py       # GET /bibliographic, /items, POST /catalog
│   │   │   ├── borrowers.py     # CRUD /borrowers
│   │   │   ├── search.py        # GET /search
│   │   │   ├── reports.py       # GET /reports/overdue, /never-borrowed
│   │   │   ├── import_export.py # POST /import/borrowers, /import/catalog
│   │   │   └── admin.py         # Settings, backup, barcodes
│   │   └── deps.py              # Dependency injection (DB session)
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── borrower.py
│   │   ├── bibliographic.py     # Notice bibliographique
│   │   ├── item.py              # Exemplaire
│   │   ├── circulation.py       # Transaction de prêt
│   │   ├── class_.py
│   │   ├── hold.py
│   │   └── settings.py
│   ├── schemas/                  # Pydantic models (request/response)
│   │   ├── __init__.py
│   │   ├── borrower.py
│   │   ├── bibliographic.py
│   │   ├── item.py
│   │   ├── circulation.py
│   │   └── common.py            # Shared schemas (Pagination, etc.)
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── circulation_service.py
│   │   ├── catalog_service.py
│   │   ├── borrower_service.py
│   │   ├── bnf_service.py       # BNF SRU API integration
│   │   ├── import_service.py
│   │   ├── report_service.py
│   │   └── barcode_service.py
│   ├── core/                     # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py            # Settings (pydantic BaseSettings)
│   │   ├── database.py          # Database connection
│   │   └── i18n.py              # Internationalization
│   └── utils/                    # Helpers
│       ├── __init__.py
│       ├── validators.py
│       └── formatters.py

├── bcd_cli/                       # CLI application (Click)
│   ├── __init__.py
│   ├── main.py                   # CLI entry point, command groups
│   ├── client.py                 # HTTP client to API
│   ├── commands/                 # CLI command implementations
│   │   ├── __init__.py
│   │   ├── circulation.py       # checkout, return, renew
│   │   ├── catalog.py           # add, search, import
│   │   ├── borrowers.py         # add, list, import
│   │   ├── reports.py           # overdue, stats
│   │   └── admin.py             # settings, backup
│   ├── interactive/              # Interactive modes
│   │   ├── __init__.py
│   │   ├── scanner.py           # Barcode scanner input handler
│   │   └── workflows.py         # Multi-step interactive flows
│   └── utils/                    # CLI utilities
│       ├── __init__.py
│       ├── output.py            # Rich formatting, tables
│       └── i18n.py              # Translation helpers

├── shared/                        # Shared between API and CLI
│   ├── __init__.py
│   └── constants.py              # Shared constants

migrations/                        # Alembic migrations
├── versions/
│   └── 001_initial_schema.py
└── alembic.ini

tests/
├── conftest.py                    # Pytest fixtures
├── api/                           # API tests
│   ├── test_circulation_api.py
│   ├── test_catalog_api.py
│   └── test_borrowers_api.py
├── cli/                           # CLI tests
│   ├── test_checkout_cli.py
│   └── test_import_cli.py
├── integration/                   # End-to-end tests
│   └── test_checkout_workflow.py
├── contract/                      # Contract tests
│   └── test_bnf_api.py
└── unit/                          # Unit tests
    └── services/
        └── test_circulation_service.py

data/                              # Sample/seed data
├── sample_borrowers.csv
├── sample_bibliographic.csv
└── fixtures.sql

locale/                            # Translation files
├── en/LC_MESSAGES/bcd.po
└── fr/LC_MESSAGES/bcd.po

docs/
├── api_guide.md                   # API documentation
├── cli_guide.md                   # CLI user guide
└── deployment.md                  # Deployment guide

requirements/
├── base.txt                       # Shared dependencies
├── api.txt                        # API-specific
└── cli.txt                        # CLI-specific

pyproject.toml                     # Project config (Poetry or setuptools)
README.md
.gitignore
```

**Structure Decision**: API-first architecture with separate `bcd_api/` (FastAPI server) and `bcd_cli/` (Click client) packages. The CLI communicates with the API via HTTP, enabling future web/Tauri clients to use the same API. Shared code in `shared/` package.

## Complexity Tracking

> **No violations**

## Phase 0: Research Tasks

**Objective**: Resolve technical unknowns, document decisions

### Research Tasks

1. **API Architecture Decision**
   - Validate FastAPI vs Flask for async performance
   - Document API versioning strategy (/api/v1/)
   - Design authentication strategy (future: API keys/JWT)

2. **CLI-to-API Communication**
   - Document localhost API endpoint configuration
   - Error handling for API unavailable scenarios
   - Offline mode strategy (local cache vs embedded API)

3. **BNF SRU API Integration**
   - Endpoint: `https://catalogue.bnf.fr/api/SRU`
   - Request format: SRU protocol with ISBN query
   - Response: UnimarcXchange (UNIMARC XML)
   - Rate limits, error codes
   - pymarc library for parsing

4. **CSV Import Mapping**
   - Analyze provided CSVs (students_import.csv, 2025-10-17-notices-et-exemplaires.csv)
   - Map all 21 fields to database schema
   - Document validation rules
   - Error handling strategy

5. **Barcode Configuration**
   - Code 39 vs Code 128 trade-offs
   - Configuration in settings table
   - python-barcode library capabilities

6. **ID Configuration Strategy**
   - Numeric-only vs alphanumeric
   - Validation rules per configuration
   - Database schema (VARCHAR vs INT)
   - Migration strategy if changing format

7. **Interactive Scanner Mode**
   - Design barcode scanner input (stdin)
   - Buffering and debouncing strategy
   - Error detection (invalid scans)
   - Timeout handling

**Output**: `research.md` with all decisions documented

## Phase 1: Design Artifacts

### 1. Data Model (`data-model.md`)

Based on [BCDI structure](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/college-lycee/module_5_2_2.htm) and CSV analysis:

**Core Entities**:

1. **BiblographicRecord** (Notice bibliographique)
   - Fields from bibliographic description + documentary analysis
   - All fields from CSV: titre, sous_titre, auteur, illustrateur, editeur, collection, numero, annee, isbn, rubrique, genre, niveau, support, mots_clefs, description, taille

2. **Item** (Exemplaire)
   - inventory_number (Inventaire) - configurable ID format
   - call_number (Cote) - Dewey/CDU classification
   - shelf_location - physical shelf location (e.g., "Shelf A-3", "Fiction Row 2")
   - bibliographic_record_id (FK)
   - condition, availability
   - acquisition_date (Date achat)
   - funding_source (Financement)
   - loanable (Empruntable)

3. **Borrower** (Emprunteur)
   - borrower_id - configurable ID format
   - name, role (student/teacher/staff)
   - class_id (FK, optional)
   - barcode
   - active status

4. **CirculationTransaction** (Prêt)
   - Links Item + Borrower
   - checkout_date, due_date, return_date
   - renewal_count

5. **Class** (Classe)
6. **Hold** (Réservation)
7. **SystemSettings** (Paramètres)
   - Configurable values: ID format, barcode type, loan limits, loan duration

**Requirements**:
- Configurable ID formats (regex validation)
- Proper indexes
- Foreign keys
- Audit timestamps

### 2. API Contracts (`contracts/api-spec.yaml`)

**OpenAPI 3.0 Specification** covering:

**Circulation Endpoints**:
```
POST /api/v1/circulation/checkout
  Request: {borrower_id, item_ids: []}
  Response: {transaction_ids: [], due_dates: []}

POST /api/v1/circulation/return
  Request: {item_ids: []}
  Response: {returned: [{item_id, return_date, was_overdue, days_overdue}]}

GET /api/v1/circulation/borrower/{borrower_id}/items
  Response: {items: [{item_id, title, due_date, days_overdue, can_renew, ...}]}

POST /api/v1/circulation/renew
  Request: {item_ids: []}  # Select which items to renew
  Response: {renewed: [{item_id, new_due_date}], errors: [{item_id, reason}]}

GET /api/v1/circulation/item/{item_id}/history
  Response: {current_borrower: {...}, history: [{borrower, checkout_date, return_date}]}

GET /api/v1/circulation/borrower/{borrower_id}/history
  Response: {current: [...], history: [...]}
```

**Hold/Reservation Endpoints** (librarian-mediated):
```
POST /api/v1/holds
  Request: {borrower_id, bibliographic_record_id}
  Response: {hold_id, queue_position, estimated_availability}

GET /api/v1/holds/bibliographic/{biblio_id}
  Response: {holds: [{borrower_id, borrower_name, hold_date, queue_position}]}

GET /api/v1/holds/borrower/{borrower_id}
  Response: {holds: [{bibliographic_record_id, title, queue_position, status}]}

DELETE /api/v1/holds/{hold_id}
  Response: {success: true}

GET /api/v1/holds/ready-for-pickup
  Response: {holds: [{hold_id, borrower, title, available_date, expires_in_days}]}
```

**Catalog Endpoints**:
```
POST /api/v1/catalog/bibliographic
  Request: {isbn?, manual_entry?}
  Response: BiblographicRecord

GET /api/v1/catalog/bibliographic/{id}
GET /api/v1/catalog/bibliographic/search?q=...
POST /api/v1/catalog/import  # CSV import
```

**Borrower Endpoints**:
```
POST /api/v1/borrowers
GET /api/v1/borrowers
GET /api/v1/borrowers/{id}
POST /api/v1/borrowers/import  # CSV import
```

**Report Endpoints**:
```
GET /api/v1/reports/overdue?class_id=...
GET /api/v1/reports/never-borrowed
GET /api/v1/reports/most-borrowed
```

**Admin Endpoints**:
```
GET /api/v1/admin/settings
PUT /api/v1/admin/settings
POST /api/v1/admin/backup
POST /api/v1/admin/barcodes/generate
```

### 3. BNF SRU API Contract (`contracts/bnf-sru-api.md`)

- Endpoint, authentication
- Request/response examples
- Error handling
- UNIMARC field mappings

### 4. CLI Quickstart (`quickstart.md`)

**Command Structure**:

```bash
# Start API server (development)
bcd-api serve --port 8000

# CLI commands (call API)

## Interactive Mode (barcode scanner)
bcd checkout          # Interactive: scan borrower, then items
bcd return            # Interactive: scan items

## Direct Mode
bcd checkout <borrower-id> <item-id> [<item-id> ...]
bcd return <item-id> [<item-id> ...]
bcd renew <borrower-id>  # Interactive: shows items, select which to renew

## Cataloging
bcd catalog add --isbn <isbn>          # BNF lookup
bcd catalog add --manual               # Manual entry (interactive form)
bcd catalog import <csv-file>
bcd catalog search --title "<title>"
bcd catalog search --author "<author>"
bcd catalog search --call-number "<cote>"

## Borrowers
bcd borrower add --name "<name>" --class "<class>"
bcd borrower import <csv-file>
bcd borrower list [--class <class>]
bcd borrower current <borrower-id>     # Current loans (shows overdue status)
bcd borrower history <borrower-id>     # Full circulation history

## Items
bcd item status <item-id>              # Current status and borrower
bcd item history <item-id>             # Circulation history (who borrowed)

## Holds/Reservations (librarian-mediated)
bcd hold add <borrower-id> <biblio-id>  # Place hold for student
bcd hold list <borrower-id>             # Show borrower's holds
bcd hold list-for-title <biblio-id>     # Show all holds for a title
bcd hold cancel <hold-id>               # Cancel a hold
bcd hold ready                          # Show items ready for pickup

## Reports (PDF/CSV export)
bcd report overdue [--class <class>] [--format pdf]
bcd report never-borrowed
bcd report most-borrowed [--limit 20]

## Admin
bcd admin settings [--set key=value]
bcd admin backup [--output <file>]
bcd admin barcode-generate --borrowers <ids> --output <pdf>
bcd admin barcode-generate --items <ids> --output <pdf>

## Configuration
bcd config --api-url http://localhost:8000
bcd config --language fr|en
```

**Interactive Scanner Mode**:
- Prompt for barcode input
- Timeout after 30 seconds
- Visual feedback (Rich progress bar)
- Error handling (invalid barcodes, not found)

## Configuration System

**SystemSettings Table** (database):
- `id_format`: "numeric" | "alphanumeric"
- `id_validation_regex`: Validation pattern
- `barcode_type`: "code39" | "code128"
- `loan_limit_default`: 2
- `loan_duration_days`: 14
- `language`: "fr" | "en"

**Validation**:
- IDs validated against configured regex
- Numeric mode: `^\d+$`
- Alphanumeric mode: `^[A-Z0-9]+$` (customizable)

## CSV Import Mappings

**Borrowers** (from students_import.csv):
```
StudentID → borrower_id
FirstName + LastName → full_name
Class → class
BlockReason → notes/blocked flag
```

**Bibliographic + Items** (from 2025-10-17-notices-et-exemplaires.csv):
```
# Bibliographic Record fields:
Titre → title
SousTitre → subtitle
ISBN → isbn
Auteur → authors
Illustrateur → illustrators
Annee → publication_year
Editeur → publisher
Collection → collection
Numero → series_number
Rubrique → category
Genre → genre
Niveau → level (reading level)
Support → medium_type (Livre, CD, DVD, etc.)
Mots-clefs → keywords
Description → description
Taille → physical_size

# Item (Exemplaire) fields:
Inventaire → item_id (inventory number)
Cote → call_number (Dewey/CDU classification)
Date achat → acquisition_date
Financement → funding_source
Empruntable → loanable (Oui/Non → boolean)
```

## Implementation Notes

### API-First Benefits
- ✅ CLI, web, Tauri all use same API
- ✅ Business logic in one place
- ✅ Easier testing (API contract tests)
- ✅ Future scalability (network API)

### Interactive Scanner Workflow

**Checkout Flow**:
```
$ bcd checkout
📖 BCD Library - Checkout
Scan borrower ID: [waiting for barcode scanner input]
> 101
✓ Borrower: Amira BENALI (CP-A)
  Current loans: 0/2

Scan item barcode (Enter to finish): [waiting]
> 785
✓ Added: Ils ont arrêté mon père
Scan item barcode (Enter to finish): [waiting]
> 787
✓ Added: Stuart Little
Scan item barcode (Enter to finish): [Enter pressed]

Checkout Summary:
┌─────────┬────────────────────────┬──────────────┐
│ Item ID │ Title                  │ Due Date     │
├─────────┼────────────────────────┼──────────────┤
│ 785     │ Ils ont arrêté mon...  │ 2026-02-13   │
│ 787     │ Stuart Little          │ 2026-02-13   │
└─────────┴────────────────────────┴──────────────┘

Confirm checkout? [Y/n]: Y
✅ 2 items checked out to Amira BENALI
```

### Barcode Configuration

**Settings API**:
```python
PUT /api/v1/admin/settings
{
  "barcode_type": "code39",  # or "code128"
  "id_format": "numeric",     # or "alphanumeric"
  "loan_limit_default": 2,
  "loan_duration_days": 14
}
```

### ID Format Flexibility

**Database Schema**:
- Use VARCHAR for all IDs (supports both numeric and alphanumeric)
- Add validation constraints based on settings
- Migration notes if changing format

## Next Steps

1. Complete Phase 0: `research.md`
2. Complete Phase 1: `data-model.md`, `contracts/`, `quickstart.md`
3. Run `/speckit.tasks` for implementation tasks
4. Implement in order:
   - Setup: Project structure, database
   - API: Core endpoints (circulation, catalog, borrowers)
   - CLI: Commands calling API
   - Integration: BNF SRU API, CSV import
   - Reports: PDF generation

## Dependencies

**API (requirements/api.txt)**:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
alembic>=1.12.0
pydantic>=2.0.0
python-barcode>=0.15.0
pymarc>=4.2.0
reportlab>=4.0.0
requests>=2.31.0
pandas>=2.1.0
```

**CLI (requirements/cli.txt)**:
```
click>=8.1.0
httpx>=0.25.0
rich>=13.0.0
```

**Both**:
```
-r base.txt

# base.txt:
python-dateutil>=2.8.0
pytz>=2023.3
```

## Sources

- [BCDI database structure](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/college-lycee/module_5_2_2.htm)
- [Koha item records](http://manual.koha-community.org/3.6/en/catitems.html)
- [Dewey Decimal Classification](https://en.wikipedia.org/wiki/Dewey_Decimal_Classification)
- [UNIMARC format](https://www.ifla.org/unimarc-updates/unimarc-bibliographic-3rd-edition-with-updates/)
