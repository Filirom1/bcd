"""Import Service

Shared constants and utilities for import operations.
"""

from typing import Optional
import re

_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dX]$", re.IGNORECASE)


# CSV Column Names (BCD export format)
class CSVColumns:
    """Column names for BCD CSV export format."""
    INVENTAIRE = "Inventaire"
    COTE = "Cote"
    RUBRIQUE = "Rubrique"
    GENRE = "Genre"
    TITRE = "Titre"
    SOUS_TITRE = "SousTitre"
    ISBN = "ISBN"
    AUTEUR = "Auteur"
    ILLUSTRATEUR = "Illustrateur"
    ANNEE = "Annee"
    EDITEUR = "Editeur"
    COLLECTION = "Collection"
    NUMERO = "Numero"
    SUPPORT = "Support"
    MOTS_CLEFS = "Mots-clefs"
    NIVEAU = "Niveau"
    DESCRIPTION = "Description"
    TAILLE = "Taille"
    DATE_ACHAT = "Date achat"
    FINANCEMENT = "Financement"
    EMPRUNTABLE = "Empruntable"


# Dublin Core CSV Column Names (standard format)
class DublinCoreColumns:
    """Dublin Core metadata element set (15 core elements)."""
    # Required
    TITLE = "dc.title"
    IDENTIFIER = "dc.identifier"  # ISBN or item ID

    # Recommended
    CREATOR = "dc.creator"  # Authors (pipe-separated)
    SUBJECT = "dc.subject"  # Keywords (pipe-separated)
    DESCRIPTION = "dc.description"
    PUBLISHER = "dc.publisher"
    CONTRIBUTOR = "dc.contributor"  # Illustrators (pipe-separated)
    DATE = "dc.date"  # Publication year (YYYY)
    TYPE = "dc.type"  # Medium type
    FORMAT = "dc.format"  # Physical format (e.g., "300 pages")
    LANGUAGE = "dc.language"  # ISO 639 code

    # Optional
    SOURCE = "dc.source"  # Collection/Series
    RELATION = "dc.relation"  # Series number
    COVERAGE = "dc.coverage"  # Target audience/level
    RIGHTS = "dc.rights"  # Loanable status

    # Extensions (non-standard but useful)
    ITEM_ID = "item.id"  # Physical item inventory number
    CALL_NUMBER = "item.callNumber"
    ACQUISITION_DATE = "item.acquisitionDate"
    FUNDING_SOURCE = "item.fundingSource"


class ImportResult:
    """Results from an import operation."""

    def __init__(self):
        self.records_created = 0
        self.items_created = 0
        self.records_skipped = 0
        self.items_skipped = 0
        self.errors = []

    def add_error(self, row_num: int, error: str):
        """Add an error to the results."""
        self.errors.append({"row": row_num, "error": error})

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "records_created": self.records_created,
            "items_created": self.items_created,
            "records_skipped": self.records_skipped,
            "items_skipped": self.items_skipped,
            "errors": self.errors,
            "total_rows": self.records_created + self.records_skipped,
        }


def _normalize_isbn(isbn: str) -> Optional[str]:
    """
    Normalize an ISBN or ISSN, returning it with the appropriate prefix.

    Returns:
        - ``isbn:NNNN`` for ISBN-10 / ISBN-13
        - ``issn:NNNN-NNNX`` for ISSN (with hyphen preserved)
        - ``None`` for invalid / empty input

    Examples:
        "978-2-07-061275-8"  → "isbn:9782070612758"
        "1163-7706"          → "issn:1163-7706"
        "issn:1163-7706"     → "issn:1163-7706"
        "isbn:9782070612758" → "isbn:9782070612758"
        "11637706"           → None  (8 digits without hyphen: not valid ISSN or ISBN)
    """
    if not isbn or isbn.strip() == "":
        return None

    normalized = isbn.strip()

    # Explicit issn: prefix
    if normalized.lower().startswith("issn:"):
        bare = normalized[5:]
        if _ISSN_RE.match(bare):
            return f"issn:{bare.upper()}"
        return None

    # Bare ISSN format NNNN-NNNX (check BEFORE stripping hyphens)
    if _ISSN_RE.match(normalized):
        return f"issn:{normalized.upper()}"

    # ISBN path: strip isbn: prefix if present, then strip hyphens/spaces
    if normalized.lower().startswith("isbn:"):
        normalized = normalized[5:]
    normalized = normalized.replace("-", "").replace(" ", "").strip()

    if len(normalized) in [10, 13]:
        return f"isbn:{normalized}"

    return None
