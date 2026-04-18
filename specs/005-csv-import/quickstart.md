# Quick Start Guide: CSV Import/Export Implementation

**Feature**: 005-csv-import
**Date**: 2026-02-06
**For**: Developers implementing CSV export and conversion scripts

## Overview

This guide provides code examples for implementing the CSV export feature. The import functionality already exists in production (`dublin_core_import.py`, 355 lines) - this feature adds the export counterpart.

**What to build**:
1. Export service (`export_service.py`) - Generate Dublin Core CSV from catalog
2. Export API endpoint (`catalog.py`) - FastAPI route returning CSV file
3. BCDI conversion script (`bcdi_to_dublin_core.py`) - Transform BCDI → Dublin Core
4. French CSV conversion script (`french_csv_to_dublin_core.py`) - Auto-detect columns
5. Vue export button (`CatalogPage.js`) - Simple download button

## Table of Contents

1. [Export Service (Backend)](#1-export-service-backend)
2. [API Endpoint](#2-api-endpoint)
3. [BCDI Conversion Script](#3-bcdi-conversion-script)
4. [French CSV Conversion Script](#4-french-csv-conversion-script)
5. [Vue Export Button (Frontend)](#5-vue-export-button-frontend)
6. [Testing](#6-testing)

---

## 1. Export Service (Backend)

**File**: `src/bcd_api/services/export_service.py`

```python
"""Export service for generating Dublin Core CSV from catalog."""
import csv
from io import StringIO
from typing import List
import json
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item


class ExportService:
    """Service for exporting catalog to Dublin Core CSV."""

    # Dublin Core columns (matches import format)
    DC_COLUMNS = [
        'dc.title',
        'dc.identifier',
        'dc.creator',
        'dc.contributor',
        'dc.publisher',
        'dc.date',
        'dc.type',
        'dc.format',
        'dc.subject',
        'dc.description',
        'dc.language',
        'dc.coverage',
        'item.id',
        'item.callNumber',
        'item.acquisitionDate',
        'item.fundingSource',
        'dc.rights',
    ]

    def __init__(self, db: Session):
        self.db = db

    def export_catalog_to_csv(self) -> str:
        """
        Export entire catalog to Dublin Core CSV format.

        Returns:
            CSV string with UTF-8 encoding (BOM added by caller)

        Performance:
            Uses joinedload to avoid N+1 queries
            Streams CSV generation (no full file in memory)
        """
        # Fetch all records with items in single query (avoid N+1)
        records = self.db.query(BiblographicRecord).options(
            joinedload(BiblographicRecord.items)
        ).all()

        # Check row limit (spec FR-008)
        total_rows = sum(max(len(record.items), 1) for record in records)
        if total_rows > 10000:
            raise ValueError(
                f"Export exceeds 10,000 row limit. "
                f"Catalog has {total_rows} items. "
                f"Contact support for bulk export options."
            )

        # Generate CSV
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=self.DC_COLUMNS,
            quoting=csv.QUOTE_MINIMAL,  # Only quote when necessary (RFC 4180)
        )
        writer.writeheader()

        # Write one row per item (or one row with empty item fields if no items)
        for record in records:
            if record.items:
                # One CSV row per item
                for item in record.items:
                    writer.writerow(self._record_to_dict(record, item))
            else:
                # Record with no items: one row with empty item columns
                writer.writerow(self._record_to_dict(record, None))

        return output.getvalue()

    def _record_to_dict(self, record: BiblographicRecord, item: Item = None) -> dict:
        """
        Convert BiblographicRecord + Item to Dublin Core dictionary.

        Args:
            record: BiblographicRecord instance
            item: Item instance (or None if record has no items)

        Returns:
            Dictionary with Dublin Core column names as keys
        """
        # Parse JSON arrays (authors, illustrators, keywords)
        authors = self._parse_json_array(record.authors)
        illustrators = self._parse_json_array(record.illustrators)
        keywords = self._parse_json_array(record.keywords)

        # Build Dublin Core row
        row = {
            # Required
            'dc.title': record.title or '',

            # Identifiers
            'dc.identifier': f'isbn:{record.isbn}' if record.isbn else '',

            # Creators (pipe-separated)
            'dc.creator': '|'.join(authors) if authors else '',
            'dc.contributor': '|'.join(illustrators) if illustrators else '',

            # Publication
            'dc.publisher': record.publisher or '',
            'dc.date': str(record.publication_year) if record.publication_year else '',

            # Type and format
            'dc.type': record.medium_type or '',  # Plain text, no transformation!
            'dc.format': f'{record.page_count} pages' if record.page_count else '',

            # Subject and description
            'dc.subject': '|'.join(keywords) if keywords else '',
            'dc.description': record.description or '',

            # Language and coverage
            'dc.language': record.language or '',
            'dc.coverage': record.level or '',

            # Item columns (empty if no item)
            'item.id': item.item_id if item else '',
            'item.callNumber': item.call_number if item else '',
            'item.acquisitionDate': (
                item.acquisition_date.isoformat() if item and item.acquisition_date else ''
            ),
            'item.fundingSource': item.funding_source if item else '',
            'dc.rights': 'Loanable' if item and item.loanable else (
                'Not loanable' if item and not item.loanable else ''
            ),
        }

        return row

    @staticmethod
    def _parse_json_array(json_str: str) -> List[str]:
        """
        Parse JSON array string to Python list.

        Args:
            json_str: JSON string like '["item1", "item2"]'

        Returns:
            Python list, or empty list if null/invalid
        """
        if not json_str:
            return []

        try:
            parsed = json.loads(json_str)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
```

---

## 2. API Endpoint

**File**: `src/bcd_api/api/v1/catalog.py` (add to existing file)

```python
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime

from src.bcd_api.core.database import get_db
from src.bcd_api.services.export_service import ExportService


@router.get("/export", response_class=Response)
async def export_catalog(
    db: Session = Depends(get_db)
):
    """
    Export entire catalog to Dublin Core CSV format.

    Returns:
        CSV file download with UTF-8 encoding and BOM

    Raises:
        400: If export exceeds 10,000 row limit
        500: If export generation fails
    """
    try:
        # Generate CSV
        export_service = ExportService(db)
        csv_content = export_service.export_catalog_to_csv()

        # Add UTF-8 BOM for Excel compatibility
        csv_with_bom = '\ufeff' + csv_content

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'catalog_export_{timestamp}.csv'

        # Return as downloadable file
        return Response(
            content=csv_with_bom.encode('utf-8'),
            media_type='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except ValueError as e:
        # Row limit exceeded (spec FR-008)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Database or other errors
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )
```

---

## 3. BCDI Conversion Script

**File**: `scripts/convert/bcdi_to_dublin_core.py`

```python
#!/usr/bin/env python3
"""
Convert BCDI CSV export to Dublin Core format.

Usage:
    python scripts/convert/bcdi_to_dublin_core.py input_bcdi.csv output_dublin_core.csv

Example:
    python scripts/convert/bcdi_to_dublin_core.py export_bcdi_2026.csv catalog.csv
"""

import csv
import sys
from pathlib import Path


# BCDI → Dublin Core column mapping
BCDI_MAPPING = {
    'ISBN': 'dc.identifier',
    'Titre': 'dc.title',
    'Auteur': 'dc.creator',
    'Editeur': 'dc.publisher',
    'Support': 'dc.type',  # Plain text, no transformation
    'Cote': 'dc.subject',
    'Année': 'dc.date',
}

# Dublin Core columns (full set)
DC_COLUMNS = [
    'dc.title', 'dc.identifier', 'dc.creator', 'dc.contributor',
    'dc.publisher', 'dc.date', 'dc.type', 'dc.format',
    'dc.subject', 'dc.description', 'dc.language', 'dc.coverage',
    'item.id', 'item.callNumber', 'item.acquisitionDate', 'item.fundingSource', 'dc.rights'
]


def detect_encoding(file_path):
    """Detect file encoding (UTF-8, Windows-1252, or Latin-1)."""
    encodings = ['utf-8', 'windows-1252', 'latin-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not detect encoding for {file_path}")


def detect_delimiter(file_path, encoding):
    """Auto-detect CSV delimiter (comma, semicolon, or tab)."""
    with open(file_path, 'r', encoding=encoding) as f:
        sample = f.read(1024)
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter


def convert_bcdi_to_dublin_core(input_file, output_file):
    """Convert BCDI CSV to Dublin Core CSV."""
    # Detect encoding and delimiter
    input_encoding = detect_encoding(input_file)
    delimiter = detect_delimiter(input_file, input_encoding)

    print(f"📖 Detected encoding: {input_encoding}")
    print(f"📖 Detected delimiter: {repr(delimiter)}")

    # Read BCDI CSV
    with open(input_file, 'r', encoding=input_encoding) as infile:
        reader = csv.DictReader(infile, delimiter=delimiter)
        rows = list(reader)

    # Write Dublin Core CSV (UTF-8 with BOM)
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=DC_COLUMNS)
        writer.writeheader()

        for row in rows:
            # Map BCDI columns to Dublin Core
            dc_row = {col: '' for col in DC_COLUMNS}  # Initialize with empty strings

            for bcdi_col, dc_col in BCDI_MAPPING.items():
                if bcdi_col in row and row[bcdi_col]:
                    value = row[bcdi_col].strip()

                    # Special handling for ISBN: add prefix
                    if dc_col == 'dc.identifier' and value and not value.startswith('isbn:'):
                        value = f'isbn:{value}'

                    dc_row[dc_col] = value

            writer.writerow(dc_row)

    # Success message
    print(f"✅ Converted {input_file} → {output_file}")
    print(f"   Encoding: {input_encoding} → UTF-8")
    print(f"   Format: BCDI → Dublin Core")
    print(f"   Rows: {len(rows)}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python bcdi_to_dublin_core.py <input_bcdi.csv> <output_dublin_core.csv>")
        print("\nExample:")
        print("  python bcdi_to_dublin_core.py export_bcdi_2026.csv catalog.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Validate input file exists
    if not Path(input_file).exists():
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)

    try:
        convert_bcdi_to_dublin_core(input_file, output_file)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## 4. French CSV Conversion Script

**File**: `scripts/convert/french_csv_to_dublin_core.py`

```python
#!/usr/bin/env python3
"""
Convert generic French CSV to Dublin Core format with auto-detection.

Usage:
    python scripts/convert/french_csv_to_dublin_core.py input.csv output_dublin_core.csv

Example:
    python scripts/convert/french_csv_to_dublin_core.py mes_livres.csv catalog.csv
"""

import csv
import sys
import unicodedata
from pathlib import Path


# French column name patterns → Dublin Core (case-insensitive, accent-insensitive)
COLUMN_PATTERNS = {
    # ISBN variations
    'isbn': 'dc.identifier',
    'isbn13': 'dc.identifier',
    'numero isbn': 'dc.identifier',

    # Title variations
    'titre': 'dc.title',
    'title': 'dc.title',
    'nom': 'dc.title',

    # Author variations
    'auteur': 'dc.creator',
    'author': 'dc.creator',
    'createur': 'dc.creator',

    # Publisher variations
    'editeur': 'dc.publisher',
    'publisher': 'dc.publisher',

    # Type variations
    'type': 'dc.type',
    'support': 'dc.type',
    'format': 'dc.type',
    'media': 'dc.type',

    # Subject variations
    'cote': 'dc.subject',
    'dewey': 'dc.subject',
    'classification': 'dc.subject',
    'sujet': 'dc.subject',

    # Date variations
    'annee': 'dc.date',
    'date': 'dc.date',
    'date de publication': 'dc.date',
}

DC_COLUMNS = [
    'dc.title', 'dc.identifier', 'dc.creator', 'dc.contributor',
    'dc.publisher', 'dc.date', 'dc.type', 'dc.format',
    'dc.subject', 'dc.description', 'dc.language', 'dc.coverage',
    'item.id', 'item.callNumber', 'item.acquisitionDate', 'item.fundingSource', 'dc.rights'
]


def normalize_text(text):
    """Normalize text: lowercase, strip, remove accents."""
    # Remove accents using Unicode NFD normalization
    nfd = unicodedata.normalize('NFD', text.lower().strip())
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def detect_encoding(file_path):
    """Detect file encoding."""
    encodings = ['utf-8', 'windows-1252', 'latin-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not detect encoding for {file_path}")


def detect_delimiter(file_path, encoding):
    """Auto-detect delimiter."""
    with open(file_path, 'r', encoding=encoding) as f:
        sample = f.read(1024)
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter


def map_columns(csv_columns):
    """
    Map CSV columns to Dublin Core using fuzzy matching.

    Returns:
        (column_map, unmapped_columns)
    """
    column_map = {}
    unmapped = []

    for col in csv_columns:
        normalized = normalize_text(col)

        if normalized in COLUMN_PATTERNS:
            dc_col = COLUMN_PATTERNS[normalized]
            column_map[col] = dc_col
        else:
            unmapped.append(col)

    return column_map, unmapped


def convert_french_csv_to_dublin_core(input_file, output_file):
    """Convert French CSV to Dublin Core with auto-detection."""
    # Detect encoding and delimiter
    input_encoding = detect_encoding(input_file)
    delimiter = detect_delimiter(input_file, input_encoding)

    print(f"📖 Detected encoding: {input_encoding}")
    print(f"📖 Detected delimiter: {repr(delimiter)}")

    # Read input CSV
    with open(input_file, 'r', encoding=input_encoding) as infile:
        reader = csv.DictReader(infile, delimiter=delimiter)
        csv_columns = reader.fieldnames
        rows = list(reader)

    # Map columns
    column_map, unmapped = map_columns(csv_columns)

    # Print mapping results
    print("✅ Mapped columns:")
    for orig, dc in column_map.items():
        print(f"   {orig} → {dc}")

    if unmapped:
        print(f"⚠️  Unmapped columns (will be ignored): {', '.join(unmapped)}")

    # Check required columns
    if 'dc.title' not in column_map.values():
        raise ValueError("Required column 'titre' or 'title' not found in CSV")

    # Write Dublin Core CSV
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=DC_COLUMNS)
        writer.writeheader()

        for row in rows:
            dc_row = {col: '' for col in DC_COLUMNS}

            for orig_col, dc_col in column_map.items():
                if orig_col in row and row[orig_col]:
                    value = row[orig_col].strip()

                    # Add ISBN prefix if needed
                    if dc_col == 'dc.identifier' and value and not value.startswith('isbn:'):
                        value = f'isbn:{value}'

                    dc_row[dc_col] = value

            writer.writerow(dc_row)

    # Success message
    print(f"✅ Converted {input_file} → {output_file}")
    print(f"   Encoding: {input_encoding} → UTF-8")
    print(f"   Format: French CSV → Dublin Core")
    print(f"   Rows: {len(rows)}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python french_csv_to_dublin_core.py <input.csv> <output_dublin_core.csv>")
        print("\nExample:")
        print("  python french_csv_to_dublin_core.py mes_livres.csv catalog.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)

    try:
        convert_french_csv_to_dublin_core(input_file, output_file)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## 5. Vue Export Button (Frontend)

**File**: `src/bcd_web_vue/js/pages/CatalogPage.js` (modify existing file)

Add export button next to existing import button:

```javascript
const { ref } = Vue;

export default {
  name: 'CatalogPage',
  setup() {
    const exporting = ref(false);

    const handleExport = async () => {
      exporting.value = true;

      try {
        // Call export API endpoint
        const response = await fetch('/api/v1/catalog/export', {
          method: 'GET',
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Export failed');
        }

        // Get filename from Content-Disposition header
        const disposition = response.headers.get('Content-Disposition');
        const filename = disposition
          ? disposition.split('filename=')[1].replace(/"/g, '')
          : 'catalog_export.csv';

        // Trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

      } catch (error) {
        console.error('Export error:', error);
        alert(`Erreur lors de l'export: ${error.message}`);
      } finally {
        exporting.value = false;
      }
    };

    return {
      exporting,
      handleExport,
    };
  },
  template: `
    <div class="catalog-page">
      <div class="page-header">
        <h1>Catalogue</h1>
        <div class="header-actions">
          <button @click="handleExport" :disabled="exporting" class="btn btn-secondary">
            {{ exporting ? 'Export en cours...' : 'Exporter CSV' }}
          </button>
          <button @click="showImportDialog = true" class="btn btn-primary">
            Importer CSV
          </button>
        </div>
      </div>

      <!-- Rest of catalog page... -->
    </div>
  `,
};
```

---

## 6. Testing

### Service-Layer Integration Test

**File**: `tests/integration/test_export_service.py`

```python
"""Integration tests for export service."""
import pytest
import csv
from io import StringIO

from src.bcd_api.services.export_service import ExportService
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item


def test_export_catalog_basic(db_session):
    """Test basic catalog export."""
    # Arrange: Create sample record
    record = BiblographicRecord(
        title="Le Petit Prince",
        isbn="9782070612758",
        medium_type="Livre",
        authors='["Antoine de Saint-Exupéry"]',
    )
    db_session.add(record)
    db_session.commit()

    item = Item(
        bibliographic_record_id=record.id,
        item_id="787",
        call_number="800.000",
        loanable=True,
    )
    db_session.add(item)
    db_session.commit()

    # Act
    service = ExportService(db_session)
    csv_output = service.export_catalog_to_csv()

    # Assert
    assert "dc.title,dc.identifier" in csv_output
    assert "Le Petit Prince" in csv_output
    assert "isbn:9782070612758" in csv_output
    assert "Livre" in csv_output  # Medium type preserved
    assert "787" in csv_output  # Item ID


def test_round_trip_fidelity(db_session, import_service, export_service):
    """Test export → import → export produces identical CSV."""
    # Arrange: Export initial data
    csv1 = export_service.export_catalog_to_csv()

    # Act: Import then export again
    import_service.import_dublin_core_csv(StringIO(csv1))
    csv2 = export_service.export_catalog_to_csv()

    # Assert: CSVs should be identical
    assert csv1 == csv2


def test_french_characters_preserved(db_session):
    """Test French accented characters survive export."""
    # Arrange
    record = BiblographicRecord(
        title="L'Été à Paris",
        medium_type="Livre",
    )
    db_session.add(record)
    db_session.commit()

    # Act
    service = ExportService(db_session)
    csv_output = service.export_catalog_to_csv()

    # Assert: French characters intact
    assert "L'Été à Paris" in csv_output
    assert csv_output.encode('utf-8')  # Should not raise UnicodeEncodeError


def test_export_row_limit(db_session):
    """Test export rejects catalog exceeding 10,000 rows."""
    # Arrange: Create 10,001 items
    record = BiblographicRecord(title="Test")
    db_session.add(record)
    db_session.commit()

    for i in range(10001):
        item = Item(
            bibliographic_record_id=record.id,
            item_id=f"item_{i}",
        )
        db_session.add(item)
    db_session.commit()

    # Act & Assert
    service = ExportService(db_session)
    with pytest.raises(ValueError, match="exceeds 10,000 row limit"):
        service.export_catalog_to_csv()
```

---

## Key Implementation Notes

1. **No normalization**: Medium types stored/exported as plain text ("Livre" stays "Livre")
2. **UTF-8 BOM**: Add `\ufeff` prefix for Excel compatibility
3. **Streaming**: Use StringIO, not full file buffering
4. **Round-trip fidelity**: Export → Import → Export must produce identical CSV
5. **JSON arrays**: Parse with `json.loads()`, join with `|` for CSV
6. **RFC 4180**: Use `csv.QUOTE_MINIMAL` for proper escaping
7. **Performance**: Use `joinedload()` to avoid N+1 queries

**Next Steps**: Implement these examples, then run `/speckit.tasks` to generate actionable task list.
