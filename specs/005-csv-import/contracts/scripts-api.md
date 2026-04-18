# Conversion Scripts Interface

**Feature**: 005-csv-import
**Purpose**: Define command-line interfaces for CSV conversion scripts

## Overview

Conversion scripts transform external CSV formats (BCDI, generic French CSV) into Dublin Core format for import into BCD. Scripts are **standalone Python utilities** that run outside the web application.

**Design Philosophy**: Unix-style tools that do one thing well - read CSV, transform to Dublin Core, write CSV.

## Script 1: BCDI to Dublin Core

### Location

`scripts/convert/bcdi_to_dublin_core.py`

### Usage

```bash
python scripts/convert/bcdi_to_dublin_core.py <input_bcdi.csv> <output_dublin_core.csv>
```

### Example

```bash
python scripts/convert/bcdi_to_dublin_core.py \
    data/sample_imports/export_bcdi_2026.csv \
    catalog_dublin_core.csv
```

### Input Format (BCDI CSV)

**Encoding**: Windows-1252 (default), auto-detect fallback
**Delimiter**: Semicolon (`;`) or comma (`,`), auto-detected

**Expected columns** (French names):
- `ISBN` → dc.identifier
- `Titre` → dc.title
- `Auteur` → dc.creator
- `Editeur` → dc.publisher
- `Support` → dc.type (plain text, no transformation)
- `Cote` → dc.subject
- `Année` → dc.date

### Output Format (Dublin Core CSV)

**Encoding**: UTF-8 with BOM
**Delimiter**: Comma (`,`)

**Columns**: Standard Dublin Core format as per export-api.yaml

### Transformations

| BCDI Column | Dublin Core Column | Transformation |
|-------------|-------------------|----------------|
| ISBN | dc.identifier | Add "isbn:" prefix if not present |
| Titre | dc.title | Direct copy |
| Auteur | dc.creator | Direct copy (preserve as-is) |
| Editeur | dc.publisher | Direct copy |
| Support | dc.type | **Direct copy** - no normalization ("Livre" stays "Livre") |
| Cote | dc.subject | Direct copy |
| Année | dc.date | Direct copy |

**Key design**: NO medium type normalization. "Livre" → "Livre", "CD Audio" → "CD Audio", "DVD Vidéo" → "DVD Vidéo".

### Exit Codes

- `0`: Success
- `1`: File not found or invalid arguments
- `2`: CSV parsing error
- `3`: Encoding detection failed

### Output Messages

**Success**:
```
✅ Converted export_bcdi_2026.csv → catalog_dublin_core.csv
   Encoding: windows-1252 → UTF-8
   Format: BCDI → Dublin Core
   Rows: 245
```

**Error**:
```
❌ Error: Input file not found: export_bcdi_2026.csv
❌ Error: Invalid CSV format (missing required column: Titre)
```

---

## Script 2: French CSV to Dublin Core

### Location

`scripts/convert/french_csv_to_dublin_core.py`

### Usage

```bash
python scripts/convert/french_csv_to_dublin_core.py <input.csv> <output_dublin_core.csv>
```

### Example

```bash
python scripts/convert/french_csv_to_dublin_core.py \
    mes_livres.csv \
    catalog_dublin_core.csv
```

### Input Format (Generic French CSV)

**Encoding**: Auto-detected (UTF-8, Latin-1, or Windows-1252)
**Delimiter**: Auto-detected (comma, semicolon, or tab)

**Column name variations recognized** (case-insensitive):

| Recognized Patterns | Maps To |
|---------------------|---------|
| "isbn", "isbn13", "numéro isbn", "numero isbn" | dc.identifier |
| "titre", "title", "nom" | dc.title |
| "auteur", "author", "créateur", "createur" | dc.creator |
| "éditeur", "editeur", "publisher", "maison d'édition" | dc.publisher |
| "type", "support", "format", "média", "media" | dc.type |
| "cote", "dewey", "classification", "sujet" | dc.subject |
| "année", "annee", "date", "date de publication" | dc.date |

### Column Detection Algorithm

1. **Normalize** column name: lowercase, strip whitespace, remove accents
2. **Match** against pattern dictionary (case-insensitive, accent-insensitive)
3. **Map** to Dublin Core column
4. **Report** unmapped columns (warning, not error)

### Output Messages

**Success with mapping info**:
```
📖 Detected encoding: utf-8
📖 Detected delimiter: ,
✅ Mapped columns:
   Titre → dc.title
   Auteur → dc.creator
   Type → dc.type
   ISBN → dc.identifier
⚠️  Unmapped columns (will be ignored): Notes, Prix d'achat
✅ Converted mes_livres.csv → catalog_dublin_core.csv
   Rows: 157
```

**Error**:
```
❌ Error: Could not detect CSV encoding
❌ Error: No recognizable columns found (expected: titre, auteur, isbn)
```

