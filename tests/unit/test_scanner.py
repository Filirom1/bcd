from unittest.mock import patch

import pytest

from src.bcd_cli.utils import scanner


def test_read_barcode_input_strips_value():
    with patch.object(scanner.console, "input", return_value="  ABC123  "):
        assert scanner.read_barcode_input(">") == "ABC123"


def test_read_barcode_input_returns_empty_on_eof():
    with patch.object(scanner.console, "input", side_effect=EOFError):
        assert scanner.read_barcode_input(">") == ""


def test_read_multiple_barcodes_stops_on_empty():
    with patch.object(scanner.console, "input", side_effect=["A", "B", ""]):
        assert scanner.read_multiple_barcodes("Scan") == ["A", "B"]


def test_read_multiple_barcodes_stops_on_eof():
    with patch.object(scanner.console, "input", side_effect=EOFError):
        assert scanner.read_multiple_barcodes("Scan") == []


@pytest.mark.parametrize("value, expected", [("1,2,2", [1, 2]), ("1-3", [1, 2, 3]), ("", [])])
def test_read_selection_parses_numbers_and_ranges(value, expected):
    with patch.object(scanner.console, "input", return_value=value):
        assert scanner.read_selection_from_list(5) == expected


def test_read_selection_ignores_invalid_and_out_of_range_values():
    with patch.object(scanner.console, "input", return_value="0,6,nope,2"):
        assert scanner.read_selection_from_list(5) == [2]
