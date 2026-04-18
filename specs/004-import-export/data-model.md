# Data Model: Import/Export with Configurable Medium Types

**Feature**: 004-import-export
**Created**: 2026-02-06
**Status**: Planning Phase

## Overview

This document defines the database schema changes required to implement configurable medium type taxonomy and CSV import/export functionality. The core architectural change is migrating from hardcoded Python enums (`MediumType.LIVRE`) to foreign key-based lookup tables with **multilingual display names** (English, French, Italian, and any future languages).

## Entity-Relationship Diagram

```
┌─────────────────────────┐
│   medium_types          │
├─────────────────────────┤
│ id (PK)                 │
│ code (UNIQUE)           │  ← Generic English: "book", "cd", "dvd"
│ display_names (JSON)    │  ← Multilingual: {"en": "Book", "fr": "Livre", "it": "Libro"}
│ active                  │
│ created_at              │
│ updated_at              │
└─────────────────────────┘
          │
          │ 1
          │
          │ N
          ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│ bibliographic_record    │         │ medium_type_mappings    │
├─────────────────────────┤         ├─────────────────────────┤
│ id (PK)                 │         │ id (PK)                 │
│ medium_type_id (FK) ←───┼─────────┤ medium_type_id (FK)     │
│ title                   │         │ source_value (UNIQUE)   │  ← "Livre", "CD-Audio", "Book"
│ authors                 │         │ priority                │  ← For conflict resolution
│ ...                     │         │ created_at              │
└─────────────────────────┘         └─────────────────────────┘
```

## Schema Definitions

### Table: `medium_types`

Stores configurable material format categories with **multilingual display names** (supports unlimited languages via JSON column).

```sql
CREATE TABLE medium_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    display_names TEXT NOT NULL,  -- JSON: {"en": "Book", "fr": "Livre", "it": "Libro"}
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT check_code_format CHECK (code GLOB '[a-z_]*'),  -- Alphanumeric lowercase + underscores only
    CONSTRAINT check_display_names_is_json CHECK (json_valid(display_names))  -- SQLite/PostgreSQL JSON validation
);

CREATE INDEX idx_medium_types_code ON medium_types(code);
CREATE INDEX idx_medium_types_active ON medium_types(active);
```

**Fields**:
- `id`: Primary key
- `code`: Generic English identifier (e.g., "book", "audiobook", "educational_kit") - immutable after creation
- `display_names`: JSON object with locale keys and display values (e.g., `{"en": "Book", "fr": "Livre", "it": "Libro"}`) - editable
- `active`: Soft delete flag (inactive types hidden from UI dropdowns but preserve historical data)
- `created_at`, `updated_at`: Audit timestamps

**Validation Rules**:
- `code` MUST be alphanumeric lowercase with underscores only (regex: `^[a-z_]+$`)
- `code` MUST be unique (enforced by database UNIQUE constraint)
- `code` is immutable (application-level enforcement - migrations only)
- `display_names` MUST be valid JSON (enforced by database CHECK constraint)
- `display_names` MUST contain at least `"en"` key (application-level validation)
- Cannot delete if bibliographic records reference this type (foreign key constraint)

**JSON Structure**:
```json
{
  "en": "Book",        // Required - English as fallback language
  "fr": "Livre",       // Optional - French translation
  "it": "Libro",       // Optional - Italian translation
  "es": "Libro",       // Optional - Spanish translation
  "de": "Buch"         // Optional - German translation
  // ... unlimited languages supported
}
```

**Application-Level Access**:
- SQLAlchemy will use a custom column type to serialize/deserialize JSON
- Vue UI will select display name based on current locale: `medium_type.display_names[currentLocale] || medium_type.display_names['en']`
- API responses include full `display_names` object for client-side locale selection

**Default Data** (seeded on fresh installation):

| id | code | display_names (JSON) |
|----|------|---------------------|
| 1  | book | `{"en": "Book", "fr": "Livre"}` |
| 2  | audiobook | `{"en": "Audiobook", "fr": "Livre CD"}` |
| 3  | cd | `{"en": "CD", "fr": "CD"}` |
| 4  | dvd | `{"en": "DVD", "fr": "DVD"}` |
| 5  | periodical | `{"en": "Periodical", "fr": "Périodique"}` |
| 6  | ebook | `{"en": "E-Book", "fr": "E-Book"}` |
| 7  | software | `{"en": "Software", "fr": "Logiciel"}` |
| 8  | educational_kit | `{"en": "Educational Kit", "fr": "Kit pédagogique"}` |
| 9  | other | `{"en": "Other", "fr": "Autre"}` |

