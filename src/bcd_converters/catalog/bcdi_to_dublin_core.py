"""Convert BCDI MémoNotices XML (before/since 2009) or tabular CSV to Dublin Core.

Only general notices are imported from nested part notices; article metadata
does not describe the physical document. BCDI lists use '/' as a separator.
Document barcodes and ISBNs are not exemplar inventory numbers.
"""

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

from .bibliopuce_to_dublin_core import DC_COLUMNS, normalize_isbn

CSV_ALIASES = {
    "TITRE": "TITRE_N",
    "AUTEUR": "AUTEURS_N",
    "AUTEURS": "AUTEURS_N",
    "ISBN": "ISBN_N",
    "ISSN": "ISSN_N",
    "EDITEUR": "EDITEURS_N",
    "EDITEURS": "EDITEURS_N",
    "DATE": "DATE_PARUTION_N",
    "ANNEE": "DATE_PARUTION_N",
    "SUPPORT": "SUPPORT_N",
    "LANGUE": "LANGUE_N",
    "DESCRIPTION": "RESUME_N",
    "RESUME": "RESUME_N",
    "DESCRIPTEUR": "DESCRIPTEURS_N",
    "MOTS-CLEFS": "MOTS_CLES_N",
    "COLLECTION": "COLLECTION_N",
    "NUMERO": "NO_COLLECTION_N",
    "NIVEAU": "NIVEAUX_N",
    "COTE": "COTE_E_X",
    "INVENTAIRE": "CODE_EXEMPLAIRE_X",
    "DATE ACHAT": "DATE_ACHAT_E_X",
}


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].upper()


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child) == name.upper()]


def _text(element: Optional[ET.Element]) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _value(nodes: list[ET.Element], *names: str) -> str:
    for node in nodes:
        for name in names:
            for child in _children(node, name):
                value = _text(child)
                if value:
                    return value
    return ""


def _structured_values(nodes: list[ET.Element], container_name: str, value_name: str) -> str:
    values = []
    for node in nodes:
        for container in _children(node, container_name):
            values.extend(
                value for child in _children(container, value_name) if (value := _text(child))
            )
    return "|".join(dict.fromkeys(values))


def _list_values(*values: str) -> str:
    return "|".join(
        dict.fromkeys(
            part.strip() for value in values for part in re.split(r"[/|]", value) if part.strip()
        )
    )


def _acquisition_date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Invalid BCDI acquisition date: {value!r}.")


def _publication_date(value: str) -> str:
    for date_format in ("%d/%m/%Y", "%d-%m-%Y", "%m/%Y", "%Y-%m-%d"):
        try:
            return str(datetime.strptime(value, date_format).year)
        except ValueError:
            continue
    return value


