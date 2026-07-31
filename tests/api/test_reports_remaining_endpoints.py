from src.bcd_api.api.v1 import reports


def test_never_borrowed_report_paginates(monkeypatch):
    items = [{"id": i} for i in range(4)]
    monkeypatch.setattr(reports.report_service, "get_never_borrowed_items", lambda *args, **kwargs: items)
    assert reports.get_never_borrowed_report(limit=2, offset=1, db="db")["items"] == [{"id": 1}, {"id": 2}]


def test_most_borrowed_report_forwards_filters(monkeypatch):
    titles = [{"title": "Book"}]
    calls = []
    monkeypatch.setattr(reports.report_service, "get_most_borrowed_titles", lambda *args, **kwargs: calls.append(kwargs) or titles)
    result = reports.get_most_borrowed_report(period="month", limit=5, offset=0, medium_type="Livre", target_audience=None, db="db")
    assert result["titles"] == titles
    assert calls[0]["period"] == "month"
    assert calls[0]["medium_type"] == "Livre"


def test_circulation_statistics_delegates(monkeypatch):
    monkeypatch.setattr(reports.report_service, "get_circulation_statistics", lambda db, period: {"period": period})
    assert reports.get_circulation_statistics(period="month", db="db") == {"period": "month"}


def test_borrower_statistics_delegates(monkeypatch):
    monkeypatch.setattr(reports.report_service, "get_borrower_statistics", lambda db, borrower_id: {"borrower_id": borrower_id})
    assert reports.get_borrower_statistics(7, db="db") == {"borrower_id": 7}


def test_holds_report_paginates(monkeypatch):
    holds = [{"id": i} for i in range(3)]
    monkeypatch.setattr(reports.report_service, "get_holds_report", lambda *args, **kwargs: holds)
    result = reports.get_holds_report(status="ready", limit=1, offset=1, db="db")
    assert result["total_holds"] == 3
    assert result["items"] == [{"id": 1}]


def test_active_loans_report_paginates(monkeypatch):
    loans = [{"id": i} for i in range(3)]
    monkeypatch.setattr(reports.report_service, "get_active_loans", lambda *args, **kwargs: loans)
    result = reports.get_active_loans_report(class_name="CP", limit=2, offset=1, db="db")
    assert result["total_active_loans"] == 3
    assert result["items"] == [{"id": 1}, {"id": 2}]