**Note**: Default data includes English and French only. Italian and other languages can be added later via admin UI or bulk update without schema changes.

---

### Table: `medium_type_mappings`

Stores import normalization rules for mapping source CSV values to medium type codes.

```sql
CREATE TABLE medium_type_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medium_type_id INTEGER NOT NULL,
    source_value VARCHAR(200) NOT NULL UNIQUE COLLATE NOCASE,  -- Case-insensitive unique
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Keys
    CONSTRAINT fk_medium_type_id FOREIGN KEY (medium_type_id)
        REFERENCES medium_types(id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT check_source_value_not_empty CHECK (LENGTH(source_value) > 0),
    CONSTRAINT check_priority_positive CHECK (priority > 0)
);

CREATE INDEX idx_medium_type_mappings_medium_type_id ON medium_type_mappings(medium_type_id);
CREATE INDEX idx_medium_type_mappings_source_value ON medium_type_mappings(source_value COLLATE NOCASE);
CREATE INDEX idx_medium_type_mappings_priority ON medium_type_mappings(priority);
```

**Fields**:
- `id`: Primary key
- `medium_type_id`: Foreign key to medium_types.id (CASCADE delete - remove mappings when type deleted)
- `source_value`: CSV input value to match (e.g., "Livre", "CD-Audio", "Book", "Texte imprimé")
- `priority`: Integer for conflict resolution (1 = highest priority), used when multiple rules could match
- `created_at`: Audit timestamp

**Validation Rules**:
- `source_value` MUST be unique (case-insensitive) - prevents duplicate mappings
- `source_value` MUST NOT be empty
- `priority` MUST be positive integer (1-N)
- Matching is case-insensitive (COLLATE NOCASE in SQLite, ILIKE in PostgreSQL)

**Default Data** (seeded for BCDI/Dublin Core compatibility):

| medium_type_id | source_value | priority |
|----------------|--------------|----------|
| 1 (book) | Book | 1 |
| 1 (book) | Livre | 1 |
| 1 (book) | livre | 1 |
| 1 (book) | Texte imprimé | 2 |
| 2 (audiobook) | Audiobook | 1 |
| 2 (audiobook) | Livre CD | 1 |
| 2 (audiobook) | Livre-CD | 1 |
| 2 (audiobook) | Livre CD-Audio | 2 |
| 3 (cd) | CD | 1 |
| 3 (cd) | CD-Audio | 2 |
| 3 (cd) | Audio CD | 2 |
| 3 (cd) | CD audio | 2 |
| 3 (cd) | Enregistrement sonore | 3 |
| 4 (dvd) | DVD | 1 |
| 4 (dvd) | DVD-vidéo | 2 |
| 4 (dvd) | DVD Video | 2 |
| 4 (dvd) | Image animée | 3 |
| 5 (periodical) | Periodical | 1 |
| 5 (periodical) | Périodique | 1 |
| 5 (periodical) | Revue | 2 |
| 5 (periodical) | Magazine | 2 |
| 9 (other) | Autre | 1 |
| 9 (other) | Other | 1 |

---

### Modified Table: `bibliographic_record`

**BREAKING CHANGE**: Convert `medium_type` from VARCHAR enum to foreign key reference.

**Before**:
```sql
CREATE TABLE bibliographic_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medium_type VARCHAR(50),  -- Hardcoded: "Livre", "CD", "DVD", etc.
    ...
    CONSTRAINT check_medium_type CHECK (medium_type IN ('Livre', 'CD', 'DVD', 'Périodique', ...))
);
```

**After**:
```sql
CREATE TABLE bibliographic_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medium_type_id INTEGER,  -- Foreign key to medium_types.id
    ...
    CONSTRAINT fk_medium_type_id FOREIGN KEY (medium_type_id)
        REFERENCES medium_types(id)
        ON DELETE RESTRICT  -- Prevent deletion of medium types in use
);

CREATE INDEX idx_bibliographic_record_medium_type_id ON bibliographic_record(medium_type_id);
```

