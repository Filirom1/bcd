"""Unit tests for ONDE to BCD borrower conversion script.

Tests:
- Column mapping detection
- Grade level extraction
- INE fallback ID generation
- Duplicate INE detection
- CSV format conversion
"""

import csv
import pytest
import tempfile
from pathlib import Path

from bcd_converters.onde_to_bcd_borrowers import (
    extract_grade_level,
    generate_borrower_id,
    find_column_mapping,
    normalize_column_name,
    convert_onde_to_bcd
)


class TestGradeLevelExtraction:
    """Test grade level extraction from class names."""

    def test_extract_grade_with_dash_separator(self):
        """CP-A should extract to CP."""
        assert extract_grade_level('CP-A') == 'CP'
        assert extract_grade_level('CE1-B') == 'CE1'
        assert extract_grade_level('CM2-C') == 'CM2'

    def test_extract_grade_with_space_separator(self):
        """CP A should extract to CP."""
        assert extract_grade_level('CP A') == 'CP'
        assert extract_grade_level('CE1 B') == 'CE1'

    def test_extract_grade_without_separator(self):
        """CM2 should remain CM2."""
        assert extract_grade_level('CM2') == 'CM2'
        assert extract_grade_level('CP') == 'CP'

    def test_extract_grade_empty_string(self):
        """Empty string should return empty."""
        assert extract_grade_level('') == ''

    def test_extract_grade_with_multiple_separators(self):
        """CP-A-Matin should extract to CP."""
        assert extract_grade_level('CP-A-Matin') == 'CP'


class TestBorrowerIdGeneration:
    """Test borrower ID generation for missing INE."""

    def test_generate_borrower_id_format(self):
        """Should generate STUDENT-#### format."""
        assert generate_borrower_id(1) == 'STUDENT-0001'
        assert generate_borrower_id(42) == 'STUDENT-0042'
        assert generate_borrower_id(999) == 'STUDENT-0999'
        assert generate_borrower_id(1234) == 'STUDENT-1234'

    def test_generate_borrower_id_padding(self):
        """Should zero-pad to 4 digits."""
        assert len(generate_borrower_id(1).split('-')[1]) == 4
        assert len(generate_borrower_id(99).split('-')[1]) == 4


class TestColumnMapping:
    """Test ONDE column name detection and mapping."""

    def test_standard_onde_columns(self):
        """Should detect standard ONDE column names."""
        headers = ['Nom', 'Prénom', 'INE', 'Identifiant Classe']
        mapping = find_column_mapping(headers)

        assert mapping['last_name'] == 'Nom'
        assert mapping['first_name'] == 'Prénom'
        assert mapping['borrower_id'] == 'INE'
        assert mapping['class'] == 'Identifiant Classe'

    def test_alternative_onde_columns(self):
        """Should detect alternative ONDE column names."""
        headers = ['Nom de l\'élève', 'Prénom de l\'élève', 'Numéro INE', 'Classe']
        mapping = find_column_mapping(headers)

        assert mapping['last_name'] == 'Nom de l\'élève'
        assert mapping['first_name'] == 'Prénom de l\'élève'
        assert mapping['borrower_id'] == 'Numéro INE'
        assert mapping['class'] == 'Classe'

    def test_case_insensitive_matching(self):
        """Should match columns case-insensitively."""
        headers = ['NOM', 'PRENOM', 'ine', 'classe']
        mapping = find_column_mapping(headers)

        assert mapping['last_name'] == 'NOM'
        assert mapping['first_name'] == 'PRENOM'
        assert mapping['borrower_id'] == 'ine'
        assert mapping['class'] == 'classe'

    def test_missing_optional_columns(self):
        """Should handle missing optional columns."""
        headers = ['Nom', 'Prénom']  # Missing INE and class
        mapping = find_column_mapping(headers)

        assert mapping['last_name'] == 'Nom'
        assert mapping['first_name'] == 'Prénom'
        assert mapping['borrower_id'] is None
        assert mapping['class'] is None


class TestColumnNameNormalization:
    """Test column name normalization."""

    def test_normalize_removes_whitespace(self):
        """Should remove leading/trailing whitespace."""
        assert normalize_column_name('  Nom  ') == 'Nom'
        assert normalize_column_name('\tPrénom\n') == 'Prénom'

    def test_normalize_preserves_content(self):
        """Should preserve column content."""
        assert normalize_column_name('Nom de l\'élève') == 'Nom de l\'élève'


