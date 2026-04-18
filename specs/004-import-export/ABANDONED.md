# ❌ SPEC ABANDONED - Too Complex

**Date**: 2026-02-06
**Reason**: Over-engineered solution for a simple problem
**Decided by**: User feedback during planning phase

## Why Abandoned

This specification attempted to solve medium type compatibility through:
- Foreign key lookup tables (`medium_types`, `medium_type_mappings`)
- Multilingual JSON columns for display names
- Fuzzy matching normalization pipeline (rapidfuzz library)
- Complex import mapping UI with confidence scores
- Admin configuration for custom types

**Result**: ~2000 lines of spec, 17 new files, 10 modified files, 3 new database tables, 2 breaking migrations

## The Simpler Alternative

### ✅ Store Medium Types as Plain Text (Like Titles)

**Approach**: Treat `medium_type` as a free-text field, just like `title` or `author`.

```sql
CREATE TABLE bibliographic_record (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,           -- Free text: "Le Petit Prince"
    author VARCHAR(100),                   -- Free text: "Antoine de Saint-Exupéry"
    medium_type VARCHAR(50),               -- Free text: "Livre", "Book", "Libro" ← NO normalization
    dewey_decimal VARCHAR(20),
    -- ...
);
```

### Import Behavior

**French school imports BCDI file**:
```csv
ISBN,Titre,Auteur,Support
9782070612758,Le Petit Prince,Saint-Exupéry,Livre
```
→ Database stores: `medium_type = "Livre"` (as-is, no mapping)

**Italian school imports their file**:
```csv
ISBN,Titolo,Autore,Tipo
9788845292613,Il Piccolo Principe,Saint-Exupéry,Libro
```
→ Database stores: `medium_type = "Libro"` (as-is, no mapping)

**English school imports Dublin Core**:
```csv
dc.identifier,dc.title,dc.creator,dc.type
isbn:9780156012195,The Little Prince,Saint-Exupéry,Text
```
→ Database stores: `medium_type = "Text"` (as-is, no mapping)

### Filtering & Search

**Use existing search/filter patterns**:

```python
# Filter by exact match
records = db.query(BibliographicRecord).filter(
    BibliographicRecord.medium_type == "Livre"
).all()

# Filter by case-insensitive partial match
records = db.query(BibliographicRecord).filter(
    BibliographicRecord.medium_type.ilike("%livre%")
).all()

# Get distinct medium types for filter dropdown (like Dewey ranges)
medium_types = db.query(BibliographicRecord.medium_type).distinct().all()
# Returns: ["Livre", "Périodique", "CD", "DVD"]
```

**UI Filter Dropdown** (auto-populated from existing data):
```javascript
// Fetch distinct medium types from database
const mediumTypes = await fetch('/api/v1/catalog/medium-types/distinct');
// Returns: ["Livre", "Périodique", "CD Audio", "DVD Vidéo", "Livre CD"]

// Show in filter dropdown (no normalization needed)
<select>
  <option value="">Tous les supports</option>
  <option value="Livre">Livre (245)</option>
  <option value="Périodique">Périodique (42)</option>
  <option value="CD Audio">CD Audio (18)</option>
</select>
```

### Export Behavior

**Export preserves original values** (no reverse mapping):
```python
# Export to CSV
for record in records:
    csv_row = {
        'title': record.title,
        'author': record.author,
        'medium_type': record.medium_type,  # "Livre" exported as "Livre"
    }
```

**Round-trip fidelity**: Import → Export produces identical values ✅

### Advantages

1. **Zero normalization complexity**: No mapping tables, no fuzzy matching, no admin UI
2. **Import as-is**: Schools keep their existing terminology (French schools: "Livre", Italian: "Libro")
3. **No data loss**: Exact values preserved (e.g., "CD Audio" vs "CD" distinction maintained)
4. **No breaking changes**: Existing `medium_type` enum can be migrated to VARCHAR (add default values, no FK constraints)
5. **Simple filtering**: Standard SQL `WHERE medium_type = 'Livre'` or `LIKE '%Livre%'`
6. **Auto-populated dropdowns**: Just `SELECT DISTINCT medium_type` from existing data
7. **No new dependencies**: No rapidfuzz, no chardet needed for medium types
8. **Familiar UX**: Users already understand free-text filtering (like searching by author name)

