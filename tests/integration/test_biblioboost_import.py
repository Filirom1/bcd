import asyncio
import io
import json

import pytest
from fastapi import HTTPException, UploadFile

from src.bcd_api.api.v1.catalog import import_catalog, list_importers
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item


def test_biblioboost_api_imports_copies_and_distinct_periodical_issues(db_session):
    content = (
        "Titre,Nº d'inventaire,ISBN/ISSN,Nº de périodique,Support,Cote,Genre,Matière,"
        "Informations diverses,Mots-clefs ou résumé\n"
        "La forêt,0007,9782070612758,,Livre,A FOR,Album,Lecture,Entré le 22/08/2017.,Résumé\n"
        "La forêt,0008,9782070612758,,Livre,A FOR,Album,Lecture,,Résumé\n"
        "Revue nature,0009,1234-567X,12,Périodique,P NAT,,,,\n"
        "Revue nature,0010,1234-567X,13,Périodique,P NAT,,,,\n"
        "Sans ISBN,0011,,,Livre,,,,,\n"
    ).encode("utf-8")

    assert "biblioboost" in {entry["name"] for entry in list_importers()["importers"]}
    result = asyncio.run(
        import_catalog(
            file=UploadFile(filename="documents.csv", file=io.BytesIO(content)),
            format="biblioboost",
            db=db_session,
        )
    )

    assert result["errors"] == []
    assert result["records_created"] == 4
    assert result["items_created"] == 5
    book = db_session.query(BibliographicRecord).filter_by(title="La forêt").one()
    assert json.loads(book.keywords) == ["Album", "Lecture"]
    assert book.total_items == 2
    items = db_session.query(Item).order_by(Item.item_id).all()
    assert [item.item_id for item in items] == ["0007", "0008", "0009", "0010", "0011"]
    assert items[0].call_number == "A FOR"
    assert items[0].acquisition_date.isoformat() == "2017-08-22"
    assert items[2].bibliographic_record_id != items[3].bibliographic_record_id
    assert items[2].bibliographic_record.series_number == "12"
    assert items[2].bibliographic_record.medium_type == "Périodique"

    repeated = asyncio.run(
        import_catalog(
            file=UploadFile(filename="documents.csv", file=io.BytesIO(content)),
            format="biblioboost",
            db=db_session,
        )
    )
    assert repeated["errors"] == []
    assert repeated["records_created"] == repeated["items_created"] == 0
    assert repeated["items_skipped"] == 5


def test_biblioboost_api_rejects_missing_inventory_without_importing(db_session):
    content = "Titre,Nº d'inventaire,ISBN/ISSN\nLivre,,9782070612758\n".encode()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            import_catalog(
                file=UploadFile(filename="documents.csv", file=io.BytesIO(content)),
                format="biblioboost",
                db=db_session,
            )
        )

    assert exc.value.status_code == 400
    assert db_session.query(BibliographicRecord).count() == 0
    assert db_session.query(Item).count() == 0
