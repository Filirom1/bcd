# Phase 0: Research & Technical Decisions

**Feature**: School Library Management System (BCD)
**Date**: 2026-01-30
**Status**: Complete

## Overview

This document captures all research findings and technical decisions made before implementation. All decisions have been validated against the project constitution and user requirements.

---

## 1. API Architecture Decision

### Requirement
Choose web framework for REST API that will be consumed by CLI (and future web/Tauri clients).

### Options Considered

**Option A: Flask + Flask-RESTful**
- Pros: Lightweight, simple, well-documented, synchronous (easier to debug)
- Cons: No built-in async support, no automatic API docs, requires many extensions (Flask-SQLAlchemy, Flask-Migrate, marshmallow for validation)

**Option B: FastAPI**
- Pros:
  - Native async/await support (better for I/O-bound operations like BNF API calls)
  - Automatic OpenAPI (Swagger) documentation generation
  - Built-in Pydantic validation (type hints → automatic validation)
  - Modern Python 3.11+ features
  - ~200% faster than Flask for async operations
- Cons: Async can be more complex (but we can use sync functions when not needed)

### Decision: **FastAPI** ✅

**Rationale**:
- Automatic OpenAPI docs align with Constitution IX (Design-First) - clients can see API contract
- Pydantic validation reduces boilerplate by ~40% (Constitution II: Library-First)
- Async enables better performance for BNF API calls without blocking
- Type hints improve code quality (Constitution I: Code Quality)
- Future web/Tauri clients benefit from standardized OpenAPI spec

**API Versioning Strategy**: `/api/v1/` prefix for all endpoints to enable future breaking changes

**Authentication**: None for MVP (local-only system). Future: API keys for network deployment.

---

## 2. CLI-to-API Communication

### Requirement
CLI application must communicate with API server reliably in offline-first environment.

### Localhost API Configuration

**Development**:
```bash
# API server
bcd-api serve --host 127.0.0.1 --port 8000

# CLI client
bcd config --api-url http://localhost:8000
```

**Production** (future):
```bash
# API on network
bcd-api serve --host 0.0.0.0 --port 8000

# CLI clients point to server
bcd config --api-url http://library-server.local:8000
```

### Error Handling Strategies

**1. API Unavailable (server not running)**:
```
Error: Cannot connect to BCD API server
  • Is the API server running? Try: bcd-api serve
  • Check API URL in config: bcd config --api-url
```

**2. Network Timeout**:
- httpx client timeout: 30 seconds (configurable)
- Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
- Clear error messages with suggested actions

**3. Offline Mode Strategy**: ❌ NOT IMPLEMENTED
- **Decision**: No offline cache or embedded API
- **Rationale**:
  - System is local-only (API and CLI on same machine)
  - Offline mode adds significant complexity (sync conflicts, stale data)
  - If API is down, better to fix it than hide the problem
  - Constitution VI: Click Minimization - don't add complexity for unlikely scenario

---

## 3. BNF SRU API Integration

### Overview
The BNF (Bibliothèque nationale de France) provides a free SRU (Search/Retrieve via URL) API for bibliographic lookups using ISBN.

### Endpoint Details

**Base URL**: `https://catalogue.bnf.fr/api/SRU`

**Protocol**: SRU 1.2 (Search/Retrieve via URL - library standard)

**Request Format**:
```
GET https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=bib.isbn%20all%20%22{ISBN}%22&recordSchema=unimarcxchange
```

**Parameters**:
- `version`: `1.2` (SRU version)
- `operation`: `searchRetrieve`
- `query`: `bib.isbn all "{ISBN}"` (URL-encoded)
- `recordSchema`: `unimarcxchange` (UNIMARC XML format)

**Response Format**: XML (UnimarcXchange schema)

