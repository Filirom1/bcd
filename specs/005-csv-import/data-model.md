# Data Model: CSV Import/Export

**Feature**: 005-csv-import
**Created**: 2026-02-06
**Status**: Planning Phase

## Overview

This feature adds CSV export to complement the existing import functionality. **No database schema changes required** - the feature uses existing `BiblographicRecord` and `Item` models with their current VARCHAR fields.

## Key Architectural Decision: Plain Text Storage

**Medium types are stored as plain text VARCHAR** (not normalized, no foreign keys, no lookup tables).

**Why this works**:
- Import preserves exact values: "Livre", "Book", "CD Audio", "Périodique"
- Export outputs exact database values (round-trip fidelity)
- Filtering works: `WHERE medium_type = 'Livre'`
- Supports multilingual: French schools use "Livre", Italian schools use "Libro"
- No data loss or transformation
- Auto-complete dropdowns populated from `SELECT DISTINCT medium_type`

**Rejected alternative**: Normalized lookup tables (abandoned in spec 004-import-export as over-engineered).

## Existing Database Schema

### BiblographicRecord Model (No Changes)

Current production schema in `src/bcd_api/models/bibliographic_record.py`:

```python
class BiblographicRecord(Base):
    __tablename__ = "bibliographic_record"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    isbn = Column(String(20), nullable=True, index=True)

    # Title information
    title = Column(String(200), nullable=False, index=True)
    subtitle = Column(String(200), nullable=True)

    # Creators (stored as JSON arrays)
    authors = Column(Text, nullable=True)  # JSON: ["Author 1", "Author 2"]
    illustrators = Column(Text, nullable=True)  # JSON: ["Illustrator 1"]

    # Publication information
    publisher = Column(String(100), nullable=True)
    publication_year = Column(Integer, nullable=True, index=True)
    collection = Column(String(100), nullable=True)
    series_number = Column(String(20), nullable=True)

    # Language and format
    language = Column(String(10), nullable=True, index=True)
    country_code = Column(String(2), nullable=True)
    binding_type = Column(String(50), nullable=True)

    # Classification and categorization
    category = Column(String(50), nullable=True, index=True)
    genre = Column(String(50), nullable=True, index=True)
    level = Column(String(50), nullable=True)
    medium_type = Column(String(50), nullable=True, index=True)  # ← Plain text!
    target_audience = Column(String(20), nullable=True, index=True)

    # Subject and description
    keywords = Column(Text, nullable=True)  # JSON: ["keyword1", "keyword2"]
    description = Column(Text, nullable=True)

    # Physical characteristics
    page_count = Column(Integer, nullable=True)
    has_illustrations = Column(Boolean, nullable=True)
    dimensions = Column(String(50), nullable=True)
    physical_size = Column(String(50), nullable=True)

    # Statistics (denormalized for performance)
    total_items = Column(Integer, default=0)
    total_circulations = Column(Integer, default=0)
    last_borrowed_at = Column(DateTime, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("Item", back_populates="bibliographic_record")
```

### Item Model (No Changes)

Current production schema in `src/bcd_api/models/item.py`:

```python
class Item(Base):
    __tablename__ = "item"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Inventory identification
    item_id = Column(String(50), nullable=False, unique=True, index=True)

    # Foreign key to bibliographic record
    bibliographic_record_id = Column(Integer, ForeignKey("bibliographic_record.id"), nullable=False, index=True)

    # Location and classification
    call_number = Column(String(50), nullable=True)
    shelf_location = Column(String(100), nullable=True)

    # Item status
    condition = Column(String(20), nullable=True)  # good, damaged, lost, withdrawn
    status = Column(String(20), nullable=True, index=True)  # available, on_loan, etc.
    loanable = Column(Boolean, default=True)

    # Acquisition information
    acquisition_date = Column(Date, nullable=True)
    funding_source = Column(String(100), nullable=True)

    # Statistics
    circulation_count = Column(Integer, default=0)
    last_borrowed_at = Column(DateTime, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bibliographic_record = relationship("BiblographicRecord", back_populates="items")
```

## CSV Data Mapping

### Dublin Core → Database (Import - Already Implemented)

