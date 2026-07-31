from unittest.mock import patch

import pytest

from src import bcd_converters


def test_list_converters_returns_sorted_metadata():
    converters = bcd_converters.list_converters()
    names = [converter["name"] for converter in converters]
    assert names == sorted(names)
    assert all("description" in converter for converter in converters)


def test_get_converter_unknown_name_raises():
    with pytest.raises(ModuleNotFoundError):
        bcd_converters.get_converter("does_not_exist")


def test_get_description_returns_module_docstring():
    assert "Convert" in bcd_converters._get_description("bibliopuce_to_dublin_core")


def test_get_description_returns_empty_when_import_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(bcd_converters.Path, "is_file", lambda self: False)
    with patch("importlib.import_module", side_effect=ImportError):
        assert bcd_converters._get_description("missing") == ""
