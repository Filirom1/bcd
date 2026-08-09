import csv
import io

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
    source = ";".join(["Inventaire", "Cote", "Rubrique", "Genre", "Titre", "SousTitre", "ISBN", "Auteur", "Illustrateur", "Annee", "Editeur", "Collection", "Numero", "Support", "Mots-clefs", "Niveau", "Description", "Taille", "Date achat", "Financement", "Empruntable"])
    row = ";".join(["B1", "A-1", "Romans", "", "J'aime lire", "", "1234-567X", "Auteur", "", "2025", "Ed", "", "4", "Magazine", "aventure", "CE2", "", "", "12/03/2025", "Mairie", "Oui"])
    empty = ";".join(["B2", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
    rows = list(csv.DictReader(io.StringIO(convert((source + "\n" + row + "\n" + empty).encode("utf-8")))))
    assert len(rows) == 1
    assert rows[0]["dc.type"] == "Text;Periodical"
    assert rows[0]["dc.rights"] == "Loanable"
    assert rows[0]["item.acquisitionDate"] == "2025-03-12"
    assert rows[0]["dc.subject"] == "Romans|aventure"