**Migration Strategy** (three-phase):

**Phase 1: Add temporary column** (migration file 1)
```sql
ALTER TABLE bibliographic_record ADD COLUMN medium_type_id INTEGER;
```

**Phase 2: Data migration** (Python migration script)
```python
# Map existing enum values to medium_type.id
mapping = {
    "Livre": 1,      # book
    "Livre CD": 2,   # audiobook
    "CD": 3,         # cd
    "DVD": 4,        # dvd
    "Périodique": 5, # periodical
    "Livre CD-ROM": 2, # audiobook (treat as audiobook)
    "Film": 4,       # dvd (treat as dvd)
    "Autre": 9,      # other
    # Add all existing enum values from shared/constants.py
}

for old_value, new_id in mapping.items():
    db.execute(
        "UPDATE bibliographic_record SET medium_type_id = ? WHERE medium_type = ?",
        (new_id, old_value)
    )

# Validate: Check for unmapped values
unmapped = db.execute(
    "SELECT DISTINCT medium_type FROM bibliographic_record WHERE medium_type_id IS NULL"
).fetchall()

if unmapped:
    raise MigrationError(f"Unmapped medium types: {unmapped}")
```

**Phase 3: Drop old column and add constraint** (migration file 2 - SQLite requires table recreation)
```sql
-- SQLite: Recreate table without medium_type column
PRAGMA foreign_keys=OFF;

CREATE TABLE bibliographic_record_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medium_type_id INTEGER NOT NULL,  -- Now required
    title VARCHAR(500) NOT NULL,
    -- ... other columns ...

    CONSTRAINT fk_medium_type_id FOREIGN KEY (medium_type_id)
        REFERENCES medium_types(id)
        ON DELETE RESTRICT
);

INSERT INTO bibliographic_record_new SELECT
    id, medium_type_id, title, ...  -- Copy all columns except old medium_type
FROM bibliographic_record;

DROP TABLE bibliographic_record;
ALTER TABLE bibliographic_record_new RENAME TO bibliographic_record;

-- Recreate indexes
CREATE INDEX idx_bibliographic_record_medium_type_id ON bibliographic_record(medium_type_id);

PRAGMA foreign_keys=ON;
```

**Rollback Strategy**:
- If migration fails, rollback transaction restores original state
- Downgrade migration recreates old column from medium_type_id using reverse mapping
- Keep old migration files indefinitely for emergency rollback

---

## SQLAlchemy ORM Models

### Model: `MediumType`

```python
# src/bcd_api/models/medium_type.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.bcd_api.core.database import Base


class MediumType(Base):
    """Configurable material format category (Book, CD, DVD, etc.)"""

    __tablename__ = "medium_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    display_name_en = Column(String(100), nullable=False)
    display_name_fr = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    bibliographic_records = relationship("BiblographicRecord", back_populates="medium_type")
    mappings = relationship("MediumTypeMapping", back_populates="medium_type", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("code GLOB '[a-z_]*'", name="check_code_format"),
        CheckConstraint("LENGTH(display_name_en) > 0", name="check_display_name_en_not_empty"),
        CheckConstraint("LENGTH(display_name_fr) > 0", name="check_display_name_fr_not_empty"),
    )

    def __repr__(self):
        return f"<MediumType(code='{self.code}', en='{self.display_name_en}', fr='{self.display_name_fr}')>"
```

### Model: `MediumTypeMapping`

```python
# src/bcd_api/models/medium_type_mapping.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.bcd_api.core.database import Base


class MediumTypeMapping(Base):
    """Import normalization rule mapping source CSV values to medium type codes"""

    __tablename__ = "medium_type_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medium_type_id = Column(Integer, ForeignKey("medium_types.id", ondelete="CASCADE"), nullable=False, index=True)
    source_value = Column(String(200), nullable=False, unique=True)  # Case-insensitive unique
    priority = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    medium_type = relationship("MediumType", back_populates="mappings")

    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(source_value) > 0", name="check_source_value_not_empty"),
        CheckConstraint("priority > 0", name="check_priority_positive"),
        Index("idx_medium_type_mappings_source_value", "source_value", sqlite_on_conflict_unique="REPLACE"),
    )

    def __repr__(self):
        return f"<MediumTypeMapping(source='{self.source_value}' → medium_type_id={self.medium_type_id}, priority={self.priority})>"
```

