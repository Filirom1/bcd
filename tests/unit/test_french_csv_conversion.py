"""Unit tests for French CSV to Dublin Core conversion script.

Tests automatic column detection and mapping for French CSV exports.
"""

import pytest
import csv
import sys
from pathlib import Path
import unicodedata

# Add scripts directory to path for importing conversion script
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "convert"))


class TestFrenchCSVConversion:
    """Test French CSV to Dublin Core conversion functionality."""

    def test_basic_french_csv_conversion(self, tmp_path):
        """Test basic French column name detection and mapping."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        # Create sample French CSV with common column names
        french_file = tmp_path / "french_input.csv"
        french_file.write_text(
            "Titre,Auteur,ISBN,Editeur,Type\n"
            "Le Petit Prince,Saint-Exupéry,978-2-07-061234-5,Gallimard,Livre\n"
            "L'Étranger,Camus,978-2-07-051234-6,Gallimard,Livre\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_output.csv"

        # Run conversion
        result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

        assert result is True
        assert output_file.exists()

        # Verify output format
        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 2

            # Check column mapping worked
            assert 'dc.title' in rows[0]
            assert 'dc.creator' in rows[0]
            assert 'dc.identifier' in rows[0]
            assert 'dc.publisher' in rows[0]
            assert 'dc.type' in rows[0]

            # Check values
            assert rows[0]['dc.title'] == 'Le Petit Prince'
            assert rows[0]['dc.creator'] == 'Saint-Exupéry'
            assert rows[0]['dc.identifier'].startswith('isbn:')

    def test_case_insensitive_matching(self, tmp_path):
        """Test that column matching is case-insensitive."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        # Test various cases
        french_file = tmp_path / "french_case.csv"
        french_file.write_text(
            "TITRE,auteur,Isbn\n"
            "Book 1,Author 1,123456\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_case.csv"

        result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

        assert result is True

        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should map despite different cases
            assert 'dc.title' in rows[0]
            assert 'dc.creator' in rows[0]
            assert 'dc.identifier' in rows[0]

    def test_accent_insensitive_matching(self, tmp_path):
        """Test that column matching handles accents (éditeur → editeur)."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core, normalize_column_name
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        # Test normalize function directly
        assert normalize_column_name('Éditeur') == 'editeur'
        assert normalize_column_name('Année') == 'annee'
        assert normalize_column_name('Créateur') == 'createur'

        # Test full conversion with accented column names
        french_file = tmp_path / "french_accents.csv"
        french_file.write_text(
            "Titre,Éditeur,Année\n"
            "Book 1,Publisher 1,2024\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_accents.csv"

        result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

        assert result is True

        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should map Éditeur to dc.publisher
            assert 'dc.publisher' in rows[0]
            assert rows[0]['dc.publisher'] == 'Publisher 1'

    def test_unmapped_column_warnings(self, tmp_path, capfd):
        """Test that unmapped columns generate warnings."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        french_file = tmp_path / "french_unmapped.csv"
        french_file.write_text(
            "Titre,Unknown_Column_Name,Another_Unknown\n"
            "Book 1,Value 1,Value 2\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_unmapped.csv"

        result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

        assert result is True

        # Check that warnings were printed
        captured = capfd.readouterr()
        assert 'unmapped' in captured.out.lower() or 'unmapped' in captured.err.lower()

    def test_column_pattern_variations(self, tmp_path):
        """Test multiple column name patterns for same field."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        # Test various title patterns
        variations = [
            "Titre,Auteur\nBook 1,Author 1\n",
            "Titre du livre,Auteur\nBook 1,Author 1\n",
            "Nom du livre,Nom de l'auteur\nBook 1,Author 1\n",
        ]

        for i, csv_content in enumerate(variations):
            french_file = tmp_path / f"french_var_{i}.csv"
            french_file.write_text(csv_content, encoding='utf-8')

            output_file = tmp_path / f"dublin_core_var_{i}.csv"

            result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

            assert result is True, f"Variation {i} failed"

            with open(output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # All variations should map to dc.title and dc.creator
                assert 'dc.title' in rows[0], f"Variation {i}: dc.title not found"
                assert 'dc.creator' in rows[0], f"Variation {i}: dc.creator not found"
                assert rows[0]['dc.title'] == 'Book 1'
                assert rows[0]['dc.creator'] == 'Author 1'

    def test_publisher_column_variations(self, tmp_path):
        """Test publisher column name detection (Editeur, Éditeur, Maison d'édition)."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        variations = [
            "Titre,Editeur\nBook,Publisher\n",
            "Titre,Éditeur\nBook,Publisher\n",
            "Titre,Maison d'édition\nBook,Publisher\n",
        ]

        for i, csv_content in enumerate(variations):
            french_file = tmp_path / f"french_pub_{i}.csv"
            french_file.write_text(csv_content, encoding='utf-8')

            output_file = tmp_path / f"dublin_core_pub_{i}.csv"

            result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

            assert result is True

            with open(output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                assert 'dc.publisher' in rows[0], f"Publisher variation {i} not detected"
                assert rows[0]['dc.publisher'] == 'Publisher'

    def test_medium_type_column_variations(self, tmp_path):
        """Test medium type/format column name detection (Support, Type, Format)."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        variations = [
            "Titre,Support\nBook,Livre\n",
            "Titre,Type\nBook,Livre\n",
            "Titre,Format\nBook,Livre\n",
            "Titre,Type de média\nBook,Livre\n",
        ]

        for i, csv_content in enumerate(variations):
            french_file = tmp_path / f"french_type_{i}.csv"
            french_file.write_text(csv_content, encoding='utf-8')

            output_file = tmp_path / f"dublin_core_type_{i}.csv"

            result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

            assert result is True

            with open(output_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                assert 'dc.type' in rows[0], f"Type variation {i} not detected"
                assert rows[0]['dc.type'] == 'Livre'

    def test_isbn_prefix_normalization(self, tmp_path):
        """Test that ISBN values get normalized with 'isbn:' prefix."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        french_file = tmp_path / "french_isbn.csv"
        french_file.write_text(
            "Titre,ISBN\n"
            "Book 1,978-2-07-061234-5\n"
            "Book 2,9782070612345\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_isbn.csv"

        result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

        assert result is True

        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # All ISBNs should have isbn: prefix
            assert rows[0]['dc.identifier'].startswith('isbn:')
            assert rows[1]['dc.identifier'].startswith('isbn:')

    def test_utf8_with_bom_output(self, tmp_path):
        """Test that output uses UTF-8 with BOM for Excel compatibility."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        french_file = tmp_path / "french_input.csv"
        french_file.write_text(
            "Titre,Auteur\nLe Petit Prince,Saint-Exupéry\n",
            encoding='utf-8'
        )

        output_file = tmp_path / "dublin_core_bom.csv"

        result = convert_french_csv_to_dublin_core(str(french_file), str(output_file))

        assert result is True

        # Check for UTF-8 BOM
        with open(output_file, 'rb') as f:
            first_bytes = f.read(3)
            assert first_bytes == b'\xef\xbb\xbf', "Output should have UTF-8 BOM for Excel compatibility"

    def test_file_not_found_error(self, tmp_path):
        """Test error handling when input file doesn't exist."""
        try:
            from french_csv_to_dublin_core import convert_french_csv_to_dublin_core
        except ImportError:
            pytest.skip("french_csv_to_dublin_core.py not yet implemented")

        result = convert_french_csv_to_dublin_core(
            str(tmp_path / "nonexistent.csv"),
            str(tmp_path / "output.csv")
        )

        assert result is False