Mapping defined in `src/bcd_api/services/dublin_core_import.py`:

| Dublin Core Column | Database Field | Data Type | Notes |
|-------------------|----------------|-----------|-------|
| dc.identifier | isbn | String | Strip "isbn:" prefix, normalize hyphens |
| dc.title | title | String | Required |
| dc.creator | authors | JSON array | Pipe-separated → JSON list |
| dc.contributor | illustrators | JSON array | Pipe-separated → JSON list |
| dc.publisher | publisher | String | |
| dc.date | publication_year | Integer | Extract year from YYYY or YYYY-MM-DD |
| dc.type | medium_type | String | **Stored as-is**, no normalization |
| dc.format | page_count | Integer | Extract number from "173 pages" or "173 p" |
| dc.subject | keywords | JSON array | Pipe-separated → JSON list |
| dc.description | description | Text | |
| dc.language | language | String | ISO 639-1 code (e.g., "fr", "en") |
| dc.coverage | level | String | Target audience/reading level |
| dc.rights | loanable (Item) | Boolean | Parse "not loanable", "reference only" |
| item.id | item_id (Item) | String | Required per row |
| item.callNumber | call_number (Item) | String | Dewey/CDU classification |
| item.acquisitionDate | acquisition_date (Item) | Date | ISO 8601 format |
| item.fundingSource | funding_source (Item) | String | |

### Database → Dublin Core (Export - New Feature)

**Reverse mapping for export** (to be implemented in `export_service.py`):

| Database Field | Dublin Core Column | Transformation |
|----------------|-------------------|----------------|
| isbn | dc.identifier | Add "isbn:" prefix if present |
| title | dc.title | Direct |
| authors (JSON) | dc.creator | JSON list → pipe-separated string |
| illustrators (JSON) | dc.contributor | JSON list → pipe-separated string |
| publisher | dc.publisher | Direct |
| publication_year | dc.date | Integer → "YYYY" string |
| medium_type | dc.type | **Direct** - no transformation |
| page_count | dc.format | Integer → "N pages" string |
| keywords (JSON) | dc.subject | JSON list → pipe-separated string |
| description | dc.description | Direct |
| language | dc.language | Direct |
| level | dc.coverage | Direct |
| item.loanable | dc.rights | Boolean → "Loanable" or "Not loanable" |
| item.item_id | item.id | Direct |
| item.call_number | item.callNumber | Direct |
| item.acquisition_date | item.acquisitionDate | Date → ISO 8601 "YYYY-MM-DD" |
| item.funding_source | item.fundingSource | Direct |

### Multi-valued Fields (Pipe-Separated in CSV)

**Import** (existing):
```python
# CSV: "White E.B.|Garth Williams"
# Database: '["White E.B.", "Garth Williams"]'
authors = json.loads(record.authors)  # → ["White E.B.", "Garth Williams"]
```

**Export** (new):
```python
# Database: '["White E.B.", "Garth Williams"]'
# CSV: "White E.B.|Garth Williams"
authors_list = json.loads(record.authors)
csv_value = "|".join(authors_list)  # → "White E.B.|Garth Williams"
```

## Export Data Flow

### Query Strategy

```python
# Get all bibliographic records with their items
records = db.query(BiblographicRecord).options(
    joinedload(BiblographicRecord.items)
).all()

# For each record with items, create one CSV row per item
# For records without items, create one row with empty item fields
```

### Record-to-Row Mapping

**One bibliographic record with multiple items**:
```
BiblographicRecord(id=1, title="Stuart Little", isbn="2211056466", medium_type="Livre")
  └─ Item(item_id="787", call_number="800.000", loanable=True)
  └─ Item(item_id="788", call_number="800.000", loanable=True)
```

**Produces two CSV rows** (one per item):
```csv
dc.title,dc.identifier,dc.type,item.id,item.callNumber,dc.rights
Stuart Little,isbn:2211056466,Livre,787,800.000,Loanable
Stuart Little,isbn:2211056466,Livre,788,800.000,Loanable
```

**Record with no items** (edge case):
```
BiblographicRecord(id=2, title="Les Misérables", isbn="123456", medium_type="Livre")
  └─ (no items)
```

