from src.bcd_api.services.report_service import _deserialize_authors


def test_deserialize_authors_supports_json_list():
    assert _deserialize_authors('["Alice", "Bob"]') == "Alice, Bob"


def test_deserialize_authors_returns_none_for_non_json_values():
    assert _deserialize_authors(["Alice", "Bob"]) is None
    assert _deserialize_authors(None) is None
    assert _deserialize_authors("") is None


def test_deserialize_authors_returns_none_for_invalid_json():
    assert _deserialize_authors("not-json") is None
