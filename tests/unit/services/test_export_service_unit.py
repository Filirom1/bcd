from src.bcd_api.services.catalog.export import ExportService


def test_export_format_helpers():
    service = ExportService(None)
    assert service._deserialize_list_to_pipe('["Alice", "Bob"]') == "Alice|Bob"
    assert service._deserialize_list_to_pipe("invalid") == ""
    assert service._deserialize_list_to_pipe('["Illustrator"]') == "Illustrator"
    assert service._deserialize_list_to_pipe('["magic", "school"]') == "magic|school"
    assert service._format_isbn("978123") == "isbn:978123"
    assert service._format_isbn("ISSN:1234-567X") == "ISSN:1234-567X"
    assert service._format_isbn("") == ""
    assert service._format_loanable(True) == "Loanable"
    assert service._format_loanable(False) == "Not loanable"
    assert service._format_loanable(None) == ""
    assert service._format_page_count(300) == "300 pages"
    assert service._format_page_count(0) == ""
