from types import SimpleNamespace

from src.bcd_api.api.v1 import circulation, holds


def test_checkout_endpoint_forwards_request(monkeypatch):
    calls = []
    monkeypatch.setattr(circulation.circulation_service, "checkout_items", lambda **kwargs: calls.append(kwargs) or {"ok": True})
    result = circulation.checkout_items(SimpleNamespace(borrower_id="B1", item_ids=["I1"], checked_out_by="api"), db="db")
    assert result == {"ok": True}
    assert calls[0]["item_ids"] == ["I1"]


def test_return_endpoint_forwards_request(monkeypatch):
    monkeypatch.setattr(circulation.circulation_service, "return_items", lambda **kwargs: kwargs)
    result = circulation.return_items(SimpleNamespace(item_ids=["I1"], returned_by="api"), db="db")
    assert result["returned_by"] == "api"


def test_renew_endpoint_uses_explicit_items(monkeypatch):
    calls = []
    monkeypatch.setattr(circulation.circulation_service, "renew_items", lambda **kwargs: calls.append(kwargs) or {"ok": True})
    result = circulation.renew_items(SimpleNamespace(borrower_id="B1", item_ids=["I1"]), db="db")
    assert result == {"ok": True}
    assert calls[0]["item_ids"] == ["I1"]


def test_renew_endpoint_selects_renewable_current_loans(monkeypatch):
    calls = []
    monkeypatch.setattr(circulation.circulation_service, "renew_items", lambda **kwargs: calls.append(kwargs) or {"ok": True})
    result = circulation.renew_items(SimpleNamespace(borrower_id="B1", item_ids=None), db="db")
    assert result == {"ok": True}
    assert calls[0]["item_ids"] is None


def test_create_hold_forwards_data(monkeypatch):
    monkeypatch.setattr(holds.hold_commands, "create_hold", lambda **kwargs: kwargs)
    result = holds.create_hold(SimpleNamespace(borrower_id=1, bibliographic_record_id=2, created_by=None, notes="note"), db="db")
    assert result["created_by"] == "api"
    assert result["notes"] == "note"


def test_get_hold_forwards_id(monkeypatch):
    monkeypatch.setattr(holds.hold_queries, "get_hold", lambda db, hold_id: {"id": hold_id})
    assert holds.get_hold(3, db="db") == {"id": 3}


def test_get_holds_for_borrower_forwards_flag(monkeypatch):
    monkeypatch.setattr(holds.hold_queries, "get_holds_for_borrower", lambda *args, **kwargs: kwargs)
    result = holds.get_holds_for_borrower(1, include_fulfilled=True, db="db")
    assert result["include_fulfilled"] is True


def test_get_holds_for_title_forwards_active_flag(monkeypatch):
    monkeypatch.setattr(holds.hold_queries, "get_holds_for_bibliographic_record", lambda *args, **kwargs: kwargs)
    result = holds.get_holds_for_title(2, active_only=False, db="db")
    assert result["active_only"] is False


def test_ready_holds_delegates(monkeypatch):
    expected = [{"id": 1}]
    monkeypatch.setattr(holds.hold_queries, "get_ready_holds", lambda db: expected)
    assert holds.get_ready_holds(db="db") == expected


def test_borrower_current_loans_delegates(monkeypatch):
    expected = [{"item_id": "I1"}]
    monkeypatch.setattr(circulation.circulation_service, "get_borrower_current_loans", lambda db, borrower_id: expected)
    assert circulation.get_borrower_current_loans("B1", db="db") == {"borrower_id": "B1", "loans_count": 1, "loans": expected}


def test_ready_route_precedes_dynamic_hold_route():
    paths = [route.path for route in holds.router.routes]
    assert paths.index("/holds/ready") < paths.index("/holds/{hold_id}")