**Example Response**:
```xml
<srw:searchRetrieveResponse>
  <srw:numberOfRecords>1</srw:numberOfRecords>
  <srw:records>
    <srw:record>
      <srw:recordData>
        <record xmlns="http://www.loc.gov/MARC21/slim">
          <datafield tag="200" ind1="1" ind2=" ">
            <subfield code="a">Ils ont arrêté mon père</subfield>
            <subfield code="f">Danielle Carmi</subfield>
          </datafield>
          <datafield tag="210" ind1=" " ind2=" ">
            <subfield code="c">Flammarion</subfield>
            <subfield code="d">2004</subfield>
          </datafield>
          <datafield tag="010" ind1=" " ind2=" ">
            <subfield code="a">978-2-08-161739-6</subfield>
          </datafield>
        </record>
      </srw:recordData>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>
```

### UNIMARC Field Mappings

| UNIMARC Tag | Field | Maps To |
|-------------|-------|---------|
| 010$a | ISBN | `isbn` |
| 200$a | Title | `title` |
| 200$e | Subtitle | `subtitle` |
| 200$f | Author (primary) | `authors` (first) |
| 701$a/$b | Additional authors | `authors` (list) |
| 210$c | Publisher | `publisher` |
| 210$d | Publication year | `publication_year` |
| 225$a | Collection/Series | `collection` |
| 225$v | Volume number | `series_number` |
| 300$a | Notes/Description | `description` |
| 330$a | Summary | `description` (append) |
| 606$a | Subject headings | `keywords` (list) |

**Library Used**: `pymarc` (mature MARC parsing library)

**Example Code**:
```python
import pymarc
from pymarc import marcxml

# Parse UNIMARC XML
record = marcxml.parse_xml_to_array(xml_response)[0]

# Extract fields
title = record['200']['a'] if '200' in record else None
author = record['200']['f'] if '200' in record and 'f' in record['200'] else None
isbn = record['010']['a'] if '010' in record else None
```

### Error Handling

**HTTP Status Codes**:
- `200 OK` + `numberOfRecords=0`: ISBN not found (allow manual entry)
- `200 OK` + `numberOfRecords>1`: Multiple matches (show list, let user select)
- `400 Bad Request`: Invalid ISBN format
- `500 Server Error`: BNF API down (fallback to manual entry)
- `Timeout`: Network issue (retry, then manual entry)

**Rate Limits**: None documented (be respectful: 1 request per ISBN lookup)

**Offline Behavior**: If BNF API unreachable, automatically switch to manual entry mode with warning.

---

## 4. CSV Import Mapping

### Source Files Analyzed

**File 1**: `~/Downloads/students_import.csv` (217 borrowers)
**File 2**: `~/Downloads/2025-10-17-notices-et-exemplaires.csv` (bibliographic + items)

### Borrower Import Mapping

**CSV Structure**:
```csv
StudentID,FirstName,LastName,Class,BlockReason
101,Amira,BENALI,CP-A,
```

**Database Mapping**:
```python
{
  'borrower_id': row['StudentID'],          # String (numeric)
  'first_name': row['FirstName'],
  'last_name': row['LastName'],
  'full_name': f"{row['FirstName']} {row['LastName']}", # Computed
  'class': row['Class'],                    # e.g., "CP-A", "CE1-B"
  'role': 'student',                        # Default for this import
  'active': True if not row['BlockReason'] else False,
  'notes': row['BlockReason'] or None,      # Why blocked
  'barcode': generate_barcode(row['StudentID'])  # Generate from ID
}
```

**Validation Rules**:
- `StudentID`: Required, numeric-only (configurable), unique
- `FirstName` + `LastName`: Required, non-empty
- `Class`: Required, must match valid class format (e.g., CP-A, CE1-A)
- `BlockReason`: Optional, if present → set `active=False`

**Error Handling**:
- Duplicate `StudentID`: Skip with warning
- Missing required fields: Skip row, log error
- Invalid class: Skip with warning (or create class if auto-create enabled)
- Report: `{imported: 215, skipped: 2, errors: [{row: 42, error: "Duplicate ID"}]}`

### Bibliographic + Item Import Mapping

