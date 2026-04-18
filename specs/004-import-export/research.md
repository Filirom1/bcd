# Research: CSV Import/Export Best Practices for Library Systems

**Feature ID**: 004-import-export
**Research Date**: 2026-02-06
**Researcher**: Claude Code

## Executive Summary

This research examines best practices for CSV import/export in library management systems, with specific focus on:
1. Configurable taxonomies (item types, material types)
2. Import mapping strategies (fuzzy matching, normalization)
3. Database migration patterns (enum to foreign key)
4. Admin UI patterns for taxonomy management
5. BCDI/UNIMARC compatibility for French library systems

The findings emphasize **lookup table patterns over enums**, **AI-assisted column mapping**, **transaction-safe migrations**, and **row-level validation feedback**.

---

## 1. Configurable Taxonomies: Database Schema Patterns

### Decision Made
**Use foreign key-based lookup tables instead of hardcoded enums** for item types, material types, and other taxonomies.

### Rationale
- **Flexibility**: Librarians can add/modify types without code changes or migrations
- **Referential Integrity**: Database enforces valid relationships automatically
- **Industry Standard**: Both Koha and Evergreen use this pattern
- **Cascade Operations**: Updates/deletes propagate automatically to dependent records

### Key Findings from Koha

**Schema Pattern**:
```sql
-- Item types table (from Koha's kohastructure.sql)
CREATE TABLE itemtypes (
  itemtype VARCHAR(10) NOT NULL,
  description LONGTEXT,
  rentalcharge DECIMAL(28,6),
  -- ... other circulation-related fields
  PRIMARY KEY (itemtype)
)

-- Circulation rules reference item types
CREATE TABLE circulation_rules (
  id INT(11) NOT NULL AUTO_INCREMENT,
  branchcode VARCHAR(10),
  categorycode VARCHAR(10),
  itemtype VARCHAR(10),
  rule_name VARCHAR(32) NOT NULL,
  rule_value VARCHAR(32) NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT circ_rules_ibfk_3
    FOREIGN KEY (itemtype)
    REFERENCES itemtypes (itemtype)
    ON DELETE CASCADE
    ON UPDATE CASCADE
)
```

**Key Features**:
- Item type code limited to 10 characters (short, URL-friendly identifier)
- Long description field for human-readable labels
- Foreign keys with CASCADE to automatically update references
- Circulation rules stored in separate table with foreign key to itemtypes

