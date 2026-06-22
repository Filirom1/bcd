"""Unit tests for BCDI to Dublin Core conversion script.

Tests the conversion of BCDI library system exports (French format) to Dublin Core CSV.
"""

import csv
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for importing conversion script
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "convert"))


class TestBCDIConversion:
    """Test BCDI to Dublin Core conversion functionality."""

    def test_basic_bcdi_conversion(self, tmp_path):
        """Test basic BCDI column mapping to Dublin Core format."""
        # Import here to avoid import errors if script doesn't exist yet
        try:
            from bcdi_to_dublin_core import BCDI_COLUMN_MAPPING, convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        # Create sample BCDI input
        bcdi_file = tmp_path / "bcdi_input.csv"
        bcdi_file.write_text(
            "ISBN,Titre,Auteur,Editeur,Support,Cote\n"
            "978-2-07-061234-5,Le Petit Prince,Saint-Exupéry,Gallimard,Livre,R SAI\n"
            "978-2-07-051234-6,L'Étranger,Camus,Gallimard,Livre,R CAM\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_output.csv"

        # Run conversion
        result = convert_bcdi_to_dublin_core(str(bcdi_file), str(output_file))

        assert result is True
        assert output_file.exists()

        # Verify output format (use utf-8-sig to handle BOM)
        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 2

            # Check first row
            assert rows[0]['dc.identifier'] == 'isbn:978-2-07-061234-5'
            assert rows[0]['dc.title'] == 'Le Petit Prince'
            assert rows[0]['dc.creator'] == 'Saint-Exupéry'
            assert rows[0]['dc.publisher'] == 'Gallimard'
            assert rows[0]['dc.type'] == 'Livre'
            assert rows[0]['dc.subject'] == 'R SAI'

    def test_windows1252_to_utf8_encoding(self, tmp_path):
        """Test conversion from Windows-1252 encoding to UTF-8."""
        try:
            from bcdi_to_dublin_core import convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        # Create BCDI file with Windows-1252 encoding (common in French schools)
        bcdi_file = tmp_path / "bcdi_windows1252.csv"
        content = "ISBN,Titre,Auteur,Editeur\n978-2-07-061234-5,L'Été à Paris,Saint-Exupéry,Éditions Gallimard\n"
        bcdi_file.write_text(content, encoding='windows-1252')

        output_file = tmp_path / "dublin_core_utf8.csv"

        # Run conversion
        result = convert_bcdi_to_dublin_core(str(bcdi_file), str(output_file))

        assert result is True

        # Verify UTF-8 output with French characters preserved
        with open(output_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            assert 'L\'Été à Paris' in content
            assert 'Saint-Exupéry' in content
            assert 'Éditions Gallimard' in content

    def test_medium_type_preservation(self, tmp_path):
        """Test that medium types (Support) are preserved as-is without normalization."""
        try:
            from bcdi_to_dublin_core import convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        # Create BCDI with various medium types (BCDI French format)
        bcdi_file = tmp_path / "bcdi_medium_types.csv"
        bcdi_file.write_text(
            "ISBN,Titre,Support\n"
            "123,Book 1,Livre\n"
            "456,Book 2,CD Audio\n"
            "789,Book 3,DVD Vidéo\n"
            "101,Book 4,Livre + CD\n"
            "102,Book 5,Bande dessinée\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_medium.csv"

        result = convert_bcdi_to_dublin_core(str(bcdi_file), str(output_file))

        assert result is True

        # Verify medium types preserved
        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert rows[0]['dc.type'] == 'Livre'
            assert rows[1]['dc.type'] == 'CD Audio'
            assert rows[2]['dc.type'] == 'DVD Vidéo'
            assert rows[3]['dc.type'] == 'Livre + CD'
            assert rows[4]['dc.type'] == 'Bande dessinée'

    def test_isbn_prefix_addition(self, tmp_path):
        """Test that ISBN values get 'isbn:' prefix added."""
        try:
            from bcdi_to_dublin_core import convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        bcdi_file = tmp_path / "bcdi_isbn.csv"
        bcdi_file.write_text(
            "ISBN,Titre\n"
            "978-2-07-061234-5,Book with dashes\n"
            "9782070612345,Book without dashes\n"
            "2-07-061234-5,Old format ISBN\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_isbn.csv"

        result = convert_bcdi_to_dublin_core(str(bcdi_file), str(output_file))

        assert result is True

        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # All ISBNs should have isbn: prefix
            assert rows[0]['dc.identifier'].startswith('isbn:')
            assert rows[1]['dc.identifier'].startswith('isbn:')
            assert rows[2]['dc.identifier'].startswith('isbn:')

    def test_column_mapping_completeness(self, tmp_path):
        """Test that all BCDI columns map correctly to Dublin Core."""
        try:
            from bcdi_to_dublin_core import BCDI_COLUMN_MAPPING
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        # Verify expected mappings exist
        expected_mappings = {
            'ISBN': 'dc.identifier',
            'Titre': 'dc.title',
            'Auteur': 'dc.creator',
            'Editeur': 'dc.publisher',
            'Support': 'dc.type',
            'Cote': 'dc.subject',
        }

        for bcdi_col, dc_col in expected_mappings.items():
            assert bcdi_col in BCDI_COLUMN_MAPPING, f"Missing mapping for {bcdi_col}"
            assert BCDI_COLUMN_MAPPING[bcdi_col] == dc_col, f"Incorrect mapping for {bcdi_col}"

    def test_empty_fields_handling(self, tmp_path):
        """Test that empty fields are handled gracefully."""
        try:
            from bcdi_to_dublin_core import convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        bcdi_file = tmp_path / "bcdi_empty_fields.csv"
        bcdi_file.write_text(
            "ISBN,Titre,Auteur,Editeur\n"
            "978-2-07-061234-5,Le Petit Prince,,Gallimard\n"
            ",L'Étranger,Camus,\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_empty.csv"

        result = convert_bcdi_to_dublin_core(str(bcdi_file), str(output_file))

        assert result is True

        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Empty fields should be empty strings
            assert rows[0]['dc.creator'] == ''
            assert rows[1]['dc.identifier'] == ''
            assert rows[1]['dc.publisher'] == ''

    def test_file_not_found_error(self, tmp_path):
        """Test error handling when input file doesn't exist."""
        try:
            from bcdi_to_dublin_core import convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        result = convert_bcdi_to_dublin_core(
            str(tmp_path / "nonexistent.csv"),
            str(tmp_path / "output.csv")
        )

        assert result is False

    def test_utf8_with_bom_output(self, tmp_path):
        """Test that output uses UTF-8 with BOM for Excel compatibility."""
        try:
            from bcdi_to_dublin_core import convert_bcdi_to_dublin_core
        except ImportError:
            pytest.skip("bcdi_to_dublin_core.py not yet implemented")

        bcdi_file = tmp_path / "bcdi_input.csv"
        bcdi_file.write_text(
            "ISBN,Titre\n978-2-07-061234-5,Le Petit Prince\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_bom.csv"

        result = convert_bcdi_to_dublin_core(str(bcdi_file), str(output_file))

        assert result is True

        # Check for UTF-8 BOM
        with open(output_file, 'rb') as f:
            first_bytes = f.read(3)
            assert first_bytes == b'\xef\xbb\xbf', "Output should have UTF-8 BOM for Excel compatibility"