def _notice_rows(notice: ET.Element) -> list[dict[str, str]]:
    general_notices = [node for node in notice.iter() if _local_name(node) == "NOTICE_GENERALE"]
    # Before 2009, document-level fields lived under DOCUMENTS, directly in NOTICES.
    records = general_notices or [notice]
    rows = []

    for record in records:
        nodes = [record, *_children(record, "DOCUMENTS")]
        isbn = _value(nodes, "ISBN_N", "ISBN_D")
        issn = _value(nodes, "ISSN_N", "ISSN_D")
        identifier = normalize_isbn(isbn) if isbn else f"issn:{issn}" if issn else ""
        title = _value(nodes, "TITRE_N", "DOCUMENT_N", "DOCUMENT_D")

        authors = _list_values(
            _value(nodes, "AUTEURS_N") or _structured_values(nodes, "AUTEURS", "AUTEUR_A")
        )
        publishers = _list_values(
            _value(nodes, "EDITEURS_N", "EDITEURS_D")
            or _structured_values(nodes, "EDITEURS", "EDITEUR_E")
        )
        collections = _structured_values(nodes, "COLLECTIONS", "COLLECTION_C")
        collection = _value(nodes, "COLLECTION_N", "COLLECTION_D") or collections
        keywords = [
            _value(nodes, name)
            for name in ("DESCRIPTEURS_N", "MOTS_CLES_N", "NATURES_N", "GENRES_N")
        ]
        subjects = _list_values(*keywords)
        support = _value(nodes, "SUPPORT_N", "SUPPORT_N_N", "SUPPORT_D")
        if support.lower() in {"périodique", "periodique", "periodical"}:
            support = "Text;Periodical"
        exemplars = _children(record, "EXEMPLAIRES")
        if not exemplars:
            exemplars = [None]

        for exemplar in exemplars:
            exemplar_nodes = [exemplar] if exemplar is not None else []
            item_id = _value(exemplar_nodes, "CODE_EXEMPLAIRE_X")
            rows.append(
                {
                    "dc.identifier": identifier,
                    "dc.title": title,
                    "dc.creator": authors,
                    "dc.publisher": publishers,
                    "dc.date": _publication_date(
                        _value(nodes, "DATE_PARUTION_N", "DATE_DE_PARUTION_D", "DATE_EDITION_N_N")
                    ),
                    "dc.type": support,
                    "dc.format": _value(nodes, "COLLATION_N"),
                    "dc.language": _list_values(_value(nodes, "LANGUE_N")),
                    "dc.subject": subjects,
                    "dc.description": _value(nodes, "RESUME_N"),
                    "dc.source": collection,
                    "dc.relation": _value(nodes, "NO_COLLECTION_N", "NO_COLLECTION_D"),
                    "dc.coverage": _list_values(_value(nodes, "NIVEAUX_N")),
                    "dc.rights": "",
                    "item.id": item_id,
                    "item.callNumber": _value(exemplar_nodes, "COTE_E_X")
                    or _value(nodes, "COTE_N", "COTE_D"),
                    "item.acquisitionDate": _acquisition_date(
                        _value(exemplar_nodes, "DATE_ACHAT_E_X")
                    ),
                    "item.fundingSource": "",
                }
            )
    return rows


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise ValueError("Invalid BCDI CSV encoding; use UTF-8 or Windows-1252.") from exc
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=";,\t")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        headers = [header.strip().upper() for header in reader.fieldnames or []]
        if not {"TITRE", "TITRE_N", "DOCUMENT_N", "DOCUMENT_D"}.intersection(headers):
            raise ValueError("BCDI CSV requires a TITRE_N or Titre column.")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError(f"Too many columns in BCDI CSV at line {reader.line_num}.")
            notice = ET.Element("NOTICES")
            exemplar = ET.SubElement(notice, "EXEMPLAIRES")
            for header, value in row.items():
                name = header.strip().upper()
                name = CSV_ALIASES.get(name, name)
                parent = exemplar if name.endswith("_X") else notice
                ET.SubElement(parent, name).text = value or ""
            rows.extend(_notice_rows(notice))
        return rows
    except csv.Error as exc:
        raise ValueError(f"Invalid BCDI CSV: {exc}") from exc


def convert(content: bytes) -> str:
    """Convert XML/CSV bytes, respecting the XML declaration's encoding.

    Raises ValueError for invalid files. Use the DC importer's require_item_id
    option to report missing exemplar codes instead of inventing them from ISBNs.
    """
    if content.lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<") or content.startswith(
        (b"\xff\xfe", b"\xfe\xff")
    ):
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid BCDI XML: {exc}") from exc
        if _local_name(root) != "MEMO_NOTICES":
            raise ValueError("Le fichier XML n'est pas un export BCDI MémoNotices.")
        rows = [row for notice in _children(root, "NOTICES") for row in _notice_rows(notice)]
    else:
        rows = _csv_rows(content)
    if not rows:
        raise ValueError("No notices found in the BCDI export.")

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[*DC_COLUMNS, "dc.language"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
