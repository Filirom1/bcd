#!/usr/bin/env python3
"""Convert BiblioPuce library system CSV export to Dublin Core format.

BiblioPuce is a French school library management software. This script converts
BiblioPuce "notices-et-exemplaires" exports to Dublin Core CSV format for import
into BCD.

Usage:
    python -m bcd_converters.bibliopuce_to_dublin_core input.csv output.csv

Example:
    python -m bcd_converters.bibliopuce_to_dublin_core 2025-10-17-notices-et-exemplaires.csv catalog_dublin_core.csv

Input Format (BiblioPuce):
    - Columns: Inventaire, Cote, Rubrique, Genre, Titre, SousTitre, ISBN, Auteur,
               Illustrateur, Annee, Editeur, Collection, Numero, Support, Mots-clefs,
               Niveau, Description, Taille, Date achat, Financement, Empruntable
    - Encoding: Windows-1252 (French Windows default)
    - Delimiter: Semicolon

Output Format (Dublin Core):
    - Columns: dc.identifier, dc.title, dc.creator, dc.contributor, dc.publisher,
               dc.date, dc.type, dc.format, dc.subject, dc.description, dc.source,
               dc.relation, dc.coverage, dc.rights, item.id, item.callNumber,
               item.acquisitionDate, item.fundingSource
    - Encoding: UTF-8 with BOM (for Excel compatibility)
    - Delimiter: Comma

Column Mapping:
    - Inventaire       → item.id
    - Cote             → item.callNumber
    - Titre            → dc.title
    - ISBN             → dc.identifier (with "isbn:" prefix)
    - Auteur           → dc.creator
    - Illustrateur     → dc.contributor
    - Annee            → dc.date
    - Editeur          → dc.publisher
    - Collection       → dc.source
    - Numero           → dc.relation
    - Support          → dc.type
    - Rubrique +
      Mots-clefs       → dc.subject (pipe-separated)
    - Niveau           → dc.coverage
    - Description      → dc.description
    - Taille           → dc.format
    - Date achat       → item.acquisitionDate (ISO YYYY-MM-DD)
    - Financement      → item.fundingSource
    - Empruntable      → dc.rights ("Oui" → "Loanable")
"""

import argparse
import csv
import io
import re
import sys

DC_COLUMNS = [
    'dc.identifier',
    'dc.title',
    'dc.creator',
    'dc.contributor',
    'dc.publisher',
    'dc.date',
    'dc.type',
    'dc.format',
    'dc.subject',
    'dc.description',
    'dc.source',
    'dc.relation',
    'dc.coverage',
    'dc.rights',
    'item.id',
    'item.callNumber',
    'item.acquisitionDate',
    'item.fundingSource',
]


def normalize_isbn(isbn: str) -> str:
    """Add 'isbn:' or 'issn:' prefix to ISBN/ISSN, strip formatting characters."""
    raw = isbn.strip()
    if not raw:
        return ''
    # Already prefixed — return as-is (normalizing ISSN uppercase)
    if raw.lower().startswith('issn:'):
        return f'issn:{raw[5:].upper()}'
    if raw.lower().startswith('isbn:'):
        stripped = raw[5:].replace('-', '').replace(' ', '')
        return f'isbn:{stripped}' if stripped else ''
    # Bare ISSN: NNNN-NNNX (check before stripping hyphens)
    if re.match(r'^\d{4}-\d{3}[\dX]$', raw, re.IGNORECASE):
        return f'issn:{raw.upper()}'
    stripped = raw.replace('-', '').replace(' ', '')
    return f'isbn:{stripped}' if stripped else ''


KNOWN_PERIODICALS: frozenset = frozenset({
    "j'aime lire", "j'aime lire max", "je bouquine",
    "wakou", "okapi", "astrapi", "phosphore", "youpi",
    "les belles histoires", "popi", "pomme d'api",
    "picoti", "toupie", "dada", "arkéo junior",
    "virgule", "vocable", "geo ado", "images doc",
    "science et vie junior", "science et vie découvertes",
})

_ISSN_LIKE_RE = re.compile(r'^\d{4}-\d{3}[\dXx]$')


