"""CSV Format Transformation Service

Convert between different CSV formats (BCD custom -> Dublin Core standard).
"""

import csv
import logging
from io import StringIO

from .import_ import CSVColumns, DublinCoreColumns

logger = logging.getLogger(__name__)


def transform_bcd_to_dublin_core(bcd_csv_content: str) -> str:
    """
    Transform BCD custom CSV format to Dublin Core standard CSV.

    Mappings:
    - Titre -> dc.title
    - ISBN -> dc.identifier
    - Auteur -> dc.creator
    - Illustrateur -> dc.contributor
    - Mots-clefs -> dc.subject
    - Description -> dc.description
    - Editeur -> dc.publisher
    - Annee -> dc.date
    - Support -> dc.type
    - Taille -> dc.format
    - Collection -> dc.source
    - Numero -> dc.relation
    - Niveau -> dc.coverage
    - Empruntable -> dc.rights
    - Inventaire -> item.id
    - Cote -> item.callNumber
    - Date achat -> item.acquisitionDate
    - Financement -> item.fundingSource

    Args:
        bcd_csv_content: BCD CSV content (semicolon-separated)

    Returns:
        Dublin Core CSV content (comma-separated)
    """
    # Parse BCD CSV
    bcd_csv = StringIO(bcd_csv_content)
    bcd_reader = csv.DictReader(bcd_csv, delimiter=";")

    # Prepare Dublin Core CSV
    dc_fieldnames = [
        DublinCoreColumns.TITLE,
        DublinCoreColumns.IDENTIFIER,
        DublinCoreColumns.CREATOR,
        DublinCoreColumns.CONTRIBUTOR,
        DublinCoreColumns.SUBJECT,
        DublinCoreColumns.DESCRIPTION,
        DublinCoreColumns.PUBLISHER,
        DublinCoreColumns.DATE,
        DublinCoreColumns.TYPE,
        DublinCoreColumns.FORMAT,
        DublinCoreColumns.SOURCE,
        DublinCoreColumns.RELATION,
        DublinCoreColumns.COVERAGE,
        DublinCoreColumns.RIGHTS,
        DublinCoreColumns.ITEM_ID,
        DublinCoreColumns.CALL_NUMBER,
        DublinCoreColumns.ACQUISITION_DATE,
        DublinCoreColumns.FUNDING_SOURCE,
    ]

    dc_output = StringIO()
    dc_writer = csv.DictWriter(dc_output, fieldnames=dc_fieldnames)
    dc_writer.writeheader()

    rows_transformed = 0
    for row in bcd_reader:
        try:
            # Build subtitle if present
            title = (row.get(CSVColumns.TITRE) or "").strip()
            subtitle = (row.get(CSVColumns.SOUS_TITRE) or "").strip()
            if subtitle:
                title = f"{title}: {subtitle}"

            # Parse authors (could be "LastName (FirstName)" format)
            auteur = (row.get(CSVColumns.AUTEUR) or "").strip()
            if auteur and "(" in auteur and ")" in auteur:
                # Convert "LastName (FirstName)" to "LastName, FirstName"
                parts = auteur.split("(")
                last_name = parts[0].strip()
                first_name = parts[1].replace(")", "").strip()
                auteur = f"{last_name}, {first_name}"

            # Parse illustrators (same format)
            illustrateur = (row.get(CSVColumns.ILLUSTRATEUR) or "").strip()
            if illustrateur and "(" in illustrateur and ")" in illustrateur:
                parts = illustrateur.split("(")
                last_name = parts[0].strip()
                first_name = parts[1].replace(")", "").strip()
                illustrateur = f"{last_name}, {first_name}"

            # Parse keywords (comma-separated to pipe-separated)
            keywords = (row.get(CSVColumns.MOTS_CLEFS) or "").strip()
            if keywords:
                keywords = "|".join([kw.strip() for kw in keywords.split(",") if kw.strip()])

            # Parse page count from Taille (e.g., "173 p" -> "173 pages")
            taille = (row.get(CSVColumns.TAILLE) or "").strip()
            format_str = ""
            if taille:
                import re
                match = re.search(r"(\d+)\s*(?:p|pages|page)", taille.lower())
                if match:
                    format_str = f"{match.group(1)} pages"
                else:
                    format_str = taille

            # Map Empruntable (Oui/Non) to dc.rights
            empruntable = (row.get(CSVColumns.EMPRUNTABLE) or "").strip().lower()
            rights = "Loanable" if empruntable in ["oui", "yes", "1", "true", ""] else "Not loanable"

            # Map Support to Dublin Core type
            support = (row.get(CSVColumns.SUPPORT) or "").strip()
            dc_type = _map_support_to_dc_type(support)

            # Build Dublin Core row
            dc_row = {
                DublinCoreColumns.TITLE: title,
                DublinCoreColumns.IDENTIFIER: (row.get(CSVColumns.ISBN) or "").strip(),
                DublinCoreColumns.CREATOR: auteur,
                DublinCoreColumns.CONTRIBUTOR: illustrateur,
                DublinCoreColumns.SUBJECT: keywords,
                DublinCoreColumns.DESCRIPTION: (row.get(CSVColumns.DESCRIPTION) or "").strip(),
                DublinCoreColumns.PUBLISHER: (row.get(CSVColumns.EDITEUR) or "").strip(),
                DublinCoreColumns.DATE: (row.get(CSVColumns.ANNEE) or "").strip(),
                DublinCoreColumns.TYPE: dc_type,
                DublinCoreColumns.FORMAT: format_str,
                DublinCoreColumns.SOURCE: (row.get(CSVColumns.COLLECTION) or "").strip(),
                DublinCoreColumns.RELATION: (row.get(CSVColumns.NUMERO) or "").strip(),
                DublinCoreColumns.COVERAGE: (row.get(CSVColumns.NIVEAU) or "").strip(),
                DublinCoreColumns.RIGHTS: rights,
                DublinCoreColumns.ITEM_ID: (row.get(CSVColumns.INVENTAIRE) or "").strip(),
                DublinCoreColumns.CALL_NUMBER: (row.get(CSVColumns.COTE) or "").strip(),
                DublinCoreColumns.ACQUISITION_DATE: (row.get(CSVColumns.DATE_ACHAT) or "").strip(),
                DublinCoreColumns.FUNDING_SOURCE: (row.get(CSVColumns.FINANCEMENT) or "").strip(),
            }

            dc_writer.writerow(dc_row)
            rows_transformed += 1

        except Exception as e:
            logger.exception(f"Error transforming row: {e}")
            continue

    logger.info(f"Transformed {rows_transformed} rows from BCD to Dublin Core")
    return dc_output.getvalue()


def _map_support_to_dc_type(support: str) -> str:
    """
    Map BCD Support field to Dublin Core Type.

    Args:
        support: BCD support value (Livre, CD, DVD, Film, etc.)

    Returns:
        Dublin Core Type value
    """
    if not support:
        return "Text"

    support_lower = support.strip().lower()

    if "livre" in support_lower:
        return "Text"
    elif "cd" in support_lower:
        return "Sound"
    elif "dvd" in support_lower or "film" in support_lower:
        return "MovingImage"
    elif "périodique" in support_lower or "revue" in support_lower or "magazine" in support_lower:
        return "Text;Periodical"
    else:
        return "PhysicalObject"
