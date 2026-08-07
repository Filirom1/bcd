from src.bcd_api.api.v1 import reports


def test_collection_stats_forwards_filters(monkeypatch):
    calls = []
    monkeypatch.setattr(reports.report_service, "get_collection_stats", lambda *args, **kwargs: calls.append((args, kwargs)) or {"total": 2})
    result = reports.get_collection_stats(crew_method="rotation", min_age_years=2, exclude_periodicals=False, medium_type="Livre", db="db")
    assert result == {"total": 2}
    assert calls[0][0] == ("db",)
    assert calls[0][1]["crew_method"] == "rotation"
    assert calls[0][1]["medium_type"] == "Livre"


def test_overdue_report_paginates_results(monkeypatch):
    items = [{"id": i} for i in range(5)]
    def mock_get_overdue_items(db, class_name=None, academic_year=None, limit=None, offset=None):
        off = offset or 0
        lim = limit or 5
        return items[off:off+lim], len(items)
    monkeypatch.setattr(reports.report_service, "get_overdue_items", mock_get_overdue_items)
    result = reports.get_overdue_report(limit=2, offset=1, db="db")
    assert result == {"total_overdue": 5, "items": [{"id": 1}, {"id": 2}], "limit": 2, "offset": 1}


def test_overdue_summary_counts_classes(monkeypatch):
    summary = [{"class_name": "CP", "overdue_count": 2}, {"class_name": "CE1", "overdue_count": 3}]
    monkeypatch.setattr(reports.report_service, "get_overdue_summary_by_class", lambda db, academic_year=None: summary)
    result = reports.get_overdue_summary_by_class(academic_year="2025", db="db")
    assert result == {"classes": summary, "total_overdue": 5}
