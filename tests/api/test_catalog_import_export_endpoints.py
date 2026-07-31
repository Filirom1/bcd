from pathlib import Path
from unittest.mock import MagicMock

from src.bcd_api.api.v1 import catalog


def test_list_importers_includes_native_and_external(monkeypatch):
    monkeypatch.setattr("bcd_converters.list_converters", lambda: [{"name": "bibliopuce", "description": "BiblioPuce"}])
    result = catalog.list_importers()
    assert result["importers"][0]["name"] == "dublin_core"
    assert result["importers"][1]["name"] == "bibliopuce"


def test_catalog_template_returns_file_response(monkeypatch, tmp_path):
    template = tmp_path / "catalog.csv"
    template.write_text("dc.title\n")
    monkeypatch.setattr("src.bcd_api.core.portable.get_bundled_resource", lambda path: template)
    result = catalog.get_catalog_template()
    assert result.filename == "catalog_dublin_core_template.csv"
    assert result.media_type == "text/csv"


def test_export_catalog_returns_csv_and_counts(monkeypatch):
    service = MagicMock()
    service.export_catalog_to_csv.return_value = ("dc.title\nBook\n", 1, 2)
    monkeypatch.setattr(catalog, "ExportService", lambda db: service)
    result = catalog.export_catalog(db=object())
    assert result.media_type == "text/csv; charset=utf-8"
    assert result.headers["X-Record-Count"] == "1"
    assert result.headers["X-Item-Count"] == "2"
    assert b"Book" in result.body
