"""Integration coverage for importing the ONDE sample borrower export."""

from pathlib import Path

from src.bcd_api.models.borrower import Borrower
from src.bcd_api.services.borrower.import_ import import_borrowers_from_csv
from src.bcd_converters.borrower.onde_to_bcd_borrowers import convert


SAMPLE_PATH = Path("data/sample_imports/onde_official_sample.csv")


def test_import_official_onde_sample_assigns_reusable_ids_and_external_ids(db_session):
    """The complete ONDE fixture converts and imports through the real services."""
    csv_text = convert(SAMPLE_PATH.read_bytes())

    result = import_borrowers_from_csv(db_session, csv_text)

    assert result["total_rows"] == 5
    assert result["borrowers_created"] == 5
    assert result["borrowers_updated"] == 0
    assert result["failed_rows"] == 0

    imported = db_session.query(Borrower).order_by(Borrower.borrower_id).all()
    assert [borrower.borrower_id for borrower in imported] == ["1", "2", "3", "4", "5"]
    assert imported[0].external_id == "10000000001AA"
    assert imported[1].external_id == "10000000002BB"
    assert imported[1].last_name == "MARTIN-BERNARD"
    assert imported[2].external_id is None
    assert imported[2].last_name == "GARCIA"
    assert imported[0].class_.name == "CP A"
    assert imported[2].class_.name == "CE1 A"
