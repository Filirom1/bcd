import csv
import io

import pytest

from bcd_converters import get_catalog_converter, list_catalog_converters
from bcd_converters.bibliopuce_to_dublin_core import convert, normalize_isbn, parse_acquisition_date


def test_normalize_isbn_and_issn():
    assert normalize_isbn("978-2-1234-5678-9") == "isbn:9782123456789"
    assert normalize_isbn("ISBN: 978 2 1234") == "isbn:97821234"
    assert normalize_isbn("1234-567X") == "issn:1234-567X"
    assert normalize_isbn("") == ""


def test_parse_acquisition_date():
    assert parse_acquisition_date("12/03/2025") == "2025-03-12"
    assert parse_acquisition_date("2025-03-12") == "2025-03-12"
    assert parse_acquisition_date("not a date") == ""
    assert parse_acquisition_date(" ") == ""


def test_bibliopuce_conversion_maps_periodical_and_skips_empty_title():
    source = ";".join(
        [
            "Inventaire",
            "Cote",
            "Rubrique",
            "Genre",
            "Titre",
            "SousTitre",
            "ISBN",
            "Auteur",
            "Illustrateur",
            "Annee",
            "Editeur",
            "Collection",
            "Numero",
            "Support",
            "Mots-clefs",
            "Niveau",
            "Description",
            "Taille",
            "Date achat",
            "Financement",
            "Empruntable",
        ]
    )
    row = ";".join(
        [
            "B1",
            "A-1",
            "Romans",
            "",
            "J'aime lire",
            "",
            "1234-567X",
            "Auteur",
            "",
            "2025",
            "Ed",
            "",
            "4",
            "Magazine",
            "aventure",
            "CE2",
            "",
            "",
            "12/03/2025",
            "Mairie",
            "Oui",
        ]
    )
    empty = ";".join(
        ["B2", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    )
    rows = list(
        csv.DictReader(io.StringIO(convert((source + "\n" + row + "\n" + empty).encode("utf-8"))))
    )
    assert len(rows) == 1
    assert rows[0]["dc.type"] == "Text;Periodical"
    assert rows[0]["dc.rights"] == "Loanable"
    assert rows[0]["item.acquisitionDate"] == "2025-03-12"
    assert rows[0]["dc.subject"] == "Romans|aventure"


@pytest.mark.parametrize("encoding,delimiter", [("utf-8-sig", ","), ("cp1252", ";")])
def test_biblioboost_conversion_preserves_metadata_and_inventory(encoding, delimiter):
    source = io.StringIO()
    writer = csv.writer(source, delimiter=delimiter)
    writer.writerow(
        [
            "Id_ecole",
            "Nº d'inventaire",
            "Titre",
            "ISBN/ISSN",
            "Nº de périodique",
            "Cote",
            "Fonds",
            "Auteur",
            "Illustrateur",
            "Editeur",
            "Collection",
            "Genre",
            "Niveau",
            "Support",
            "Matière",
            "Informations diverses",
            "Année",
            "Mots-clefs ou résumé",
        ]
    )
    writer.writerow(
        [
            "42",
            "0007",
            "La forêt",
            "978-2-07-061275-8",
            "",
            "A FOR",
            "Fonds école",
            "Martin, Léa",
            "Durand, Paul",
            "Éditions du Bois",
            "Nature",
            "Album",
            "Cycle 2",
            "Livre",
            "Lecture",
            "Entré le 22/08/2017. Don.\nTrès bon état.",
            "2009",
            "Une forêt, des arbres.\nUn récit.",
        ]
    )

    converter = get_catalog_converter("biblioboost")
    (row,) = csv.DictReader(io.StringIO(converter.convert(source.getvalue().encode(encoding))))

    assert "biblioboost" in {entry["name"] for entry in list_catalog_converters()}
    assert row["item.id"] == "0007"
    assert row["item.callNumber"] == "A FOR"
    assert row["item.acquisitionDate"] == "2017-08-22"
    assert row["dc.identifier"] == "isbn:9782070612758"
    assert row["dc.title"] == "La forêt"
    assert row["dc.creator"] == "Martin, Léa"
    assert row["dc.contributor"] == "Durand, Paul"
    assert row["dc.publisher"] == "Éditions du Bois"
    assert row["dc.source"] == "Nature"
    assert row["dc.date"] == "2009"
    assert row["dc.type"] == "Livre"
    assert row["dc.subject"] == "Album|Lecture"
    assert row["dc.coverage"] == "Cycle 2"
    assert row["dc.description"] == (
        "Une forêt, des arbres.\nUn récit.\n"
        "Entré le 22/08/2017. Don.\nTrès bon état.\nFonds : Fonds école"
    )
    assert row["item.fundingSource"] == ""


@pytest.mark.parametrize(
    "source",
    [
        "Titre,ISBN\nLivre,9782070612758\n",
        "Titre,Nº d'inventaire,ISBN/ISSN\nLivre,1\n",
        "Titre,Nº d'inventaire,ISBN/ISSN\nLivre,1,,extra\n",
        "Titre,Nº d'inventaire,ISBN/ISSN\n,1,\n",
        "Titre,Nº d'inventaire,ISBN/ISSN\nLivre,,9782070612758\n",
        "Titre,Nº d'inventaire,ISBN/ISSN,Informations diverses\nLivre,1,,Entré le 31/02/2020.\n",
    ],
)
def test_biblioboost_invalid_input_is_reported(source):
    with pytest.raises(ValueError):
        get_catalog_converter("biblioboost").convert(source.encode())