**Produces one CSV row** with empty item fields:
```csv
dc.title,dc.identifier,dc.type,item.id,item.callNumber,dc.rights
Les Misérables,isbn:123456,Livre,,,
```

## Round-Trip Fidelity Requirements

### Test Case: Export → Import → Export

**Original export** (CSV 1):
```csv
dc.title,dc.identifier,dc.creator,dc.type,dc.subject,item.id
Le Petit Prince,isbn:9782070612758,Antoine de Saint-Exupéry,Livre,histoire|merveilleux,787
```

**After import and re-export** (CSV 2):
```csv
dc.title,dc.identifier,dc.creator,dc.type,dc.subject,item.id
Le Petit Prince,isbn:9782070612758,Antoine de Saint-Exupéry,Livre,histoire|merveilleux,787
```

**Assertion**: CSV 1 == CSV 2 (byte-identical)

### Round-Trip Test Cases

1. **French characters**: "L'Été à Paris" → "L'Été à Paris" ✅
2. **Medium type preservation**: "Livre" → "Livre" (not "Text" or "book") ✅
3. **Pipe-separated lists**: "author1|author2" → "author1|author2" ✅
4. **Empty fields**: "" → "" (not "null" or "N/A") ✅
5. **ISBN prefix**: "isbn:123" → "isbn:123" ✅

## Data Validation Rules

### Import Validation (Existing)

Implemented in `dublin_core_import.py`:

- **dc.title**: Required (reject row if empty)
- **dc.identifier OR item.id**: At least one required
- **ISBN format**: If present, must be 10 or 13 digits after normalization
- **Duplicate detection**: Check existing records by ISBN, then by title
- **Multi-valued fields**: Parse pipe-separated, handle empty strings
- **Date parsing**: Extract year from YYYY, YYYY-MM, YYYY-MM-DD formats

### Export Validation (New)

To be implemented in `export_service.py`:

- **Required fields**: title always present (database constraint)
- **JSON parsing**: Handle null/empty JSON arrays gracefully
- **Special characters**: Escape commas, quotes per RFC 4180
- **UTF-8 encoding**: Use UTF-8 with BOM for Excel compatibility
- **Row limit**: Reject exports exceeding 10,000 rows (spec FR-008)

## Error Handling

### Export Error Scenarios

1. **Empty catalog**: Return CSV with headers only (no data rows)
2. **JSON parse error**: Skip field, log warning, continue export
3. **Too many records**: Return 400 error "Export exceeds 10,000 row limit"
4. **Database error**: Return 500 error with rollback

### Import Error Scenarios (Existing)

1. **Missing required column**: Reject CSV with clear error message
2. **Invalid ISBN**: Skip row, include in error list
3. **Duplicate item.id**: Skip row, include in error list
4. **Encoding error**: Auto-detect and retry with different encoding

## Performance Considerations

### Export Performance

**Target**: 1000 records in <5 seconds (spec SC-001)

**Strategy**:
- Use `joinedload` to fetch items in single query (avoid N+1)
- Stream CSV generation (yield rows, don't build entire file in memory)
- Use `csv.DictWriter` with `QUOTE_MINIMAL` (faster than QUOTE_ALL)

**Memory profile** for 10,000 records:
- Database query: ~50MB (with items joined)
- CSV generation: ~5MB (streaming)
- Total: <100MB peak memory

### Import Performance (Existing - Already Optimized)

**Achieved**: 1000 records in <10 seconds (spec SC-002)

**Strategy** (from `dublin_core_import.py`):
- Group rows by ISBN/title (bulk create)
- Single bulk insert for all records
- Single bulk insert for all items
- Transaction isolation (commit once at end)

## Migration Notes

**No database migrations required** for this feature.

**Reason**: Feature uses existing schema. The `medium_type` field is already VARCHAR(50) with no constraints.

**If migrating from hardcoded enum** (not applicable to this feature, but documented for reference):
- Previous spec 004-import-export proposed migration from enum → VARCHAR
- That spec was abandoned as over-engineered
- Current schema already uses VARCHAR, no migration needed