### Modified Model: `BiblographicRecord`

```python
# src/bcd_api/models/bibliographic_record.py (MODIFIED)

from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from src.bcd_api.core.database import Base


class BiblographicRecord(Base):
    """Bibliographic metadata for library materials"""

    __tablename__ = "bibliographic_record"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # CHANGED: medium_type VARCHAR → medium_type_id INTEGER (FK)
    medium_type_id = Column(
        Integer,
        ForeignKey("medium_types.id", ondelete="RESTRICT"),  # Prevent deletion of types in use
        nullable=False,  # Required field
        index=True
    )

    title = Column(String(500), nullable=False)
    # ... other fields ...

    # Relationships
    medium_type = relationship("MediumType", back_populates="bibliographic_records")  # NEW
    items = relationship("Item", back_populates="bibliographic_record")

    # REMOVED: CheckConstraint for medium_type enum (no longer needed)
```

---

## Validation Rules

### Application-Level Validation

**Medium Type Creation**:
```python
def validate_medium_type_create(code: str, display_name_en: str, display_name_fr: str):
    # Code format
    if not re.match(r'^[a-z_]+$', code):
        raise ValidationError("Code must be alphanumeric lowercase with underscores only")

    # Code uniqueness (checked by database, but provide user-friendly error)
    if db.query(MediumType).filter(MediumType.code == code).first():
        raise ValidationError(f"Code '{code}' already exists")

    # Display names not empty
    if not display_name_en.strip():
        raise ValidationError("English display name required")
    if not display_name_fr.strip():
        raise ValidationError("French display name required")
```

**Medium Type Deletion**:
```python
def validate_medium_type_delete(medium_type_id: int):
    # Check if any bibliographic records use this type
    count = db.query(BiblographicRecord).filter(
        BiblographicRecord.medium_type_id == medium_type_id
    ).count()

    if count > 0:
        raise ValidationError(
            f"Cannot delete medium type - {count} bibliographic records still use this type. "
            f"Deactivate instead or reassign items first."
        )
```

**Import Mapping Creation**:
```python
def validate_mapping_create(source_value: str, medium_type_id: int):
    # Source value not empty
    if not source_value.strip():
        raise ValidationError("Source value required")

    # Source value uniqueness (case-insensitive)
    existing = db.query(MediumTypeMapping).filter(
        func.lower(MediumTypeMapping.source_value) == source_value.lower()
    ).first()

    if existing:
        raise ValidationError(
            f"Mapping for '{source_value}' already exists → "
            f"{existing.medium_type.display_name_en}. "
            f"Delete existing mapping first."
        )

    # Medium type exists
    if not db.query(MediumType).filter(MediumType.id == medium_type_id).first():
        raise ValidationError(f"Medium type ID {medium_type_id} not found")
```

---

## Performance Considerations

### Indexes

All foreign keys and frequently queried columns are indexed:
- `medium_types.code` (UNIQUE index for code lookups)
- `medium_types.active` (filter active types in dropdowns)
- `medium_type_mappings.medium_type_id` (JOIN optimization)
- `medium_type_mappings.source_value` (case-insensitive lookup)
- `medium_type_mappings.priority` (ORDER BY optimization)
- `bibliographic_record.medium_type_id` (JOIN optimization)

### Query Optimization

**Fetch medium types with counts**:
```sql
-- Get medium types with count of bibliographic records using each type
SELECT
    mt.id,
    mt.code,
    mt.display_name_en,
    mt.display_name_fr,
    mt.active,
    COUNT(br.id) AS record_count
FROM medium_types mt
LEFT JOIN bibliographic_record br ON br.medium_type_id = mt.id
GROUP BY mt.id
ORDER BY mt.code;
```

**Fuzzy matching with priority**:
```sql
-- Find mapping for source value (case-insensitive, ordered by priority)
SELECT medium_type_id
FROM medium_type_mappings
WHERE LOWER(source_value) = LOWER(?)
ORDER BY priority ASC
LIMIT 1;
```

