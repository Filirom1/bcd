from unittest.mock import MagicMock, patch
import pytest

from src.bcd_api.services.catalog.export import ExportService


def test_export_catalog_to_csv():
    # Mock database and query returns
    db = MagicMock()
    record = MagicMock(title="Book", isbn="9782211056465", authors='["Carmi"]', illustrators='[]', keywords='[]', publication_year=2024, medium_type="Livre", page_count=128, collection=None, series_number=None, level=None, description=None, language="fr")
    item = MagicMock(item_id="123", call_number="800.000", acquisition_date=None, funding_source=None, loanable=True)
    record.items = [item]
    db.query.return_value.options.return_value.all.return_value = [record]

    service = ExportService(db)
    csv_content, record_count, item_count = service.export_catalog_to_csv()

    assert record_count == 1
    assert item_count == 1
    assert "Book" in csv_content
    assert "9782211056465" in csv_content
    assert "123" in csv_content