### Trade-offs

**❌ Lost**:
- Standardized codes across schools (French "Livre" ≠ Italian "Libro" in queries)
- Multilingual display (French school can't see "Book" in English UI)
- Validation (users can typo "Lvire" instead of "Livre")

**✅ Gained**:
- Simplicity (90% less code)
- No configuration needed (works out of the box)
- No migration risk (simple VARCHAR column)
- Faster import (no normalization pipeline)

### What This Means for the Spec

**Keep from original spec**:
- ✅ CSV import/export functionality (FR-001 to FR-030)
- ✅ BCDI format compatibility (FR-009)
- ✅ Dublin Core format support (FR-010)
- ✅ UTF-8 encoding (FR-069)
- ✅ Round-trip fidelity (FR-064 to FR-070)
- ✅ Fuzzy column matching for import (FR-046 to FR-048)
- ✅ Import wizard UI (US3, US4)
- ✅ Export dialog UI (US1, US2)

**Remove from original spec**:
- ❌ Configurable medium type taxonomy (FR-031 to FR-045, US6)
- ❌ Medium type normalization (FR-049 to FR-055)
- ❌ Admin configuration UI for types/mappings
- ❌ `medium_types` and `medium_type_mappings` tables
- ❌ Multilingual display names
- ❌ Foreign key migration
- ❌ rapidfuzz dependency for medium type matching

**Remaining complexity**:
- Import wizard (upload → map columns → preview → confirm)
- Fuzzy column name matching (for CSV headers, not medium types)
- Export format conversion (Standard → BCDI → Dublin Core)
- Encoding detection (UTF-8, Latin-1, Windows-1252)

**Implementation estimate**:
- Before: 17 new files, 10 modified files, ~40 hours
- After: ~8 new files, ~5 modified files, ~15-20 hours

## Migration Path for Existing Data

If BCD already has hardcoded French enums (`MediumType.LIVRE`):

```python
# Simple migration: enum → VARCHAR with default values
# No FK constraints, no lookup tables

# Alembic migration
def upgrade():
    # Add new VARCHAR column
    op.add_column('bibliographic_record',
        sa.Column('medium_type_text', sa.String(50), nullable=True)
    )

    # Migrate existing enum values to French text
    op.execute("""
        UPDATE bibliographic_record
        SET medium_type_text = CASE
            WHEN medium_type = 'BOOK' THEN 'Livre'
            WHEN medium_type = 'PERIODICAL' THEN 'Périodique'
            WHEN medium_type = 'CD' THEN 'CD'
            WHEN medium_type = 'DVD' THEN 'DVD'
            ELSE 'Autre'
        END
    """)

    # Drop old enum column
    op.drop_column('bibliographic_record', 'medium_type')

    # Rename new column
    op.alter_column('bibliographic_record', 'medium_type_text', new_column_name='medium_type')

def downgrade():
    # Reverse migration (best effort)
    # ...
```

**Result**: Existing French data preserved as "Livre", "Périodique", etc. (no breaking change for users)

## Conclusion

**Original spec**: Tried to solve "How do we normalize medium types across different languages and formats?"

**Reality check**: Schools don't need normalized codes. They need to:
1. Import their existing data without errors ✅
2. Filter their catalog by medium type ✅
3. Export data in their original format ✅

**Solution**: Don't normalize. Store as-is. Filter like any other text field.

**Next steps**: Create new simplified spec focusing only on CSV import/export functionality.

---

**Lessons Learned**:
- Start simple, add complexity only when proven necessary
- Question whether "normalization" actually helps users
- Free-text fields with search are often simpler than lookup tables
- 1000 lines of spec = red flag to reconsider approach
