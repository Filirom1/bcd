import asyncio
import csv
import io
import json
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from src.bcd_api.api.v1.catalog import import_catalog
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.services.catalog.import_dc import import_dublin_core_csv
from src.bcd_converters.catalog.bcdi_to_dublin_core import convert


def test_bcdi_memonotices_xml_imports_record_and_each_exemplar(db_session):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE MEMO_NOTICES SYSTEM "http://example.invalid/bcdi.dtd">
    <MEMO_NOTICES>
      <NOTICES>
        <NOTICE_GENERALE>
          <ISBN_N>978-2-07-036002-4</ISBN_N>
          <TITRE_N>Les Misérables</TITRE_N>
          <EDITEURS_N>Gallimard</EDITEURS_N>
          <AUTEURS_N>Hugo, Victor</AUTEURS_N>
          <DATE_PARUTION_N>1862</DATE_PARUTION_N>
          <SUPPORT_N>Livre</SUPPORT_N>
          <RESUME_N>Un roman historique.</RESUME_N>
          <DESCRIPTEURS_N>Histoire|Classique</DESCRIPTEURS_N>
          <EXEMPLAIRES>
            <CODE_EXEMPLAIRE_X>BCDI-001</CODE_EXEMPLAIRE_X>
            <COTE_E_X>R HUG</COTE_E_X>
            <DATE_ACHAT_E_X>15/09/2024</DATE_ACHAT_E_X>
          </EXEMPLAIRES>
          <EXEMPLAIRES>
            <CODE_EXEMPLAIRE_X>BCDI-002</CODE_EXEMPLAIRE_X>
            <COTE_E_X>R HUG</COTE_E_X>
          </EXEMPLAIRES>
        </NOTICE_GENERALE>
      </NOTICES>
    </MEMO_NOTICES>""".encode(
        "utf-8"
    )

    result = import_dublin_core_csv(db_session, convert(xml))

    assert result.records_created == 1
    assert result.items_created == 2
    record = db_session.query(BibliographicRecord).one()
    assert record.title == "Les Misérables"
    assert record.isbn == "isbn:9782070360024"
    assert record.publisher == "Gallimard"
    assert record.publication_year == 1862
    assert json.loads(record.authors) == ["Hugo, Victor"]
    assert json.loads(record.keywords) == ["Histoire", "Classique"]

    items = db_session.query(Item).order_by(Item.item_id).all()
    assert [item.item_id for item in items] == ["BCDI-001", "BCDI-002"]
    assert items[0].call_number == "R HUG"
    assert items[0].acquisition_date.isoformat() == "2024-09-15"


def test_bcdi_legacy_memonotices_fields_are_converted():
    xml = """<MEMO_NOTICES>
      <NOTICES>
        <TITRE_N>Le Petit Prince</TITRE_N>
        <SUPPORT_N_N>Livre</SUPPORT_N_N>
        <AUTEURS_N>Saint-Exupéry, Antoine</AUTEURS_N>
        <DOCUMENTS>
          <ISBN_D>9782070612758</ISBN_D>
          <EDITEURS_D>Gallimard</EDITEURS_D>
          <DATE_DE_PARUTION_D>1943</DATE_DE_PARUTION_D>
          <COTE_D>R SAI</COTE_D>
        </DOCUMENTS>
        <EXEMPLAIRES>
          <CODE_EXEMPLAIRE_X>BCDI-003</CODE_EXEMPLAIRE_X>
        </EXEMPLAIRES>
      </NOTICES>
    </MEMO_NOTICES>""".encode(
        "utf-8"
    )

    csv_content = convert(xml)

    assert "Le Petit Prince" in csv_content
    assert "9782070612758" in csv_content
    assert "Gallimard" in csv_content
    assert "BCDI-003" in csv_content


def test_bcdi_lists_encoding_language_and_structured_authorities_are_preserved(db_session):
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
    <MEMO_NOTICES xmlns="urn:bcdi"><NOTICES><NOTICE_GENERALE>
      <TITRE_N>La forêt / le jardin</TITRE_N>
      <AUTEURS_N>Martin, Léa/ Durand, Paul /</AUTEURS_N>
      <EDITEURS><EDITEUR_E>Éditions du Bois</EDITEUR_E></EDITEURS>
      <LANGUE_N>Fre / Eng</LANGUE_N>
      <DESCRIPTEURS_N>forêt / arbres /</DESCRIPTEURS_N>
      <MOTS_CLES_N>arbres|jardin</MOTS_CLES_N>
      <DATE_PARUTION_N>15/09/2020</DATE_PARUTION_N>
      <EXEMPLAIRES><CODE_EXEMPLAIRE_X>0007</CODE_EXEMPLAIRE_X></EXEMPLAIRES>
    </NOTICE_GENERALE></NOTICES></MEMO_NOTICES>""".encode(
        "iso-8859-1"
    )

    result = import_dublin_core_csv(db_session, convert(xml))

    assert not result.errors
    record = db_session.query(BibliographicRecord).one()
    assert record.title == "La forêt / le jardin"
    assert json.loads(record.authors) == ["Martin, Léa", "Durand, Paul"]
    assert json.loads(record.keywords) == ["forêt", "arbres", "jardin"]
    assert record.publisher == "Éditions du Bois"
    assert record.language == "Fre|Eng"
    assert record.publication_year == 2020
    assert db_session.query(Item).one().item_id == "0007"