### Caching Strategy

**Medium types cache** (application-level):
- Cache all active medium types in memory (typically <20 types)
- Refresh on admin CRUD operations (POST/PATCH/DELETE to /api/v1/medium-types)
- TTL: 1 hour or invalidate on write

**Mapping cache** (application-level):
- Precompute lowercase/normalized versions on startup
- Store as dict: `{"livre": 1, "cd-audio": 3, ...}` for O(1) lookups
- Refresh on admin mapping changes

---

## Migration Checklist

**Before Migration**:
- [ ] Backup database (SQLite: copy bcd.db file, PostgreSQL: pg_dump)
- [ ] Test migration on copy of production database
- [ ] Verify all existing medium_type enum values have mappings defined
- [ ] Estimate downtime (1-5 minutes for 10k records)

**During Migration**:
- [ ] Run migration 1: Add medium_type_id column
- [ ] Run Python data migration script
- [ ] Validate: Check for NULL medium_type_id values (should be zero)
- [ ] Run migration 2: Drop old column, add constraint
- [ ] Verify foreign key constraints active (PRAGMA foreign_keys=ON)

**After Migration**:
- [ ] Run SELECT query to verify all records have valid medium_type_id
- [ ] Test import with BCDI sample file (verify mapping works)
- [ ] Test export to BCDI format (verify reverse mapping works)
- [ ] Test admin UI: Add new medium type, verify catalog uses it
- [ ] Run integration tests: test_migration_medium_type.py

**Rollback Plan**:
```sql
-- Emergency rollback (recreate old column from FK)
ALTER TABLE bibliographic_record ADD COLUMN medium_type VARCHAR(50);

UPDATE bibliographic_record SET medium_type = (
    SELECT CASE code
        WHEN 'book' THEN 'Livre'
        WHEN 'audiobook' THEN 'Livre CD'
        WHEN 'cd' THEN 'CD'
        WHEN 'dvd' THEN 'DVD'
        WHEN 'periodical' THEN 'Périodique'
        WHEN 'other' THEN 'Autre'
        -- Add all mappings
    END
    FROM medium_types
    WHERE medium_types.id = bibliographic_record.medium_type_id
);

-- Then drop medium_type_id column (requires table recreation in SQLite)
```

---

## Testing Data

**Sample medium types** (for test database):
```python
TEST_MEDIUM_TYPES = [
    {"code": "book", "display_name_en": "Book", "display_name_fr": "Livre"},
    {"code": "audiobook", "display_name_en": "Audiobook", "display_name_fr": "Livre CD"},
    {"code": "cd", "display_name_en": "CD", "display_name_fr": "CD"},
    {"code": "dvd", "display_name_en": "DVD", "display_name_fr": "DVD"},
    {"code": "periodical", "display_name_en": "Periodical", "display_name_fr": "Périodique"},
    {"code": "other", "display_name_en": "Other", "display_name_fr": "Autre"},
]
```

**Sample mappings** (for import testing):
```python
TEST_MAPPINGS = [
    {"source_value": "Livre", "medium_type_code": "book", "priority": 1},
    {"source_value": "Book", "medium_type_code": "book", "priority": 1},
    {"source_value": "CD-Audio", "medium_type_code": "cd", "priority": 2},
    {"source_value": "Enregistrement sonore", "medium_type_code": "cd", "priority": 3},
    {"source_value": "DVD-vidéo", "medium_type_code": "dvd", "priority": 2},
]
```

**Sample CSV import data** (for round-trip testing):
```csv
dc.title,dc.identifier,dc.type,item.id
Stuart Little,9780064400558,Book,ITEM-001
Le Petit Prince,9782070408504,Livre,ITEM-002
Music CD,1234567890123,CD-Audio,ITEM-003
Harry Potter DVD,5051889000877,DVD-vidéo,ITEM-004
```

---

## References

- Research findings: [research.md](./research.md)
- Koha itemtypes schema: https://schema.koha-community.org/tables/itemtypes.html
- SQLAlchemy relationships: https://docs.sqlalchemy.org/en/20/orm/relationship_api.html
- Alembic migrations: https://alembic.sqlalchemy.org/en/latest/tutorial.html