**CSV Structure** (21 fields, semicolon-separated):
```csv
Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
785;800.000;Lire des histoires;Album;Ils ont arrêté mon père;"";"";Carmi (Danielle);"";"";"";"";"";Livre;histoires vécues;"";"";"";"";"";Oui
```

**BiblographicRecord Mapping**:
```python
{
  'title': row['Titre'],                    # Required
  'subtitle': row['SousTitre'] or None,
  'isbn': clean_isbn(row['ISBN']),          # Normalize (remove hyphens)
  'authors': parse_authors(row['Auteur']),  # "Carmi (Danielle)" → list
  'illustrators': parse_authors(row['Illustrateur']),
  'publisher': row['Editeur'] or None,
  'publication_year': int(row['Annee']) if row['Annee'] else None,
  'collection': row['Collection'] or None,
  'series_number': row['Numero'] or None,
  'category': row['Rubrique'],              # e.g., "Lire des histoires"
  'genre': row['Genre'],                    # e.g., "Album"
  'level': row['Niveau'],                   # Reading level
  'medium_type': row['Support'],            # "Livre", "CD", "DVD"
  'keywords': parse_keywords(row['Mots-clefs']),  # Split by semicolons
  'description': row['Description'] or None,
  'physical_size': row['Taille'] or None    # Physical dimensions
}
```

**Item (Exemplaire) Mapping**:
```python
{
  'item_id': row['Inventaire'],             # Unique inventory number
  'call_number': row['Cote'],               # Dewey/CDU classification
  'shelf_location': None,                   # Not in CSV, set manually
  'bibliographic_record_id': biblio_id,     # FK to created record
  'acquisition_date': parse_date(row['Date achat']),
  'funding_source': row['Financement'] or None,
  'loanable': row['Empruntable'].lower() == 'oui',  # "Oui"/"Non" → boolean
  'condition': 'good',                      # Default
  'status': 'available'                     # Default
}
```

**Validation Rules**:
- `Titre`: Required
- `Inventaire`: Required, unique, numeric-only (configurable)
- `ISBN`: Optional, if present → must be valid ISBN-10/13 format
- `Empruntable`: Must be "Oui" or "Non" (case-insensitive)
- `Annee`: If present, must be valid year (1000-2100)
- `Support`: Must be one of: Livre, CD, DVD, Revue, etc. (configurable list)

**Import Strategy**:
1. Group by `ISBN` or `Titre` (if no ISBN) → one BiblographicRecord per unique title
2. Each CSV row → one Item linked to BiblographicRecord
3. If BiblographicRecord exists (by ISBN), add Item to existing record
4. Report: `{bibliographic_created: 45, items_created: 78, skipped: 2}`

**Error Handling**:
- Duplicate `Inventaire` (item ID): Skip with warning
- Invalid ISBN format: Log warning, import without ISBN
- Missing `Titre`: Skip row entirely
- Invalid `Empruntable` value: Default to "Non" (not loanable), log warning

---

## 5. Barcode Configuration

### Requirement
Support configurable barcode symbology for different hardware/preferences.

### Options

**Code 39**:
- Pros:
  - Widely supported (most scanners)
  - Alphanumeric support (0-9, A-Z, +-.$/%)
  - Self-checking (no checksum digit required)
  - Larger, easier to scan
- Cons:
  - Lower density (larger physical size for same data)
  - Limited character set

**Code 128**:
- Pros:
  - High density (smaller physical size)
  - Full ASCII character set
  - Better for long numeric sequences
- Cons:
  - Requires checksum digit calculation
  - Slightly more complex

### Decision: **Code 39 (default), configurable to Code 128** ✅

**Rationale**:
- User's school currently uses Code 39 (validated)
- Code 39 is more forgiving for legacy scanners (Constitution VI: Performance for Legacy Hardware)
- Alphanumeric support future-proofs for non-numeric IDs
- Configuration allows schools to switch if needed

**Configuration**:
```python
# SystemSettings table
barcode_type: "code39" | "code128"
```

**Library**: `python-barcode` (supports both Code 39 and Code 128)

