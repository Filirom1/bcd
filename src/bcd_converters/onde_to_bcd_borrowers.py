#!/usr/bin/env python3
"""Convert ONDE (French national student database) CSV exports to BCD borrower format.

ONDE (Outil Numérique pour la Direction d'École) is the French national student
database used by elementary schools. This script converts ONDE CSV exports to the
BCD borrower CSV format for import.

Usage:
    python -m bcd_converters.onde_to_bcd_borrowers input.csv output.csv
    python -m bcd_converters.onde_to_bcd_borrowers input.csv output.csv --delimiter=";"

ONDE Format:
    - Delimiter: Semicolon (;) by default
    - Encoding: UTF-8
    - Columns: French column names (Nom, Prénom, INE, Identifiant Classe, etc.)

BCD Borrower Format:
    - Delimiter: Comma (,)
    - Encoding: UTF-8 with BOM (Excel compatibility)
    - Columns: borrower_id, first_name, last_name, role, class, active, email, phone, notes

Column Mapping:
    - Nom / Nom de l'élève → last_name
    - Prénom / Prénom de l'élève → first_name
    - INE / Identifiant National Élève → borrower_id (with fallback to STUDENT-{number})
    - Identifiant Classe / Classe → class (extracts grade level from "CP-A" → "CP")
    - Role: Always set to "student" for ONDE records

Features:
    - Auto-detects column name variations (Nom vs. Nom de l'élève)
    - Handles missing INE with auto-generated fallback IDs
    - Extracts grade level from class names (CP-A → CP)
    - Detects and warns about duplicate INE values
    - UTF-8 input/output with BOM for Excel compatibility
    - Configurable delimiter (--delimiter flag)

Author: BCD Development Team
Date: 2026-02-06
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


# Column name variations for flexible matching
COLUMN_VARIATIONS = {
    'last_name': ['Nom', 'Nom de l\'élève', 'NOM', 'nom'],
    'first_name': ['Prénom', 'Prénom de l\'élève', 'PRENOM', 'prenom', 'Prenom'],
    'borrower_id': ['INE', 'Identifiant National Élève', 'Identifiant National Eleve',
                     'ine', 'Numéro INE', 'Numero INE'],
    'class': ['Identifiant Classe', 'Classe', 'classe', 'CLASSE', 'Nom de la classe']
}

# BCD borrower CSV columns
BCD_COLUMNS = [
    'borrower_id', 'first_name', 'last_name', 'role', 'class',
    'active', 'email', 'phone', 'notes'
]


def normalize_column_name(name: str) -> str:
    """Normalize column name by removing extra whitespace and lowercasing."""
    return name.strip()


def find_column_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    """Map ONDE column names to BCD field names.

    Args:
        headers: List of column names from ONDE CSV

    Returns:
        Dictionary mapping BCD field names to ONDE column names
    """
    mapping = {}

    for bcd_field, variations in COLUMN_VARIATIONS.items():
        found = None
        for header in headers:
            normalized_header = normalize_column_name(header)
            if normalized_header in variations or header in variations:
                found = header
                break
        mapping[bcd_field] = found

    return mapping


def extract_grade_level(class_name: str) -> str:
    """Extract grade level from class name.

    Examples:
        - "CP-A" → "CP"
        - "CE1-B" → "CE1"
        - "CM2" → "CM2"
        - "CP A" → "CP"

    Args:
        class_name: Full class name with section

    Returns:
        Grade level without section
    """
    if not class_name:
        return ''

    # Remove section suffix (after dash or space)
    for separator in ['-', ' ']:
        if separator in class_name:
            return class_name.split(separator)[0].strip()

    return class_name.strip()


def generate_borrower_id(row_number: int) -> str:
    """Generate fallback borrower ID when INE is missing.

    Args:
        row_number: Row number in CSV (1-indexed)

    Returns:
        Generated borrower ID in format "STUDENT-{number}"
    """
    return f"STUDENT-{row_number:04d}"


def convert_onde_to_bcd(
    input_path: Path,
    output_path: Path,
    delimiter: str = ';',
    encoding: str = 'utf-8'
) -> None:
    """Convert ONDE CSV export to BCD borrower format.

    Args:
        input_path: Path to ONDE CSV file
        output_path: Path to output BCD CSV file
        delimiter: CSV delimiter for input file (default: semicolon)
        encoding: Input file encoding (default: utf-8)
    """
    # Track statistics
    total_rows = 0
    converted_rows = 0
    ine_fallback_count = 0
    duplicate_ines: Set[str] = set()
    seen_ines: Set[str] = set()

    # Read ONDE CSV
    with open(input_path, 'r', encoding=encoding, newline='') as f_in:
        reader = csv.DictReader(f_in, delimiter=delimiter)

        # Map ONDE columns to BCD fields
        column_mapping = find_column_mapping(reader.fieldnames or [])

        # Validate that we found required columns
        if not column_mapping.get('first_name'):
            print(f"ERROR: Could not find first name column. Expected one of: {COLUMN_VARIATIONS['first_name']}")
            print(f"   Found columns: {', '.join(reader.fieldnames or [])}")
            sys.exit(1)

        if not column_mapping.get('last_name'):
            print(f"ERROR: Could not find last name column. Expected one of: {COLUMN_VARIATIONS['last_name']}")
            print(f"   Found columns: {', '.join(reader.fieldnames or [])}")
            sys.exit(1)

        # Print detected column mapping
        print("\nDetected column mapping:")
        for bcd_field, onde_column in column_mapping.items():
            if onde_column:
                print(f"   {onde_column} -> {bcd_field}")
            else:
                print(f"   (not found) -> {bcd_field}")

        print()  # Blank line for readability

        # Convert rows
        bcd_rows = []
        for row_num, row in enumerate(reader, start=1):
            total_rows += 1

            # Extract and map fields
            first_name = row.get(column_mapping.get('first_name', ''), '').strip()
            last_name = row.get(column_mapping.get('last_name', ''), '').strip()
            ine = row.get(column_mapping.get('borrower_id', ''), '').strip()
            class_name = row.get(column_mapping.get('class', ''), '').strip()

            # Skip rows with missing required fields
            if not first_name or not last_name:
                print(f"WARNING: Row {row_num}: Missing first_name or last_name, skipping")
                continue

            # Use INE or generate fallback ID
            if ine:
                borrower_id = ine
                # Detect duplicate INE
                if ine in seen_ines:
                    duplicate_ines.add(ine)
                    print(f"WARNING: Row {row_num}: Duplicate INE '{ine}' detected, using first occurrence")
                    continue  # Skip duplicate
                seen_ines.add(ine)
            else:
                borrower_id = generate_borrower_id(row_num)
                ine_fallback_count += 1

            # Extract grade level from class name
            grade_level = extract_grade_level(class_name) if class_name else ''

            # Create BCD borrower record
            bcd_row = {
                'borrower_id': borrower_id,
                'first_name': first_name,
                'last_name': last_name,
                'role': 'student',  # All ONDE records are students
                'class': grade_level,
                'active': 'true',  # Default to active
                'email': '',  # ONDE typically doesn't include email
                'phone': '',  # ONDE typically doesn't include phone
                'notes': f'Imported from ONDE' if not ine else ''
            }

            bcd_rows.append(bcd_row)
            converted_rows += 1

        # Write BCD CSV with UTF-8 BOM for Excel compatibility
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=BCD_COLUMNS, delimiter=',')
            writer.writeheader()
            writer.writerows(bcd_rows)

    # Print summary
    print(f"Conversion complete!")
    print(f"   Input file:  {input_path}")
    print(f"   Output file: {output_path}")
    print(f"   Total rows processed: {total_rows}")
    print(f"   Rows converted: {converted_rows}")
    print(f"   Rows skipped: {total_rows - converted_rows}")

    if ine_fallback_count > 0:
        print(f"   INE fallback IDs generated: {ine_fallback_count}")

    if duplicate_ines:
        print(f"   Duplicate INEs detected: {len(duplicate_ines)}")
        print(f"      Duplicates: {', '.join(sorted(duplicate_ines))}")


def main():
    """Main entry point for ONDE to BCD borrower conversion script."""
    parser = argparse.ArgumentParser(
        description='Convert ONDE CSV export to BCD borrower format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert with default semicolon delimiter
  python -m bcd_converters.onde_to_bcd_borrowers students.csv borrowers.csv

  # Convert with custom delimiter
  python -m bcd_converters.onde_to_bcd_borrowers students.csv borrowers.csv --delimiter=","

  # Specify encoding (if not UTF-8)
  python -m bcd_converters.onde_to_bcd_borrowers students.csv borrowers.csv --encoding="latin-1"

Column Mapping:
  ONDE Format              -> BCD Borrower Format
  ─────────────────────────────────────────────────
  Nom / Nom de l'élève     -> last_name
  Prénom / Prénom de l'élève -> first_name
  INE                      -> borrower_id (with STUDENT-#### fallback)
  Identifiant Classe       -> class (grade level extracted: "CP-A" -> "CP")
  (auto-set)               -> role="student"

Notes:
  - All ONDE records are imported as role="student"
  - Missing INE values trigger auto-generated IDs (STUDENT-0001, STUDENT-0002, etc.)
  - Grade levels are extracted from class names (CP-A -> CP, CE1-B -> CE1)
  - Duplicate INE values are detected and skipped (first occurrence kept)
  - Output uses UTF-8 with BOM for Excel compatibility
"""
    )

    parser.add_argument('input', type=Path, help='Path to ONDE CSV file')
    parser.add_argument('output', type=Path, help='Path to output BCD borrower CSV file')
    parser.add_argument(
        '--delimiter',
        default=';',
        help='CSV delimiter for input file (default: semicolon ";")'
    )
    parser.add_argument(
        '--encoding',
        default='utf-8',
        help='Input file encoding (default: utf-8)'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    # Convert
    convert_onde_to_bcd(
        input_path=args.input,
        output_path=args.output,
        delimiter=args.delimiter,
        encoding=args.encoding
    )


if __name__ == '__main__':
    main()