def is_periodical(row: dict) -> bool:
    """Return True if the BiblioPuce row represents a magazine/periodical."""
    collection = row.get('Collection', '').strip().lower()
    titre = row.get('Titre', '').strip().lower()
    if any(p in collection or p in titre for p in KNOWN_PERIODICALS):
        return True
    isbn_field = row.get('ISBN', '').strip()
    return bool(_ISSN_LIKE_RE.match(isbn_field))


def parse_acquisition_date(date_str: str) -> str:
    """Parse BiblioPuce date to ISO YYYY-MM-DD; return empty string on failure."""
    date_str = date_str.strip()
    if not date_str:
        return ''
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
    if m:
        return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
    return ''


def map_row(row: dict) -> dict:
    """Map one BiblioPuce row to a Dublin Core dict."""
    rubrique = row.get('Rubrique', '').strip()
    mots_clefs = row.get('Mots-clefs', '').strip()
    subjects = [s for s in [rubrique, mots_clefs] if s]

    empruntable = row.get('Empruntable', '').strip()
    rights = 'Loanable' if empruntable.lower() == 'oui' else ''

    return {
        'dc.identifier': normalize_isbn(row.get('ISBN', '')),
        'dc.title': row.get('Titre', '').strip(),
        'dc.creator': row.get('Auteur', '').strip(),
        'dc.contributor': row.get('Illustrateur', '').strip(),
        'dc.publisher': row.get('Editeur', '').strip(),
        'dc.date': row.get('Annee', '').strip(),
        'dc.type': 'Text;Periodical' if is_periodical(row) else row.get('Support', '').strip(),
        'dc.format': row.get('Taille', '').strip(),
        'dc.subject': '|'.join(subjects),
        'dc.description': row.get('Description', '').strip(),
        'dc.source': row.get('Collection', '').strip(),
        'dc.relation': row.get('Numero', '').strip(),
        'dc.coverage': row.get('Niveau', '').strip(),
        'dc.rights': rights,
        'item.id': row.get('Inventaire', '').strip(),
        'item.callNumber': row.get('Cote', '').strip(),
        'item.acquisitionDate': parse_acquisition_date(row.get('Date achat', '')),
        'item.fundingSource': row.get('Financement', '').strip(),
    }


def _parse_text(text: str) -> list:
    """Parse BiblioPuce CSV text and return list of Dublin Core dicts."""
    reader = csv.DictReader(io.StringIO(text), delimiter=';')
    dc_rows = []
    for row in reader:
        if not row.get('Titre', '').strip():
            continue
        dc_rows.append(map_row(row))
    return dc_rows


def convert(content: bytes) -> str:
    """Convert BiblioPuce CSV bytes to Dublin Core CSV string (in-memory, for API use).

    Args:
        content: Raw bytes of BiblioPuce CSV file (notices-et-exemplaires)

    Returns:
        Dublin Core CSV string (UTF-8)
    """
    text = None
    for encoding in ['windows-1252', 'utf-8', 'latin-1', 'iso-8859-1']:
        try:
            text = content.decode(encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if text is None:
        text = content.decode('utf-8', errors='replace')

    text = text.lstrip('\ufeff')

    dc_rows = _parse_text(text)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=DC_COLUMNS)
    writer.writeheader()
    writer.writerows(dc_rows)
    return output.getvalue()


def convert_file(input_file: str, output_file: str) -> bool:
    """Convert BiblioPuce CSV file to Dublin Core CSV file.

    Args:
        input_file: Path to BiblioPuce CSV file
        output_file: Path to output Dublin Core CSV file

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        with open(input_file, 'rb') as f:
            content = f.read()

        csv_content = convert(content)

        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(csv_content)

        dc_rows = list(csv.DictReader(io.StringIO(csv_content)))
        print('Conversion successful!')
        print(f'  Input:  {input_file}')
        print(f'  Output: {output_file} (UTF-8 with BOM)')
        print(f'  Records converted: {len(dc_rows)}')
        return True

    except Exception as e:
        print(f'Error during conversion: {e}', file=sys.stderr)
        return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Convert BiblioPuce CSV export to Dublin Core format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('input_file', help='Input BiblioPuce CSV file (notices-et-exemplaires)')
    parser.add_argument('output_file', help='Output Dublin Core CSV file')
    args = parser.parse_args()
    sys.exit(0 if convert_file(args.input_file, args.output_file) else 1)


if __name__ == '__main__':
    main()