### Exit Codes

Same as BCDI converter (0 = success, 1-3 = errors)

---

## Common Script Features

### Encoding Detection

Both scripts use this detection pattern:

```python
def detect_encoding(file_path):
    """Try encodings in order of likelihood."""
    encodings = ['utf-8', 'windows-1252', 'latin-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue

    raise ValueError("Could not detect file encoding")
```

### Delimiter Detection

```python
def detect_delimiter(file_path, encoding):
    """Auto-detect delimiter (comma, semicolon, tab)."""
    import csv

    with open(file_path, 'r', encoding=encoding) as f:
        sample = f.read(1024)
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter
```

### UTF-8 BOM Output

Both scripts write UTF-8 with BOM for Excel compatibility:

```python
with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
    # utf-8-sig automatically adds BOM
    writer = csv.DictWriter(f, fieldnames=dublin_core_columns)
    writer.writeheader()
    # ...
```

### ISBN Normalization

Add "isbn:" prefix if not present:

```python
def normalize_isbn(isbn_value):
    """Add isbn: prefix if missing."""
    if not isbn_value:
        return ""

    if isbn_value.startswith("isbn:"):
        return isbn_value

    return f"isbn:{isbn_value}"
```

---

## Testing

### Test Data

Sample files in `data/sample_imports/`:
- `bcdi_sample.csv` - BCDI export (semicolon, Windows-1252)
- `french_sample.csv` - Generic French CSV (comma, UTF-8)

### Test Cases

**BCDI Conversion**:
```bash
# Input: BCDI CSV with French column names
# Expected: Dublin Core CSV with all columns mapped
python scripts/convert/bcdi_to_dublin_core.py \
    tests/fixtures/bcdi_sample.csv \
    /tmp/output.csv

# Verify: output has dc.title, dc.creator, dc.type columns
# Verify: encoding is UTF-8
# Verify: medium types unchanged ("Livre" still "Livre")
```

**French CSV Conversion**:
```bash
# Input: Custom CSV with variations ("Titre du livre", "Nom auteur")
# Expected: Auto-detection works, columns mapped
python scripts/convert/french_csv_to_dublin_core.py \
    tests/fixtures/custom_french.csv \
    /tmp/output.csv

# Verify: detected columns correctly
# Verify: unmapped columns reported in output
```

### Round-Trip Test

```bash
# 1. Export from BCD
curl http://localhost:8000/api/v1/catalog/export > export1.csv

# 2. Convert to BCDI format (hypothetical reverse script)
python scripts/convert/dublin_core_to_bcdi.py export1.csv bcdi.csv

# 3. Convert back to Dublin Core
python scripts/convert/bcdi_to_dublin_core.py bcdi.csv export2.csv

# 4. Import to BCD
curl -F "file=@export2.csv" http://localhost:8000/api/v1/catalog/import-dc

# 5. Export again
curl http://localhost:8000/api/v1/catalog/export > export3.csv

# 6. Verify exports are identical
diff export1.csv export3.csv
# Expected: No differences
```

---

## Integration with BCD Web UI

### User Workflow

1. **User has BCDI export** (`export_bcdi.csv`)
2. **Run conversion script**:
   ```bash
   python scripts/convert/bcdi_to_dublin_core.py export_bcdi.csv catalog.csv
   ```
3. **Upload to BCD** via web UI:
   - Click "Import Catalog" button
   - Select `catalog.csv`
   - Click "Import"
4. **Success**: Records imported into BCD

### Documentation

Scripts include docstring with usage examples:

```python
#!/usr/bin/env python3
"""
Convert BCDI CSV export to Dublin Core format.

Usage:
    python bcdi_to_dublin_core.py input_bcdi.csv output_dublin_core.csv

Example:
    python bcdi_to_dublin_core.py export_bcdi_2026.csv catalog.csv

The script will:
- Auto-detect encoding (Windows-1252, UTF-8, Latin-1)
- Convert French column names to Dublin Core
- Preserve medium types as-is (no normalization)
- Output UTF-8 CSV with BOM for Excel compatibility
"""
```

README.md includes full conversion guide:

```markdown
## Importing from BCDI

If you have a BCDI export file:

1. Run the conversion script:
   ```bash
   python scripts/convert/bcdi_to_dublin_core.py your_export.csv catalog.csv
   ```

2. Import the converted file via the web UI

The script handles French characters and preserves medium types.
```

---

## Performance

**Target**: Convert 10,000 rows in <5 seconds

**Strategy**:
- Stream processing (csv.DictReader/DictWriter)
- No in-memory file buffering
- Simple column mapping (O(1) lookup)

**Memory profile**:
- Peak: <50MB for 10,000 rows
- CPU: Single-threaded (adequate for script usage)
