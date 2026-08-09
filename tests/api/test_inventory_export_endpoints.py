from src.bcd_api.api.v1 import inventory
from src.bcd_api.schemas.inventory import ExportCSVRequest


def test_export_inventory_csv_returns_download(monkeypatch):
    monkeypatch.setattr(inventory.inventory_service, "get_items_csv", lambda db, ids: "barcode,title\n.I1,Book\n")
    response = inventory.export_csv_endpoint(ExportCSVRequest(item_ids=["I1"]), db="db")
    assert response.media_type == "text/csv; charset=utf-8"
    assert b"Book" in response.body
