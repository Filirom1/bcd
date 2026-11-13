"""Convert Biblioboost document CSV exports to Dublin Core format.

Accepts comma/semicolon-separated UTF-8 or Windows-1252 CSV. Inventory numbers
remain strings. Genre and subject become keywords; summaries, notes and fonds
are preserved in the description. The entry date is extracted from notes.
"""

import csv
import io
import re
from datetime import datetime

from .bibliopuce_to_dublin_core import DC_COLUMNS, normalize_isbn

INVENTORY_COLUMN = "Nº d'inventaire"
ISSUE_COLUMN = "Nº de périodique"
_ENTRY_DATE_RE = re.compile(r"\bEntré le (\d{2}/\d{2}/\d{4})", re.IGNORECASE)


def _map_row(row: dict[str, str]) -> dict[str, str]:
    identifier = normalize_isbn(row.get("ISBN/ISSN", ""))
    support = row.get("Support", "")
    periodical = support.lower() in {"périodique", "periodique"} or identifier.startswith("issn:")
    issue = row.get(ISSUE_COLUMN, "")
    title = row["Titre"]
    # The importer groups serial issues by ISSN + title, not by series number.
    if periodical and issue:
        title = f"{title} - n° {issue}"

    notes = row.get("Informations diverses", "")
    acquisition_date = ""
    if match := _ENTRY_DATE_RE.search(notes):
        try:
            acquisition_date = datetime.strptime(match[1], "%d/%m/%Y").date().isoformat()
        except ValueError as exc:
            raise ValueError(f"Invalid Biblioboost entry date: {match[1]!r}.") from exc

    description = [row.get("Mots-clefs ou résumé", ""), notes]
    if fonds := row.get("Fonds", ""):
        description.append(f"Fonds : {fonds}")

    return {
        "dc.identifier": identifier,
        "dc.title": title,
        "dc.creator": row.get("Auteur", ""),
        "dc.contributor": row.get("Illustrateur", ""),
        "dc.publisher": row.get("Editeur", ""),
        "dc.date": row.get("Année", ""),
        "dc.type": "Text;Periodical" if periodical else support,
        "dc.subject": "|".join(
            dict.fromkeys(value for key in ("Genre", "Matière") if (value := row.get(key, "")))
        ),
        "dc.description": "\n".join(part for part in description if part),
        "dc.source": row.get("Collection", ""),
        "dc.relation": issue,
        "dc.coverage": row.get("Niveau", ""),
        "item.id": row[INVENTORY_COLUMN],
        "item.callNumber": row.get("Cote", ""),
        "item.acquisitionDate": acquisition_date,
    }


def convert(content: bytes) -> str:
    """Convert a Biblioboost export, rejecting malformed rows before import."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise ValueError("Invalid Biblioboost encoding; use UTF-8 or Windows-1252.") from exc

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=DC_COLUMNS)
    writer.writeheader()
    try:
        delimiter = csv.Sniffer().sniff(text.partition("\n")[0], delimiters=",;").delimiter
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter, strict=True)
        headers = [header.strip() for header in reader.fieldnames or []]
        required = {"Titre", INVENTORY_COLUMN, "ISBN/ISSN"}
        if not required.issubset(headers):
            raise ValueError(
                "Biblioboost CSV requires Titre, Nº d'inventaire and ISBN/ISSN columns."
            )
        reader.fieldnames = headers
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Invalid Biblioboost column count at line {reader.line_num}.")
            cleaned = {key: value.strip() for key, value in row.items()}
            if not cleaned["Titre"] or not cleaned[INVENTORY_COLUMN]:
                raise ValueError(
                    f"Missing Biblioboost title or inventory at line {reader.line_num}."
                )
            try:
                writer.writerow(_map_row(cleaned))
            except ValueError as exc:
                raise ValueError(f"Biblioboost line {reader.line_num}: {exc}") from exc
    except csv.Error as exc:
        raise ValueError(f"Invalid Biblioboost CSV: {exc}") from exc
    return output.getvalue()