class TestConversionEndToEnd:
    """End-to-end conversion tests."""

    def test_basic_onde_conversion(self):
        """Should convert basic ONDE CSV to BCD format."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f_in:
            input_path = Path(f_in.name)
            writer = csv.writer(f_in, delimiter=';')
            writer.writerow(['Nom', 'Prénom', 'INE', 'Identifiant Classe'])
            writer.writerow(['Dupont', 'Marie', '12345678901', 'CP-A'])
            writer.writerow(['Martin', 'Lucas', '98765432109', 'CE1-B'])

        # Create temporary output file
        output_path = Path(tempfile.mktemp(suffix='.csv'))

        try:
            # Convert
            convert_onde_to_bcd(input_path, output_path, delimiter=';')

            # Read output
            with open(output_path, 'r', encoding='utf-8-sig', newline='') as f_out:
                reader = csv.DictReader(f_out)
                rows = list(reader)

            # Validate
            assert len(rows) == 2

            # Check first row
            assert rows[0]['borrower_id'] == '12345678901'
            assert rows[0]['first_name'] == 'Marie'
            assert rows[0]['last_name'] == 'Dupont'
            assert rows[0]['role'] == 'student'
            assert rows[0]['class'] == 'CP'
            assert rows[0]['active'] == 'true'

            # Check second row
            assert rows[1]['borrower_id'] == '98765432109'
            assert rows[1]['first_name'] == 'Lucas'
            assert rows[1]['last_name'] == 'Martin'
            assert rows[1]['class'] == 'CE1'

        finally:
            # Cleanup
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def test_conversion_with_missing_ine(self):
        """Should generate fallback IDs for missing INE."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f_in:
            input_path = Path(f_in.name)
            writer = csv.writer(f_in, delimiter=';')
            writer.writerow(['Nom', 'Prénom', 'INE', 'Classe'])
            writer.writerow(['Dupont', 'Marie', '', 'CP'])  # Missing INE
            writer.writerow(['Martin', 'Lucas', '98765432109', 'CE1'])

        output_path = Path(tempfile.mktemp(suffix='.csv'))

        try:
            convert_onde_to_bcd(input_path, output_path, delimiter=';')

            with open(output_path, 'r', encoding='utf-8-sig', newline='') as f_out:
                reader = csv.DictReader(f_out)
                rows = list(reader)

            # First row should have generated ID
            assert rows[0]['borrower_id'] == 'STUDENT-0001'
            assert rows[0]['first_name'] == 'Marie'
            assert rows[0]['notes'] == 'Imported from ONDE'

            # Second row should have INE
            assert rows[1]['borrower_id'] == '98765432109'
            assert rows[1]['notes'] == ''

        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def test_conversion_skips_duplicate_ine(self):
        """Should skip rows with duplicate INE values."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f_in:
            input_path = Path(f_in.name)
            writer = csv.writer(f_in, delimiter=';')
            writer.writerow(['Nom', 'Prénom', 'INE', 'Classe'])
            writer.writerow(['Dupont', 'Marie', '12345678901', 'CP'])
            writer.writerow(['Martin', 'Lucas', '12345678901', 'CE1'])  # Duplicate INE
            writer.writerow(['Bernard', 'Sophie', '98765432109', 'CM1'])

        output_path = Path(tempfile.mktemp(suffix='.csv'))

        try:
            convert_onde_to_bcd(input_path, output_path, delimiter=';')

            with open(output_path, 'r', encoding='utf-8-sig', newline='') as f_out:
                reader = csv.DictReader(f_out)
                rows = list(reader)

            # Should only have 2 rows (duplicate skipped)
            assert len(rows) == 2
            assert rows[0]['borrower_id'] == '12345678901'
            assert rows[0]['first_name'] == 'Marie'
            assert rows[1]['borrower_id'] == '98765432109'
            assert rows[1]['first_name'] == 'Sophie'

        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def test_conversion_extracts_grade_levels(self):
        """Should extract grade levels from class names."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f_in:
            input_path = Path(f_in.name)
            writer = csv.writer(f_in, delimiter=';')
            writer.writerow(['Nom', 'Prénom', 'INE', 'Identifiant Classe'])
            writer.writerow(['Dupont', 'Marie', '111', 'CP-A'])
            writer.writerow(['Martin', 'Lucas', '222', 'CE1-B'])
            writer.writerow(['Bernard', 'Sophie', '333', 'CM2 C'])  # Space separator

        output_path = Path(tempfile.mktemp(suffix='.csv'))

        try:
            convert_onde_to_bcd(input_path, output_path, delimiter=';')

            with open(output_path, 'r', encoding='utf-8-sig', newline='') as f_out:
                reader = csv.DictReader(f_out)
                rows = list(reader)

            assert rows[0]['class'] == 'CP'
            assert rows[1]['class'] == 'CE1'
            assert rows[2]['class'] == 'CM2'

        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    def test_conversion_with_comma_delimiter(self):
        """Should support comma-delimited input."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f_in:
            input_path = Path(f_in.name)
            writer = csv.writer(f_in, delimiter=',')  # Comma instead of semicolon
            writer.writerow(['Nom', 'Prénom', 'INE', 'Classe'])
            writer.writerow(['Dupont', 'Marie', '12345678901', 'CP'])

        output_path = Path(tempfile.mktemp(suffix='.csv'))

        try:
            # Specify comma delimiter
            convert_onde_to_bcd(input_path, output_path, delimiter=',')

            with open(output_path, 'r', encoding='utf-8-sig', newline='') as f_out:
                reader = csv.DictReader(f_out)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]['borrower_id'] == '12345678901'

        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
