from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bcd_cli.commands.catalog import catalog


def test_catalog_search_builds_filters_and_displays_results():
    client = MagicMock()
    client.get.return_value = MagicMock(status_code=200, json=lambda: {"total": 2, "items": [{"id": 1, "title": "Book", "authors": ["Author"], "isbn": "123", "total_items": 3}]})
    with patch("bcd_cli.commands.catalog.get_client", return_value=client):
        result = CliRunner().invoke(catalog, ["search", "--title", "Book", "--author", "Author", "--limit", "1"])
    assert result.exit_code == 0
    assert client.get.call_args.kwargs["params"] == {"title": "Book", "author": "Author", "limit": 1}
    assert "Found 2 records" in result.output
    assert "Showing 1 of 2" in result.output


def test_catalog_search_empty_result():
    client = MagicMock()
    client.get.return_value = MagicMock(status_code=200, json=lambda: {"total": 0, "items": []})
    with patch("bcd_cli.commands.catalog.get_client", return_value=client):
        result = CliRunner().invoke(catalog, ["search"])
    assert result.exit_code == 0
    assert "No records found" in result.output


def test_catalog_search_api_error():
    client = MagicMock()
    client.get.return_value = MagicMock(status_code=500)
    with patch("bcd_cli.commands.catalog.get_client", return_value=client):
        result = CliRunner().invoke(catalog, ["search"])
    assert result.exit_code != 0
    assert "Search failed" in result.output


def test_catalog_transform_writes_dublin_core(tmp_path):
    source = tmp_path / "input.csv"
    target = tmp_path / "output.csv"
    source.write_text("title,author\nBook,Author\n", encoding="cp1252")
    with patch("src.bcd_api.services.csv_transform.transform_bcd_to_dublin_core", return_value="dc.title,dc.creator\nBook,Author\n"):
        result = CliRunner().invoke(catalog, ["transform", str(source), str(target)])
    assert result.exit_code == 0
    assert target.read_text() == "dc.title,dc.creator\nBook,Author\n"