def test_bcdi_part_notice_does_not_leak_metadata_into_general_notice():
    xml = b"""<MEMO_NOTICES><NOTICES><NOTICE_PARTIE>
      <TITRE_N>Article title</TITRE_N><AUTEURS_N>Article author</AUTEURS_N>
      <RESUME_N>Article summary</RESUME_N>
      <NOTICE_GENERALE><TITRE_N>Magazine issue</TITRE_N>
        <SUPPORT_N>Periodique</SUPPORT_N><ISSN_N>1234-567X</ISSN_N>
        <EXEMPLAIRES><CODE_EXEMPLAIRE_X>MAG-01</CODE_EXEMPLAIRE_X></EXEMPLAIRES>
      </NOTICE_GENERALE>
    </NOTICE_PARTIE></NOTICES></MEMO_NOTICES>"""

    (row,) = csv.DictReader(io.StringIO(convert(xml)))

    assert row["dc.title"] == "Magazine issue"
    assert row["dc.creator"] == ""
    assert row["dc.description"] == ""
    assert row["dc.identifier"] == "issn:1234-567X"
    assert row["dc.type"] == "Text;Periodical"


@pytest.mark.parametrize("exemplars", ["", "<EXEMPLAIRES/>"])
def test_bcdi_api_does_not_invent_item_ids_from_isbn(db_session, exemplars):
    xml = f"""<MEMO_NOTICES><NOTICES><NOTICE_GENERALE>
      <TITRE_N>A book</TITRE_N><ISBN_N>9782070612758</ISBN_N>
      <CODE_BARRE_N>9782070612758</CODE_BARRE_N>{exemplars}
    </NOTICE_GENERALE></NOTICES></MEMO_NOTICES>""".encode()

    result = asyncio.run(
        import_catalog(
            file=UploadFile(filename="catalog.xml", file=io.BytesIO(xml)),
            format="bcdi",
            db=db_session,
        )
    )

    assert result["records_created"] == 1
    assert result["items_created"] == 0
    assert result["errors"]
    assert db_session.query(Item).count() == 0


@pytest.mark.parametrize(
    "filename, title",
    [
        ("bcdi_sample.csv", "Alice au pays des merveilles"),
        ("bcdi_export_sample.csv", "Le Petit Prince"),
    ],
)
def test_bcdi_csv_variants_are_converted(filename, title):
    content = (Path(__file__).parents[2] / "data" / "sample_imports" / filename).read_bytes()

    rows = list(csv.DictReader(io.StringIO(convert(content))))

    assert rows[0]["dc.title"] == title
    assert rows[0]["dc.creator"]
    assert rows[0]["dc.publisher"]


def test_bcdi_csv_windows_encoding_and_item_fields_are_imported(db_session):
    content = (
        "Titre;Auteur;ISBN;Editeur;Inventaire;Cote;Date achat\n"
        "École;Léa / Paul;9782070612758;Éditions;00042;R ECO;15/09/2024\n"
    ).encode("cp1252")

    result = asyncio.run(
        import_catalog(
            file=UploadFile(filename="catalog.csv", file=io.BytesIO(content)),
            format="bcdi",
            db=db_session,
        )
    )

    assert result["items_created"] == 1
    assert result["errors"] == []
    item = db_session.query(Item).one()
    assert item.item_id == "00042"
    assert item.acquisition_date.isoformat() == "2024-09-15"


