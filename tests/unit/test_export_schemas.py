import pytest
from pydantic import ValidationError

from bcd_api.schemas.export import ExportResponse, ExportStats, ExportFormat, ImportResponse


def test_export_response_defaults_and_counts():
    result = ExportResponse(filename="catalog.csv", record_count=2, item_count=3)
    assert result.content_type.startswith("text/csv")
    assert result.encoding == "utf-8"


def test_export_response_rejects_negative_counts():
    with pytest.raises(ValidationError):
        ExportResponse(filename="catalog.csv", record_count=-1, item_count=0)


def test_export_stats_and_import_defaults():
    stats = ExportStats(total_records=3, total_items=4, records_with_items=2, records_without_items=1)
    result = ImportResponse(total_rows=1, successful_rows=1, failed_rows=0)
    assert stats.execution_time_ms is None
    assert result.errors == []
    assert ExportFormat.CSV.value == "csv"