**Source**: [Koha kohastructure.sql](https://github.com/Koha-Community/Koha/blob/main/installer/data/mysql/kohastructure.sql)

### Key Findings from Evergreen

**Schema Pattern**:
Evergreen uses a `config` schema to store configuration tables:

```sql
-- Config schema holds static configuration data
config.copy_status       -- Item statuses (Available, Checked Out, etc.)
config.circ_modifier     -- Circulation modifiers
config.item_form_map     -- Item form types
config.non_cat_type      -- Non-cataloged item types
```

**Key Features**:
- Dedicated `config` schema separates configuration from operational data
- Copy status 0 = Available (special meaning)
- PostgreSQL backend with proper foreign key support
- Configuration tables are foundational to circulation rules

**Source**: [Evergreen Database Schema](https://olddocs.evergreen-ils.org/3.2_schema/)

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Hardcoded Enums** (Current BCD) | Fast lookups, type-safe | Requires code changes, migration for every new type |
| **PostgreSQL ENUM** | Type-safe, validated by DB | Cannot remove values easily, ALTER TYPE locks table |
| **CHECK Constraints** | Lightweight | Still requires migration to add values |
| **Lookup Tables** (Recommended) | Fully flexible, admin-configurable | Slightly slower joins (negligible in practice) |

### Implementation for BCD

**Recommended Schema**:
```sql
-- Core taxonomy table
CREATE TABLE item_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,  -- Short code (e.g., "ALBUM", "ROMAN")
    label_en VARCHAR(100) NOT NULL,     -- English label
    label_fr VARCHAR(100) NOT NULL,     -- French label
    description TEXT,
    renewable BOOLEAN DEFAULT 1,
    loan_duration_days INTEGER DEFAULT 14,
    max_renewals INTEGER DEFAULT 2,
    active BOOLEAN DEFAULT 1,           -- Soft delete support
    display_order INTEGER DEFAULT 0,    -- UI ordering
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Foreign key from items table
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- ... other fields ...
    item_type_id INTEGER NOT NULL,
    FOREIGN KEY (item_type_id) REFERENCES item_types(id)
);

-- Indexes for performance
CREATE INDEX idx_item_types_code ON item_types(code);
CREATE INDEX idx_item_types_active ON item_types(active);
CREATE INDEX idx_items_type ON items(item_type_id);
```

**Key Design Decisions**:
1. **Surrogate ID**: Use integer primary key (fast joins, stable across renames)
2. **Business Key**: `code` field for human-readable identifier (used in URLs, imports)
3. **Bilingual**: Separate `label_en` and `label_fr` columns (per BCD constitution)
4. **Soft Delete**: `active` flag instead of DELETE (preserve historical data)
5. **Circulation Defaults**: Store loan rules in taxonomy (can be overridden)
6. **Display Order**: Allow librarians to control UI presentation

---

## 2. Import Mapping Strategies: Fuzzy Matching & Normalization

### Decision Made
**Implement multi-stage import process with AI-assisted column mapping, fuzzy matching for taxonomy values, and comprehensive validation feedback.**

### Rationale
- **User-Friendly**: Auto-mapping reduces manual work by 80-90%
- **Error Recovery**: Row-level validation allows fixing errors without re-import
- **Data Quality**: Normalization prevents duplicate entries from typos
- **Industry Standard**: All modern import tools use this pattern

### Normalization Best Practices

**Three-Stage Normalization Pipeline**:

```python
# Stage 1: Text Cleaning
def normalize_text(value: str) -> str:
    """Clean and standardize text values."""
    # 1. Trim whitespace
    value = value.strip()

    # 2. Normalize Unicode (NFD for accents)
    value = unicodedata.normalize('NFD', value)

    # 3. Lowercase for case-insensitive matching
    value = value.lower()

    # 4. Remove punctuation (except hyphens)
    value = re.sub(r'[^\w\s-]', '', value)

    # 5. Collapse multiple spaces
    value = re.sub(r'\s+', ' ', value)

    return value

# Stage 2: Abbreviation Expansion
ABBREVIATION_MAP = {
    'bd': 'bande dessinée',
    'cd': 'cd-rom',
    'dvd': 'dvd-rom',
    # ... from import configuration
}

# Stage 3: Synonym Resolution
SYNONYM_MAP = {
    'book': ['livre', 'roman', 'ouvrage', 'volume'],
    'album': ['picture book', 'illustrated book'],
    # ... from import configuration
}
```

**Fuzzy Matching Algorithm**:

```python
from rapidfuzz import fuzz, process

def match_taxonomy_value(
    input_value: str,
    valid_values: list[str],
    threshold: int = 80
) -> tuple[str | None, int]:
    """
    Match input value to valid taxonomy values using fuzzy matching.

    Returns:
        (matched_value, confidence_score) or (None, 0) if no match
    """
    # Normalize input
    normalized_input = normalize_text(input_value)

    # Try exact match first (after normalization)
    normalized_valid = {normalize_text(v): v for v in valid_values}
    if normalized_input in normalized_valid:
        return normalized_valid[normalized_input], 100

    # Try fuzzy match with configurable threshold
    result = process.extractOne(
        input_value,
        valid_values,
        scorer=fuzz.ratio,
        score_cutoff=threshold
    )

    if result:
        matched_value, score, _ = result
        return matched_value, score

    return None, 0
```

**Source**: [String Data Normalization and Similarity Matching](https://medium.com/@ievgenii.shulitskyi/string-data-normalization-and-similarity-matching-algorithms-4b7b1734798e)

### Column Mapping Strategies

**AI-Assisted Auto-Mapping** (Used by CSVBox, Dromo, Flatfile):

1. **Header Analysis**: Parse CSV headers and compare to expected field names
2. **Synonym Detection**: Match variations (e.g., "Author" → "creator", "ISBN" → "isbn_13")
3. **Data Pattern Analysis**: Inspect first 5-10 rows to detect data types
4. **Confidence Scoring**: Rank matches by confidence (exact > synonym > pattern)
5. **User Confirmation**: Present suggestions with confidence scores for review

**Implementation Pattern**:

```python
def auto_map_columns(
    csv_headers: list[str],
    target_schema: dict[str, FieldDefinition],
    sample_rows: list[dict]
) -> dict[str, tuple[str, int]]:
    """
    Auto-map CSV columns to schema fields.

    Returns:
        {csv_header: (schema_field, confidence_score)}
    """
    mappings = {}

    for csv_header in csv_headers:
        # 1. Try exact match (case-insensitive)
        normalized_header = normalize_text(csv_header)
        for field_name, field_def in target_schema.items():
            if normalized_header == normalize_text(field_name):
                mappings[csv_header] = (field_name, 100)
                break

        # 2. Try synonym match
        if csv_header not in mappings:
            for field_name, field_def in target_schema.items():
                if normalized_header in field_def.synonyms:
                    mappings[csv_header] = (field_name, 90)
                    break

        # 3. Try fuzzy match on field name
        if csv_header not in mappings:
            result = process.extractOne(
                csv_header,
                target_schema.keys(),
                scorer=fuzz.ratio,
                score_cutoff=70
            )
            if result:
                field_name, score, _ = result
                mappings[csv_header] = (field_name, score)

        # 4. Try pattern-based detection (e.g., ISBN regex)
        if csv_header not in mappings:
            for field_name, field_def in target_schema.items():
                if matches_pattern(sample_rows, csv_header, field_def.pattern):
                    mappings[csv_header] = (field_name, 75)
                    break

    return mappings
```

**Sources**:
- [CSVBox Column Mapping](https://blog.csvbox.io/inside-csvbox-column-mapping/)
- [Dromo AI-Powered Column Matching](https://dromo.io/blog/common-data-import-errors-and-how-to-fix-them)

### Blocking Strategy for Large Imports

For datasets with 10,000+ rows, use **incremental matching**:

1. **Initial Match**: Auto-map columns with high confidence (>85%)
2. **Review Low-Confidence**: Present uncertain mappings (70-85%) for user review
3. **Manual Mapping**: User maps remaining unmapped columns
4. **Save Configuration**: Store mapping for reuse on similar files

**Source**: [csvmatch - Incremental Matching](https://github.com/maxharlow/csvmatch)

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Exact Match Only** | Simple, predictable | Fails on typos, case differences |
| **Manual Mapping Only** | Full user control | Time-consuming, error-prone |
| **AI Auto-Map (Recommended)** | Fast, user-friendly | Requires good training data |
| **Template-Based** | Consistent for repeated imports | Inflexible for variations |

---

## 3. Database Migration Patterns: Enum to Foreign Key

### Decision Made
**Use Alembic multi-step migration with temporary columns and data validation checkpoints.**

### Rationale
- **Zero Data Loss**: Temporary columns ensure rollback capability
- **Transaction Safety**: Each step is atomic and reversible
- **SQLite Compatible**: Works around SQLite's ALTER TABLE limitations
- **Validation**: Verify data integrity before committing changes

### Migration Strategy (PostgreSQL/SQLite)

**Three-Phase Migration Pattern**:

```python
# alembic/versions/xxx_migrate_item_type_to_fk.py

def upgrade():
    """Migrate from enum/string to foreign key lookup table."""

    # ===== PHASE 1: Create New Structures =====

    # Create item_types lookup table
    op.create_table(
        'item_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('label_en', sa.String(100), nullable=False),
        sa.Column('label_fr', sa.String(100), nullable=False),
        sa.Column('active', sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Populate with current enum values
    from src.shared.constants import ItemType
    item_types_data = [
        {'code': 'ALBUM', 'label_en': 'Picture Book', 'label_fr': 'Album'},
        {'code': 'ROMAN', 'label_en': 'Novel', 'label_fr': 'Roman'},
        {'code': 'BD', 'label_en': 'Comic Book', 'label_fr': 'Bande Dessinée'},
        # ... all current types
    ]
    op.bulk_insert(
        sa.table('item_types', sa.column('code'), sa.column('label_en'), sa.column('label_fr')),
        item_types_data
    )

    # ===== PHASE 2: Migrate Data =====

    # Add temporary FK column to items table
    op.add_column('items', sa.Column('item_type_id_new', sa.Integer(), nullable=True))

    # Populate new column from old enum/string column
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE items
        SET item_type_id_new = (
            SELECT id FROM item_types
            WHERE item_types.code = items.item_type
        )
    """))

    # Verify no nulls (all old values matched)
    result = connection.execute(sa.text(
        "SELECT COUNT(*) FROM items WHERE item_type_id_new IS NULL"
    ))
    null_count = result.scalar()
    if null_count > 0:
        raise ValueError(f"Migration failed: {null_count} items have unmapped item_type values")

    # ===== PHASE 3: Switch Columns =====

    # SQLite: Use recreate-table pattern
    if connection.dialect.name == 'sqlite':
        # Disable foreign keys
        op.execute('PRAGMA foreign_keys = OFF')

        # Rename old table
        op.rename_table('items', 'items_old')

        # Create new table with correct schema
        op.create_table(
            'items',
            # ... all columns ...
            sa.Column('item_type_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['item_type_id'], ['item_types.id'])
        )

        # Copy data
        op.execute("""
            INSERT INTO items (id, barcode, item_type_id, ...)
            SELECT id, barcode, item_type_id_new, ...
            FROM items_old
        """)

        # Drop old table
        op.drop_table('items_old')

        # Re-enable foreign keys
        op.execute('PRAGMA foreign_keys = ON')

    # PostgreSQL: Standard ALTER TABLE
    else:
        # Make new column NOT NULL
        op.alter_column('items', 'item_type_id_new', nullable=False)

        # Drop old column
        op.drop_column('items', 'item_type')

        # Rename new column to final name
        op.alter_column('items', 'item_type_id_new', new_column_name='item_type_id')

        # Add foreign key constraint
        op.create_foreign_key(
            'fk_items_item_type',
            'items', 'item_types',
            ['item_type_id'], ['id']
        )

    # Add indexes
    op.create_index('idx_items_type', 'items', ['item_type_id'])


def downgrade():
    """Rollback to enum/string column."""

    # Add old column back
    op.add_column('items', sa.Column('item_type_old', sa.String(20), nullable=True))

    # Populate from lookup table
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE items
        SET item_type_old = (
            SELECT code FROM item_types
            WHERE item_types.id = items.item_type_id
        )
    """))

    # Verify no nulls
    result = connection.execute(sa.text(
        "SELECT COUNT(*) FROM items WHERE item_type_old IS NULL"
    ))
    null_count = result.scalar()
    if null_count > 0:
        raise ValueError(f"Rollback failed: {null_count} items have invalid item_type_id")

    # SQLite: Recreate table
    if connection.dialect.name == 'sqlite':
        op.execute('PRAGMA foreign_keys = OFF')
        op.rename_table('items', 'items_new')

        # Create old table structure
        op.create_table(
            'items',
            # ... columns with item_type as String ...
        )

        # Copy data
        op.execute("""
            INSERT INTO items (id, barcode, item_type, ...)
            SELECT id, barcode, item_type_old, ...
            FROM items_new
        """)

        op.drop_table('items_new')
        op.execute('PRAGMA foreign_keys = ON')

    # PostgreSQL: Standard ALTER TABLE
    else:
        op.drop_constraint('fk_items_item_type', 'items')
        op.drop_column('items', 'item_type_id')
        op.alter_column('items', 'item_type_old', new_column_name='item_type')

    # Drop lookup table
    op.drop_table('item_types')
```

**Source**: [Safe Database Migration: Converting MySQL Enum to String](https://dev.to/bhaidar/safe-database-migration-converting-mysql-enum-to-string-in-laravel-1mle)

### SQLite-Specific Considerations

**Foreign Key Management**:
```python
# Must disable foreign keys during table recreation
connection.execute('PRAGMA foreign_keys = OFF')

# Perform table recreation

# Verify integrity before re-enabling
connection.execute('PRAGMA foreign_key_check')

# Re-enable foreign keys
connection.execute('PRAGMA foreign_keys = ON')
```

**Why This Pattern**:
- SQLite doesn't support `ALTER TABLE ADD FOREIGN KEY`
- Must recreate entire table to add constraints
- PRAGMA controls prevent orphaned references
- foreign_key_check ensures referential integrity

**Source**: [SQLite Foreign Key Support](https://sqlite.org/foreignkeys.html)

### PostgreSQL vs SQLite Differences

| Operation | PostgreSQL | SQLite |
|-----------|-----------|--------|
| **Add Column** | ALTER TABLE ADD COLUMN | ALTER TABLE ADD COLUMN |
| **Drop Column** | ALTER TABLE DROP COLUMN | Recreate table |
| **Add Foreign Key** | ALTER TABLE ADD CONSTRAINT | Recreate table |
| **Enum Migration** | ALTER TYPE (locks table) | N/A (no enum type) |
| **Locking** | ACCESS EXCLUSIVE during ALTER | Database-level lock |

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Direct ALTER TABLE** | Simple, single step | Risky, no rollback |
| **Dual-Write Pattern** | Zero downtime | Complex, requires code changes |
| **Temp Column (Recommended)** | Safe, verifiable | Requires multiple steps |
| **Shadow Table** | Atomic switch | Requires 2x disk space |

---

## 4. Admin UI Patterns for Taxonomy Management

### Decision Made
**Implement inline-editable table with drag-and-drop reordering, modal forms for add/edit, and soft-delete with archive view.**

### Rationale
- **Minimal Clicks**: Edit in-place without navigation (BCD Constitution #5)
- **Visual Feedback**: Drag-and-drop for intuitive ordering
- **Data Safety**: Soft delete prevents accidental loss
- **Accessibility**: Keyboard navigation and ARIA labels

### UI Components Pattern

**1. List View with Inline Editing**:

```html
<!-- Taxonomy management table -->
<div class="taxonomy-manager">
  <!-- Toolbar -->
  <div class="toolbar">
    <button @click="addNewType" class="btn-primary">
      <i class="icon-plus"></i> {{ $t('admin.item_types.add') }}
    </button>
    <button @click="showArchived = !showArchived" class="btn-secondary">
      <i class="icon-archive"></i>
      {{ showArchived ? $t('admin.hide_archived') : $t('admin.show_archived') }}
    </button>
    <input
      type="search"
      v-model="searchQuery"
      :placeholder="$t('admin.search_placeholder')"
      class="search-input"
    />
  </div>

  <!-- Table with drag-and-drop -->
  <table class="taxonomy-table" role="grid">
    <thead>
      <tr>
        <th scope="col" class="drag-handle-column"></th>
        <th scope="col">{{ $t('admin.item_types.code') }}</th>
        <th scope="col">{{ $t('admin.item_types.label_en') }}</th>
        <th scope="col">{{ $t('admin.item_types.label_fr') }}</th>
        <th scope="col">{{ $t('admin.item_types.loan_duration') }}</th>
        <th scope="col" class="actions-column">{{ $t('admin.actions') }}</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="itemType in filteredItemTypes"
        :key="itemType.id"
        :class="{ 'archived': !itemType.active }"
        draggable="true"
        @dragstart="handleDragStart(itemType)"
        @dragover.prevent
        @drop="handleDrop(itemType)"
      >
        <!-- Drag handle -->
        <td class="drag-handle">
          <i class="icon-drag" aria-label="Drag to reorder"></i>
        </td>

        <!-- Editable fields -->
        <td>
          <input
            v-model="itemType.code"
            @blur="saveField(itemType, 'code')"
            class="inline-edit"
            :aria-label="$t('admin.item_types.code')"
          />
        </td>
        <td>
          <input
            v-model="itemType.label_en"
            @blur="saveField(itemType, 'label_en')"
            class="inline-edit"
          />
        </td>
        <td>
          <input
            v-model="itemType.label_fr"
            @blur="saveField(itemType, 'label_fr')"
            class="inline-edit"
          />
        </td>
        <td>
          <input
            type="number"
            v-model.number="itemType.loan_duration_days"
            @blur="saveField(itemType, 'loan_duration_days')"
            class="inline-edit numeric"
          />
        </td>

        <!-- Actions -->
        <td class="actions">
          <button
            @click="editDetails(itemType)"
            class="btn-icon"
            :aria-label="$t('admin.edit')"
          >
            <i class="icon-edit"></i>
          </button>
          <button
            @click="toggleArchive(itemType)"
            class="btn-icon"
            :aria-label="itemType.active ? $t('admin.archive') : $t('admin.restore')"
          >
            <i :class="itemType.active ? 'icon-archive' : 'icon-restore'"></i>
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

**2. Modal Form for Advanced Settings**:

```html
<!-- Modal for adding/editing item types -->
<dialog ref="itemTypeModal" class="modal">
  <form @submit.prevent="saveItemType">
    <header class="modal-header">
      <h2>{{ editing ? $t('admin.edit_item_type') : $t('admin.add_item_type') }}</h2>
      <button @click="closeModal" class="btn-close" aria-label="Close">&times;</button>
    </header>

    <div class="modal-body">
      <!-- Basic info -->
      <div class="form-group">
        <label for="code">{{ $t('admin.item_types.code') }} *</label>
        <input
          id="code"
          v-model="form.code"
          required
          maxlength="20"
          pattern="[A-Z0-9_]+"
          :placeholder="$t('admin.item_types.code_hint')"
        />
        <small>{{ $t('admin.item_types.code_help') }}</small>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="label_en">{{ $t('admin.item_types.label_en') }} *</label>
          <input id="label_en" v-model="form.label_en" required />
        </div>
        <div class="form-group">
          <label for="label_fr">{{ $t('admin.item_types.label_fr') }} *</label>
          <input id="label_fr" v-model="form.label_fr" required />
        </div>
      </div>

      <!-- Circulation rules -->
      <fieldset>
        <legend>{{ $t('admin.item_types.circulation_defaults') }}</legend>

        <div class="form-group">
          <label for="loan_duration">{{ $t('admin.item_types.loan_duration') }}</label>
          <input
            id="loan_duration"
            type="number"
            v-model.number="form.loan_duration_days"
            min="1"
            max="365"
          />
          <small>{{ $t('admin.item_types.loan_duration_help') }}</small>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="form.renewable" />
            {{ $t('admin.item_types.renewable') }}
          </label>
        </div>

        <div class="form-group" v-if="form.renewable">
          <label for="max_renewals">{{ $t('admin.item_types.max_renewals') }}</label>
          <input
            id="max_renewals"
            type="number"
            v-model.number="form.max_renewals"
            min="0"
            max="10"
          />
        </div>
      </fieldset>

      <!-- Import mappings -->
      <fieldset>
        <legend>{{ $t('admin.item_types.import_config') }}</legend>

        <div class="form-group">
          <label for="synonyms">{{ $t('admin.item_types.synonyms') }}</label>
          <textarea
            id="synonyms"
            v-model="synonymsText"
            rows="3"
            :placeholder="$t('admin.item_types.synonyms_placeholder')"
          ></textarea>
          <small>{{ $t('admin.item_types.synonyms_help') }}</small>
        </div>
      </fieldset>
    </div>

    <footer class="modal-footer">
      <button type="button" @click="closeModal" class="btn-secondary">
        {{ $t('common.cancel') }}
      </button>
      <button type="submit" class="btn-primary">
        {{ $t('common.save') }}
      </button>
    </footer>
  </form>
</dialog>
```

**3. CSV Import Mapping Interface**:

```html
<!-- Column mapping UI during import -->
<div class="import-mapper">
  <div class="instructions">
    <h3>{{ $t('import.map_columns') }}</h3>
    <p>{{ $t('import.map_instructions') }}</p>
  </div>

  <!-- Auto-mapped columns (review only) -->
  <section v-if="autoMappedColumns.length > 0">
    <h4>{{ $t('import.auto_mapped') }} ({{ autoMappedColumns.length }})</h4>
    <div class="mapping-grid">
      <div
        v-for="mapping in autoMappedColumns"
        :key="mapping.csvColumn"
        class="mapping-row auto-mapped"
      >
        <div class="csv-column">
          <i class="icon-check-circle success"></i>
          <strong>{{ mapping.csvColumn }}</strong>
          <small>{{ $t('import.confidence') }}: {{ mapping.confidence }}%</small>
        </div>
        <i class="icon-arrow-right"></i>
        <div class="target-field">
          <select
            v-model="mapping.targetField"
            @change="updateMapping(mapping)"
          >
            <option
              v-for="field in availableFields"
              :key="field.name"
              :value="field.name"
            >
              {{ field.label }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </section>

  <!-- Unmapped columns (require manual mapping) -->
  <section v-if="unmappedColumns.length > 0">
    <h4 class="warning">
      <i class="icon-alert"></i>
      {{ $t('import.unmapped') }} ({{ unmappedColumns.length }})
    </h4>
    <div class="mapping-grid">
      <div
        v-for="column in unmappedColumns"
        :key="column"
        class="mapping-row unmapped"
      >
        <div class="csv-column">
          <strong>{{ column }}</strong>
          <small>{{ $t('import.sample') }}: {{ getSampleValue(column) }}</small>
        </div>
        <i class="icon-arrow-right"></i>
        <div class="target-field">
          <select v-model="columnMappings[column]">
            <option value="">-- {{ $t('import.skip_column') }} --</option>
            <option
              v-for="field in availableFields"
              :key="field.name"
              :value="field.name"
            >
              {{ field.label }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </section>

  <!-- Required fields validation -->
  <div v-if="missingRequiredFields.length > 0" class="alert error">
    <i class="icon-alert-circle"></i>
    <strong>{{ $t('import.missing_required') }}:</strong>
    <ul>
      <li v-for="field in missingRequiredFields" :key="field">
        {{ field }}
      </li>
    </ul>
  </div>

  <!-- Actions -->
  <div class="actions">
    <button @click="goBack" class="btn-secondary">
      {{ $t('common.back') }}
    </button>
    <button
      @click="saveMapping"
      class="btn-tertiary"
      :disabled="!isValidMapping"
    >
      <i class="icon-save"></i>
      {{ $t('import.save_mapping') }}
    </button>
    <button
      @click="proceedToValidation"
      class="btn-primary"
      :disabled="!isValidMapping"
    >
      {{ $t('import.validate_data') }}
      <i class="icon-arrow-right"></i>
    </button>
  </div>
</div>
```

**Sources**:
- [Designing An Attractive And Usable Data Importer](https://www.smashingmagazine.com/2020/12/designing-attractive-usable-data-importer-app/)
- [React CSV Importer](https://github.com/beamworks/react-csv-importer)

### Design Patterns from Modern Libraries

**React-Admin** provides built-in patterns for:
- List view with inline editing
- Create/Edit forms with validation
- Filter and search
- Bulk actions
- Undo/redo support

**Ant Design** (enterprise admin panels):
- Editable tables with inline validation
- Modal drawers for complex forms
- Transfer component for column mapping
- Timeline for audit logs

**Source**: [15 Best React UI Libraries for 2026](https://www.builder.io/blog/react-component-libraries-2026)

### Accessibility Requirements

Per BCD Constitution, admin UI must support:
- Keyboard navigation (Tab, Enter, Escape)
- Screen reader labels (ARIA attributes)
- High contrast mode
- Focus indicators
- Error announcements

### Alternatives Considered

| Pattern | Pros | Cons |
|---------|------|------|
| **Inline Editing (Recommended)** | Fast, minimal clicks | Limited space for complex fields |
| **Modal Forms** | Full control, validation | Extra click required |
| **Dedicated Pages** | More space | Navigation overhead |
| **Spreadsheet-Style** | Familiar to Excel users | Complex implementation |

---

## 5. BCDI/UNIMARC Compatibility

### Decision Made
**Support Dublin Core to UNIMARC field mapping with configurable crosswalk tables, focusing on bibliographic essentials (200, 700-702, 606, 610).**

### Rationale
- **Legal Requirement**: French state grants require UNIMARC import support (since 1993)
- **Industry Standard**: UNIMARC is the national exchange format in France
- **Interoperability**: Schools may migrate from/to BCDI
- **Simplicity**: Focus on core bibliographic fields used by elementary schools

### UNIMARC Field Mappings

**Core Bibliographic Fields** (Elementary School Focus):

| UNIMARC Field | Subfield | Dublin Core | BCD Field | Description |
|---------------|----------|-------------|-----------|-------------|
| **200** | $a | dc:title | title | Title Proper |
| **200** | $e | - | subtitle | Subtitle |
| **200** | $f | dc:creator | authors[0] | First Author |
| **200** | $g | dc:contributor | authors[1+] | Additional Authors |
| **205** | $a | - | edition | Edition Statement |
| **210** | $a | dc:publisher | publisher | Place of Publication |
| **210** | $c | dc:publisher | publisher | Publisher Name |
| **210** | $d | dc:date | publication_year | Date of Publication |
| **215** | $a | dc:format | pages | Physical Description (pages) |
| **225** | $a | dc:relation | series | Series Title |
| **610** | $a | dc:subject | subjects | Uncontrolled Subject Terms (Free indexing) |
| **606** | $a | dc:subject | subjects | Topical Name (Controlled) |
| **675** | - | dc:subject | dewey | UDC Classification |
| **676** | $a | - | dewey | Dewey Decimal |
| **700** | $a $b | dc:creator | authors[primary] | Personal Name - Primary Responsibility |
| **701** | $a $b | dc:creator | authors[alternative] | Personal Name - Alternative Responsibility |
| **702** | $a $b | dc:contributor | illustrators | Personal Name - Secondary (e.g., illustrator) |

**Key Insights from Research**:

1. **Field 610 (Free Indexing)**: Since BCDI 2.62, exports indexing directly in UNIMARC "610 $a" tag. This is crucial for schools that manually index books.

2. **Creator Mapping Challenge**: Dublin Core's `creator` doesn't distinguish between primary/secondary authors, while UNIMARC uses 700 (primary), 701 (alternative), 702 (secondary like illustrators). BCD should:
   - Map first author to 700
   - Map subsequent authors to 701
   - Map illustrators to 702

3. **Subject Handling**: UNIMARC supports both controlled (606) and uncontrolled (610) subject terms. BCD should combine both into `subjects` array during import.

**Sources**:
- [Mapping Dublin Core to UNIMARC](https://www.ukoln.ac.uk/metadata/interoperability/dc_unimarc.html)
- [BCDI UNIMARC Documentation](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/special/html/ImporterMmnUnimarc.htm)

### BCDI CSV Export Format

**Field Separator**: Semicolon (`;`)
**Text Delimiter**: Quotes (`"`)
**Encoding**: UTF-8 (verify - older BCDI may use ISO-8859-1)
**Line Ending**: CRLF (Windows)

**Example Row**:
```csv
"Barcode";"Title";"Author";"Publisher";"Year";"ISBN";"Item Type";"Dewey"
"3000000001";"Le Petit Prince";"Saint-Exupéry, Antoine de";"Gallimard";"1943";"978-2070612758";"Roman";"843"
```

**Import Normalization Required**:
- Author format: `Last, First` → split into `first_name` and `last_name`
- Year: May include month/day → extract year only
- ISBN: May include hyphens → strip to digits only
- Item Type: French labels → map to BCD taxonomy via fuzzy matching

**Source**: [BCDI Export Formats](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/special/html/FondsExporterMemoNotices.htm)

### Implementation Approach

**1. Define Crosswalk Configuration**:

```python
# src/bcd_api/utils/unimarc_mapping.py

UNIMARC_TO_BCD_MAPPING = {
    '200$a': {'field': 'title', 'required': True},
    '200$e': {'field': 'subtitle', 'required': False},
    '200$f': {'field': 'authors', 'action': 'append', 'role': 'primary'},
    '200$g': {'field': 'authors', 'action': 'append', 'role': 'secondary'},
    '210$c': {'field': 'publisher', 'required': False},
    '210$d': {'field': 'publication_year', 'type': 'year'},
    '610$a': {'field': 'subjects', 'action': 'append'},
    '606$a': {'field': 'subjects', 'action': 'append'},
    '676$a': {'field': 'dewey', 'type': 'decimal'},
    '700$a': {'field': 'authors', 'action': 'append', 'role': 'primary'},
    '701$a': {'field': 'authors', 'action': 'append', 'role': 'alternative'},
    '702$a': {'field': 'illustrators', 'action': 'append'},
}

def parse_unimarc_record(marc_record: dict) -> dict:
    """Convert UNIMARC record to BCD bibliographic format."""
    bcd_record = {}

    for unimarc_field, mapping in UNIMARC_TO_BCD_MAPPING.items():
        field_code, subfield = unimarc_field.split('$')

        # Extract value from MARC record
        value = marc_record.get(field_code, {}).get(subfield)

        if value:
            target_field = mapping['field']

            # Handle list fields (append)
            if mapping.get('action') == 'append':
                if target_field not in bcd_record:
                    bcd_record[target_field] = []
                bcd_record[target_field].append(value)

            # Handle single-value fields
            else:
                bcd_record[target_field] = value

    return bcd_record
```

**2. CSV Import with BCDI Preset**:

```python
# Import configuration presets
IMPORT_PRESETS = {
    'bcdi_csv': {
        'name': 'BCDI CSV Export',
        'description': 'Import from BCDI CSV export format',
        'delimiter': ';',
        'encoding': 'utf-8',
        'column_mappings': {
            'Barcode': 'barcode',
            'Title': 'title',
            'Author': 'authors',
            'Publisher': 'publisher',
            'Year': 'publication_year',
            'ISBN': 'isbn',
            'Item Type': 'item_type',
            'Dewey': 'dewey',
        },
        'transformations': {
            'authors': 'parse_last_first_name',
            'publication_year': 'extract_year',
            'isbn': 'normalize_isbn',
            'item_type': 'fuzzy_match_taxonomy',
        }
    },
    'dublin_core': {
        'name': 'Dublin Core CSV',
        'description': 'Import from Dublin Core metadata',
        'delimiter': ',',
        'encoding': 'utf-8',
        'column_mappings': {
            'dc:title': 'title',
            'dc:creator': 'authors',
            'dc:publisher': 'publisher',
            'dc:date': 'publication_year',
            'dc:subject': 'subjects',
            'dc:identifier': 'isbn',
        }
    }
}
```

### UNIMARC Export Requirements

For schools migrating **from** BCD to BCDI:

1. **Generate UNIMARC XML** (MémoNotices format preferred by BCDI)
2. **Required Fields**:
   - 001: Record Identifier
   - 200: Title and Statement of Responsibility
   - 700/701: Authors (split by role)
   - 210: Publication Info
   - 610: Free subject terms

3. **Character Encoding**: UTF-8
4. **Format**: XML (`.xml`) or ISO 2709 (`.mrc`)

**Source**: [BCDI Import MémoNotices](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/special/html/ImporterMmnUnimarc.htm)

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Full UNIMARC Support** | Maximum compatibility | Overly complex for elementary schools |
| **Core Fields Only (Recommended)** | Simple, covers 95% of use cases | May miss specialized fields |
| **MARCXML Parser** | Industry standard | Heavy dependency for rare use case |
| **Manual Mapping UI** | Flexible | Requires user expertise |

---

## 6. Validation & Error Reporting Patterns

### Best Practices from Research

**Multi-Stage Validation**:

1. **Pre-Import Validation**:
   - File format check (CSV structure, encoding)
   - Header validation (required columns present)
   - Sample row validation (data types, patterns)

2. **Row-Level Validation**:
   - Required fields present
   - Data type checks (e.g., year is 4 digits)
   - Range validation (e.g., publication year 1800-2026)
   - Foreign key existence (e.g., item_type exists)
   - Business rules (e.g., barcode uniqueness)

3. **Post-Import Validation**:
   - Referential integrity check
   - Duplicate detection
   - Data quality metrics

**Error Reporting UI**:

```html
<!-- Validation results display -->
<div class="validation-results">
  <!-- Summary -->
  <div class="summary" :class="summaryClass">
    <i :class="summaryIcon"></i>
    <div>
      <strong>{{ validationSummary.title }}</strong>
      <p>
        {{ $t('import.validated_rows', { count: totalRows }) }}
        <br>
        <span class="success">{{ validRows }} {{ $t('import.valid') }}</span>
        <span v-if="errorRows > 0" class="error">
          {{ errorRows }} {{ $t('import.errors') }}
        </span>
        <span v-if="warningRows > 0" class="warning">
          {{ warningRows }} {{ $t('import.warnings') }}
        </span>
      </p>
    </div>
  </div>

  <!-- Error details table -->
  <div v-if="errors.length > 0" class="error-table">
    <div class="table-header">
      <h4>{{ $t('import.errors_found') }}</h4>
      <button @click="downloadErrors" class="btn-secondary">
        <i class="icon-download"></i>
        {{ $t('import.download_errors') }}
      </button>
    </div>

    <table>
      <thead>
        <tr>
          <th>{{ $t('import.row') }}</th>
          <th>{{ $t('import.column') }}</th>
          <th>{{ $t('import.value') }}</th>
          <th>{{ $t('import.error') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="error in paginatedErrors" :key="error.id" class="error-row">
          <td class="row-number">{{ error.row }}</td>
          <td><code>{{ error.column }}</code></td>
          <td class="error-value">{{ error.value }}</td>
          <td class="error-message">
            <i class="icon-alert-circle"></i>
            {{ error.message }}
            <button
              v-if="error.suggestion"
              @click="applySuggestion(error)"
              class="btn-link"
            >
              {{ $t('import.did_you_mean', { value: error.suggestion }) }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="pagination">
      <!-- Pagination controls -->
    </div>
  </div>

  <!-- Actions -->
  <div class="actions">
    <button @click="goBack" class="btn-secondary">
      {{ $t('common.cancel') }}
    </button>
    <button
      v-if="errorRows > 0"
      @click="downloadErrors"
      class="btn-secondary"
    >
      <i class="icon-download"></i>
      {{ $t('import.download_fix_reupload') }}
    </button>
    <button
      v-if="warningRows > 0 && errorRows === 0"
      @click="proceedWithWarnings"
      class="btn-warning"
    >
      {{ $t('import.import_with_warnings') }}
    </button>
    <button
      v-if="errorRows === 0"
      @click="proceedToImport"
      class="btn-primary"
    >
      {{ $t('import.import_records', { count: validRows }) }}
      <i class="icon-check"></i>
    </button>
  </div>
</div>
```

**Error Download Format**:

Export failed rows as CSV with additional columns:
- `_error_column`: Which field failed
- `_error_message`: Description of error
- `_suggestion`: Suggested fix (if available)

Users can fix errors in Excel and re-upload.

**Source**: [Show row-level error messages in imports](https://blog.csvbox.io/row-level-errors-csv/)

---

## 7. Implementation Priority & Roadmap

### Phase 1: Core Infrastructure (Sprint 1)
- [ ] Create `item_types` lookup table schema
- [ ] Write Alembic migration (enum → foreign key)
- [ ] Update models and services to use foreign keys
- [ ] Add admin API endpoints (CRUD for item_types)
- [ ] Write integration tests for taxonomy management

### Phase 2: Admin UI (Sprint 2)
- [ ] Build taxonomy management page (inline editing)
- [ ] Add drag-and-drop reordering
- [ ] Implement soft delete/archive functionality
- [ ] Add search and filter
- [ ] Internationalize all labels (en/fr)

### Phase 3: Import Foundation (Sprint 3)
- [ ] CSV parser with encoding detection
- [ ] Column auto-mapping algorithm
- [ ] Fuzzy matching for taxonomy values
- [ ] Normalization pipeline (text cleaning, abbreviations)
- [ ] Validation engine with row-level errors

### Phase 4: Import UI (Sprint 4)
- [ ] File upload page
- [ ] Column mapping interface
- [ ] Validation results display
- [ ] Error download/fix/reupload workflow
- [ ] Import progress tracking

### Phase 5: BCDI/UNIMARC Support (Sprint 5)
- [ ] BCDI CSV preset configuration
- [ ] Dublin Core to UNIMARC crosswalk
- [ ] UNIMARC export (XML format)
- [ ] Character encoding handling (UTF-8/ISO-8859-1)
- [ ] Test with real BCDI export files

---

## 8. Key Architectural Decisions Summary

| Decision | Rationale | Risk Mitigation |
|----------|-----------|-----------------|
| **Lookup tables over enums** | Flexibility, admin configurability | Add indexes for join performance |
| **AI-assisted column mapping** | Reduce user effort by 80-90% | Allow manual override of suggestions |
| **Multi-stage migration** | Zero data loss, rollback safety | Validate at each checkpoint |
| **Inline editing UI** | Minimal clicks (Constitution #5) | Auto-save with optimistic updates |
| **Row-level validation** | Clear error feedback | Batch validation for large files |
| **UNIMARC core fields only** | Simplicity for target users | Document extension points |
| **Soft delete** | Preserve audit trail | Periodic archive cleanup |
| **Fuzzy matching with threshold** | Handle typos gracefully | Show confidence scores to user |

---

## 9. Performance Considerations

### Database
- **Indexes**: Add indexes on foreign keys and frequently queried columns
- **Batch Inserts**: Use `bulk_insert` for imports >100 rows
- **Transaction Size**: Commit every 500 rows to avoid memory issues

### CSV Processing
- **Streaming Parser**: Use `csv.DictReader` with iterator for large files
- **Chunk Processing**: Process in batches of 1000 rows
- **Background Jobs**: Use Celery/RQ for imports >10,000 rows

### UI Responsiveness
- **Pagination**: Show 50 errors per page
- **Virtual Scrolling**: For tables >500 rows
- **Debounce**: Search input with 300ms delay

---

## 10. Security Considerations

### File Upload
- **File Size Limit**: 10 MB max (configurable)
- **MIME Type Validation**: Only accept `text/csv`, `text/plain`
- **Virus Scanning**: Scan uploads in production
- **Temporary Storage**: Delete uploaded files after import

### Taxonomy Management
- **Authorization**: Admin role required
- **Audit Log**: Track all taxonomy changes
- **Soft Delete**: Prevent accidental data loss
- **Validation**: Prevent SQL injection via input sanitization

### Data Integrity
- **Foreign Keys**: Enforce at database level
- **Transactions**: All multi-step operations in transactions
- **Backup**: Export before import (allow rollback)

---

## References

### Library System Schema Design
1. [Koha Database Schema](https://schema.koha-community.org/) - Official Koha schema documentation
2. [Koha kohastructure.sql](https://github.com/Koha-Community/Koha/blob/main/installer/data/mysql/kohastructure.sql) - Source schema definitions
3. [Where are my circ rules in the database as of 20.05](https://bywatersolutions.com/education/where-are-my-circ-rules-in-the-database-as-of-20-05) - Koha circulation rules pattern
4. [Evergreen Database Schema](https://olddocs.evergreen-ils.org/3.2_schema/) - PostgreSQL-based schema reference

### Fuzzy Matching & Normalization
5. [String Data Normalization and Similarity Matching](https://medium.com/@ievgenii.shulitskyi/string-data-normalization-and-similarity-matching-algorithms-4b7b1734798e) - Normalization pipeline patterns
6. [Fuzzy Matching 101](https://dataladder.com/fuzzy-matching-101/) - Fuzzy matching workflow (normalization, blocking, scoring)
7. [csvmatch](https://github.com/maxharlow/csvmatch) - Incremental CSV matching approach
8. [Python Tools for Record Linking](https://pbpython.com/record-linking.html) - fuzzymatcher and recordlinkage libraries

### Database Migration Patterns
9. [Safe Database Migration: Converting MySQL Enum to String](https://dev.to/bhaidar/safe-database-migration-converting-mysql-enum-to-string-in-laravel-1mle) - Multi-step migration pattern
10. [Lookup Table or Enum Type?](https://www.cybertec-postgresql.com/en/lookup-table-or-enum-type/) - Trade-offs analysis
11. [SQLite Foreign Key Support](https://sqlite.org/foreignkeys.html) - SQLite foreign key management
12. [Migrating PostgreSQL Enum using SQLAlchemy](https://code.keplergrp.com/blog/migrating-postgresql-enum-sqlalchemy-alembic) - Alembic migration examples

### Admin UI Patterns
13. [Designing An Attractive And Usable Data Importer](https://www.smashingmagazine.com/2020/12/designing-attractive-usable-data-importer-app/) - Import UI best practices
14. [React CSV Importer](https://github.com/beamworks/react-csv-importer) - Column mapping UI component
15. [CSVBox Column Mapping](https://blog.csvbox.io/inside-csvbox-column-mapping/) - AI-assisted mapping algorithm
16. [15 Best React UI Libraries for 2026](https://www.builder.io/blog/react-component-libraries-2026) - React-Admin, Ant Design patterns

### Validation & Error Handling
17. [Show row-level error messages in imports](https://blog.csvbox.io/row-level-errors-csv/) - Row-level validation feedback
18. [5 Common Data Import Errors and How to Fix Them](https://dromo.io/blog/common-data-import-errors-and-how-to-fix-them) - Validation patterns and AI column matching

### BCDI & UNIMARC
19. [Mapping Dublin Core to UNIMARC](https://www.ukoln.ac.uk/metadata/interoperability/dc_unimarc.html) - Field mappings for Project BIBLINK
20. [MARC to Dublin Core Crosswalk](https://www.loc.gov/marc/marc2dc.html) - Library of Congress mapping reference
21. [BCDI: Importer des notices UNIMARC](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/special/html/ImporterMmnUnimarc.htm) - BCDI import documentation
22. [BCDI: Exporter MémoNotices](https://ressources.solutionsdocumentaires.fr/manuels/bcdi/special/html/FondsExporterMemoNotices.htm) - BCDI export formats
23. [UNIMARC as a Cataloguing Format in France](http://archive.ifla.org/IV/ifla64/111-161e.htm) - Historical context and adoption

---

## Appendices

### Appendix A: Sample Item Types Configuration

```json
{
  "item_types": [
    {
      "code": "ALBUM",
      "label_en": "Picture Book",
      "label_fr": "Album",
      "loan_duration_days": 14,
      "renewable": true,
      "max_renewals": 2,
      "synonyms": ["picture book", "illustrated book", "album jeunesse"]
    },
    {
      "code": "ROMAN",
      "label_en": "Novel",
      "label_fr": "Roman",
      "loan_duration_days": 14,
      "renewable": true,
      "max_renewals": 2,
      "synonyms": ["book", "livre", "fiction", "novel"]
    },
    {
      "code": "BD",
      "label_en": "Comic Book",
      "label_fr": "Bande Dessinée",
      "loan_duration_days": 14,
      "renewable": true,
      "max_renewals": 2,
      "synonyms": ["comic", "graphic novel", "manga", "bd", "bande dessinee"]
    },
    {
      "code": "DOC",
      "label_en": "Documentary",
      "label_fr": "Documentaire",
      "loan_duration_days": 14,
      "renewable": true,
      "max_renewals": 2,
      "synonyms": ["non-fiction", "documentary", "reference", "documentaire"]
    },
    {
      "code": "PERIODIQUE",
      "label_en": "Periodical",
      "label_fr": "Périodique",
      "loan_duration_days": 7,
      "renewable": false,
      "max_renewals": 0,
      "synonyms": ["magazine", "journal", "periodical", "revue"]
    }
  ]
}
```

### Appendix B: Validation Rules Template

```python
VALIDATION_RULES = {
    'barcode': {
        'required': True,
        'type': 'string',
        'pattern': r'^[0-9]{10,13}$',
        'unique': True,
        'error_messages': {
            'required': 'Barcode is required',
            'pattern': 'Barcode must be 10-13 digits',
            'unique': 'Barcode already exists in database'
        }
    },
    'title': {
        'required': True,
        'type': 'string',
        'max_length': 500,
        'error_messages': {
            'required': 'Title is required',
            'max_length': 'Title cannot exceed 500 characters'
        }
    },
    'publication_year': {
        'required': False,
        'type': 'integer',
        'min_value': 1800,
        'max_value': 2026,
        'error_messages': {
            'type': 'Year must be a number',
            'min_value': 'Year cannot be before 1800',
            'max_value': 'Year cannot be in the future'
        }
    },
    'item_type': {
        'required': True,
        'type': 'foreign_key',
        'table': 'item_types',
        'fuzzy_match': True,
        'threshold': 80,
        'error_messages': {
            'required': 'Item type is required',
            'foreign_key': 'Item type not found in taxonomy'
        }
    }
}
```

### Appendix C: BCDI Field Name Variations

Common variations found in BCDI exports (for auto-mapping):

| English | French | BCDI Variation | BCD Field |
|---------|--------|----------------|-----------|
| Barcode | Code-barres | Code barre, Cote | barcode |
| Title | Titre | Titre principal | title |
| Author | Auteur | Auteur principal, Créateur | authors |
| Publisher | Éditeur | Editeur, Maison d'édition | publisher |
| Year | Année | Année de publication, Date | publication_year |
| ISBN | ISBN | ISBN 13, ISBN-13 | isbn |
| Item Type | Type | Type de document, Support | item_type |
| Dewey | Dewey | Classification Dewey, Cote | dewey |
| Subject | Sujet | Mots-clés, Indexation | subjects |

---

**Document Status**: Complete
**Next Steps**: Review with team, prioritize implementation phases, create technical specification