@pytest.mark.parametrize(
    "content",
    [
        b"<MEMO_NOTICES>",
        b"<MEMO_AUTEURS/>",
        b"<MEMO_NOTICES/>",
        b"unexpected,columns\nfoo,bar",
    ],
)
def test_bcdi_api_invalid_formats_return_client_error(db_session, content):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            import_catalog(
                file=UploadFile(filename="catalog.xml", file=io.BytesIO(content)),
                format="bcdi",
                db=db_session,
            )
        )

    assert exc.value.status_code == 400
    assert db_session.query(BibliographicRecord).count() == 0


def test_bcdi_periodical_issues_with_same_issn_are_not_merged_on_import_or_reimport(db_session):
    xml = b"""<MEMO_NOTICES>
    <NOTICES><NOTICE_GENERALE><TITRE_N>Magazine 001</TITRE_N>
      <ISSN_N>1234-567X</ISSN_N><SUPPORT_N>Periodique</SUPPORT_N>
      <EXEMPLAIRES><CODE_EXEMPLAIRE_X>M001</CODE_EXEMPLAIRE_X></EXEMPLAIRES>
    </NOTICE_GENERALE></NOTICES>
    <NOTICES><NOTICE_GENERALE><TITRE_N>Magazine 002</TITRE_N>
      <ISSN_N>1234-567X</ISSN_N><SUPPORT_N>Periodique</SUPPORT_N>
      <EXEMPLAIRES><CODE_EXEMPLAIRE_X>M002</CODE_EXEMPLAIRE_X></EXEMPLAIRES>
    </NOTICE_GENERALE></NOTICES></MEMO_NOTICES>"""

    result = import_dublin_core_csv(db_session, convert(xml), require_item_id=True)

    assert result.records_created == 2
    items = db_session.query(Item).order_by(Item.item_id).all()
    assert [item.bibliographic_record.title for item in items] == ["Magazine 001", "Magazine 002"]
    result = import_dublin_core_csv(db_session, convert(xml), require_item_id=True)
    assert result.records_created == 0
    assert result.items_created == 0
    assert result.records_skipped == 2


def test_bcdi_structured_authorities_and_legacy_document_title_are_used():
    xml = b"""<MEMO_NOTICES><NOTICES>
      <AUTEURS><AUTEUR_A>Author One</AUTEUR_A></AUTEURS>
      <AUTEURS><AUTEUR_A>Author Two</AUTEUR_A></AUTEURS>
      <DOCUMENTS><DOCUMENT_D>Legacy title</DOCUMENT_D>
        <EDITEURS><EDITEUR_E>Publisher</EDITEUR_E></EDITEURS>
        <COLLECTIONS><COLLECTION_C>Series</COLLECTION_C></COLLECTIONS>
      </DOCUMENTS>
    </NOTICES></MEMO_NOTICES>"""

    (row,) = csv.DictReader(io.StringIO(convert(xml)))

    assert row["dc.title"] == "Legacy title"
    assert row["dc.creator"] == "Author One|Author Two"
    assert row["dc.publisher"] == "Publisher"
    assert row["dc.source"] == "Series"


def test_bcdi_invalid_acquisition_date_is_not_silently_discarded():
    xml = b"""<MEMO_NOTICES><NOTICES><TITRE_N>Book</TITRE_N>
      <EXEMPLAIRES><DATE_ACHAT_E_X>31/02/2024</DATE_ACHAT_E_X></EXEMPLAIRES>
    </NOTICES></MEMO_NOTICES>"""
    with pytest.raises(ValueError, match="acquisition date"):
        convert(xml)


def test_bcdi_long_descriptions_do_not_break_csv_delimiter_detection(db_session):
    description = "A detailed summary with commas, semicolons; and words. " * 40
    xml = f"""<MEMO_NOTICES><NOTICES><NOTICE_GENERALE>
      <TITRE_N>Long summary</TITRE_N><RESUME_N>{description}</RESUME_N>
      <EXEMPLAIRES><CODE_EXEMPLAIRE_X>LONG-01</CODE_EXEMPLAIRE_X></EXEMPLAIRES>
    </NOTICE_GENERALE></NOTICES></MEMO_NOTICES>""".encode()

    result = asyncio.run(
        import_catalog(
            file=UploadFile(filename="catalog.xml", file=io.BytesIO(xml)),
            format="bcdi",
            db=db_session,
        )
    )

    assert result["records_created"] == 1
    assert result["items_created"] == 1
    assert result["errors"] == []
    assert db_session.query(BibliographicRecord).one().description == description.strip()