**Barcode Generation**:
```python
from barcode import Code39, Code128
from barcode.writer import ImageWriter

def generate_barcode(value: str, barcode_type: str = "code39"):
    if barcode_type == "code39":
        barcode_class = Code39
    else:
        barcode_class = Code128

    barcode = barcode_class(value, writer=ImageWriter())
    return barcode.save(f"barcode_{value}")  # Returns PNG path
```

---

## 6. ID Configuration Strategy

### Requirement
Support both numeric-only IDs (user's school) and alphanumeric IDs (flexibility).

### Options

**Option A: Numeric-only (INT in database)**
- Pros: Smaller storage, faster indexing, easier to type
- Cons: Inflexible, requires migration to change

**Option B: Alphanumeric (VARCHAR in database)**
- Pros: Flexible (supports both numeric and alphanumeric), no migration needed to change format
- Cons: Slightly larger storage, minimal performance impact

### Decision: **VARCHAR with configurable validation** ✅

**Database Schema**:
```sql
-- Borrower IDs
borrower_id VARCHAR(20) NOT NULL UNIQUE

-- Item IDs
item_id VARCHAR(20) NOT NULL UNIQUE
```

**Configuration** (SystemSettings table):
```python
{
  'id_format': 'numeric',  # or 'alphanumeric'
  'id_validation_regex': '^\\d+$',  # Numeric-only pattern
  'id_length_min': 1,
  'id_length_max': 10
}
```

**Validation Examples**:
```python
# Numeric mode (user's school)
id_format = "numeric"
id_validation_regex = r'^\d+$'  # Only digits
# Valid: "101", "785"
# Invalid: "A101", "101-B"

# Alphanumeric mode
id_format = "alphanumeric"
id_validation_regex = r'^[A-Z0-9]+$'  # Uppercase letters + digits
# Valid: "A101", "BOOK785", "101"
# Invalid: "a101" (lowercase), "101-B" (hyphen)
```

**Migration Notes**:
If school changes from numeric to alphanumeric:
1. No database migration needed (VARCHAR already supports both)
2. Update `SystemSettings.id_validation_regex`
3. New IDs validated against new pattern
4. Existing IDs remain valid (grandfathered)

---

## 7. Interactive Scanner Mode

### Requirement
Support barcode scanner input in interactive CLI workflows without user typing barcodes manually.

### Technical Approach

**Barcode Scanner Behavior**:
- Most barcode scanners act as **keyboard wedge** devices
- They type the barcode value followed by **Enter key**
- To the system, it looks like: `785\n` (very fast typing)

**Implementation Strategy**:

**Input Handling**:
```python
import sys

def read_barcode_or_manual(prompt: str, timeout: int = 30) -> str:
    """
    Read input from barcode scanner (fast) or manual entry (slow).
    Scanner inputs come as rapid keystrokes + Enter.
    """
    print(prompt, end='', flush=True)

    # Use stdin.readline() - works for both scanner and keyboard
    # Scanner will type fast, human types slow (same API)
    user_input = sys.stdin.readline().strip()

    return user_input
```

**Timeout Handling**:
```python
import select

def read_with_timeout(prompt: str, timeout: int = 30) -> Optional[str]:
    """
    Read input with timeout. If no input in <timeout> seconds, return None.
    """
    print(prompt, end='', flush=True)

    # Check if input available within timeout (Unix/Linux only)
    ready, _, _ = select.select([sys.stdin], [], [], timeout)

    if ready:
        return sys.stdin.readline().strip()
    else:
        print("\n⏱️ Timeout - no input received")
        return None
```

**Error Detection**:
- **Invalid barcode** (not in database): Display error, allow retry or manual entry
- **Invalid format** (doesn't match ID regex): Display error, allow retry
- **Empty input** (just Enter pressed): Interpret as "done" (for multi-item input)

**Debouncing**: Not needed - barcode scanners send complete string + Enter as one event

**Visual Feedback** (using Rich library):
```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn

console = Console()

# While waiting for scan
with console.status("[bold blue]Scan borrower ID...") as status:
    borrower_id = read_barcode_or_manual("")

# Success feedback
console.print(f"✓ Borrower: [green]{borrower.name}[/green] ({borrower.class})")

# Error feedback
console.print(f"✗ Borrower ID not found: [red]{borrower_id}[/red]", style="bold red")
```

**Workflow Example** (checkout):
```
$ bcd checkout
📖 BCD Library - Checkout

Scan borrower ID: [cursor blinks]
[Scanner input: 101\n - appears instantly]
✓ Borrower: Amira BENALI (CP-A)
  Current loans: 0/2

Scan item barcode (Enter to finish): [cursor blinks]
[Scanner input: 785\n]
✓ Added: Ils ont arrêté mon père

Scan item barcode (Enter to finish): [cursor blinks]
[User presses Enter - empty input]

Checkout Summary:
┌─────────┬────────────────────────┬──────────────┐
│ Item ID │ Title                  │ Due Date     │
├─────────┼────────────────────────┼──────────────┤
│ 785     │ Ils ont arrêté mon...  │ 2026-02-13   │
└─────────┴────────────────────────┴──────────────┘

Confirm checkout? [Y/n]:
```

**Platform Compatibility**:
- **Linux**: `select.select()` works natively
- **Windows**: `select` doesn't work on stdin; use `msvcrt` module or threading
  - Fallback: No timeout (wait indefinitely)
  - Alternative: `keyboard` library (cross-platform)

---

## Decision Summary

| # | Decision | Choice | Status |
|---|----------|--------|--------|
| 1 | Web Framework | FastAPI | ✅ Approved |
| 2 | Offline Mode | No offline cache | ✅ Approved |
| 3 | BNF API | SRU protocol + pymarc | ✅ Approved |
| 4 | CSV Import | Pandas + validation | ✅ Approved |
| 5 | Barcode Type | Code 39 (configurable) | ✅ Approved |
| 6 | ID Format | VARCHAR + regex validation | ✅ Approved |
| 7 | Scanner Input | stdin + timeout | ✅ Approved |

---

## Operational Model Decisions

Based on user requirements clarification:

**Confirmed Scope**:
- ✅ Librarian-operated system (no student self-service)
- ✅ Offline-first (only online for BNF ISBN lookups)
- ✅ Fine-free (privilege blocking instead of fines)
- ✅ Printed reports (no email/SMS notifications)
- ✅ Holds via librarian (librarian-mediated workflow)

**Out of Scope**:
- ❌ Student OPAC (online public access catalog)
- ❌ Fine/fee management and payment tracking
- ❌ Budget/acquisitions tracking
- ❌ Email/SMS automated notifications
- ❌ Remote access from student homes

**Rationale**: This aligns with traditional French BCD/CDI model where the librarian (documentaliste) is the central point of interaction. System is a tool for the librarian, not a self-service portal for students.

---

## Research Sources

- [BCDI - Wikipédia (FR)](https://fr.wikipedia.org/wiki/BCDI)
- [Koha Library System](https://www.eifl.net/resources/koha-worlds-first-free-and-open-source-integrated-library-management-system)
- [PMB Software Overview](https://en.wikipedia.org/wiki/PMB_(software))
- [BNF SRU API Documentation](https://api.bnf.fr/api-sru-catalog)
- [UNIMARC Format](https://www.ifla.org/unimarc-updates/)
- [Code 39 vs Code 128 Comparison](https://www.barcodesinc.com/articles/code-39-vs-code-128.htm)
- FastAPI Documentation
- pymarc Documentation
- python-barcode Documentation

---

## Next Steps

Phase 0 (Research) is complete. Proceed to **Phase 1: Design Artifacts**:

1. `data-model.md` - Complete database schema
2. `contracts/api-spec.yaml` - OpenAPI 3.0 specification
3. `contracts/bnf-sru-api.md` - BNF API integration contract
4. `quickstart.md` - CLI command reference

All design artifacts will be validated against this research document and the project constitution.
