import pytest

pytest.importorskip("xlrd")

from bcd_converters.xls_classes_to_csv import is_data_row, sheet_name_to_class


def test_xls_helpers_filter_headers():
    assert sheet_name_to_class("CM1 2025") == "CM1"
    assert is_data_row(["Dupont", "Alice"])
    assert not is_data_row(["Classe - enseignant", "Alice"])
    assert not is_data_row(["Dupont", ""])
    assert not is_data_row(["Élève 12", "Alice"])
