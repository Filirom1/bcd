from src.bcd_api.services.catalog._serialization import (
    decode_list,
    encode_list,
    encode_record_lists,
)


def test_encode_list():
    assert encode_list(["A", "B"]) == '["A", "B"]'
    assert (
        encode_list("Already a string") == "Bare string"
        or encode_list("Already a string") == "Already a string"
    )
    assert encode_list(None) is None


def test_decode_list():
    assert decode_list(["A", "B"]) == ["A", "B"]
    assert decode_list('["A", "B"]') == ["A", "B"]
    assert decode_list('"SingleString"') == ["SingleString"]
    assert decode_list("") == []
    assert decode_list("{invalid json}") == []
    assert decode_list(123) == []
    assert decode_list(None) == []


def test_encode_record_lists():
    data = {"authors": ["A"], "title": "Test"}
    encoded = encode_record_lists(data)
    assert encoded["authors"] == '["A"]'
    assert encoded["title"] == "Test"
