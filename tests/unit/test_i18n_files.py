"""
Tests for i18n translation files.

Validates that JSON files are valid and contain required keys.
"""

import json
from pathlib import Path

# Path to locales directory
LOCALES_DIR = Path(__file__).parent.parent.parent / "src" / "bcd_web_vue" / "locales"


class TestI18nFiles:
    """Test suite for i18n translation files."""

    def test_en_json_is_valid(self):
        """Test that en.json is valid JSON."""
        en_file = LOCALES_DIR / "en.json"
        assert en_file.exists(), "en.json file not found"

        with open(en_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, dict), "en.json should contain a JSON object"
        assert len(data) > 0, "en.json should not be empty"

    def test_fr_json_is_valid(self):
        """Test that fr.json is valid JSON."""
        fr_file = LOCALES_DIR / "fr.json"
        assert fr_file.exists(), "fr.json file not found"

        with open(fr_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, dict), "fr.json should contain a JSON object"
        assert len(data) > 0, "fr.json should not be empty"

    def test_en_and_fr_have_same_top_level_keys(self):
        """Test that en.json and fr.json have the same top-level keys."""
        en_file = LOCALES_DIR / "en.json"
        fr_file = LOCALES_DIR / "fr.json"

        with open(en_file, 'r', encoding='utf-8') as f:
            en_data = json.load(f)

        with open(fr_file, 'r', encoding='utf-8') as f:
            fr_data = json.load(f)

        en_keys = set(en_data.keys())
        fr_keys = set(fr_data.keys())

        missing_in_fr = en_keys - fr_keys
        missing_in_en = fr_keys - en_keys

        assert not missing_in_fr, f"Keys missing in fr.json: {missing_in_fr}"
        assert not missing_in_en, f"Keys missing in en.json: {missing_in_en}"

    def test_required_sections_exist(self):
        """Test that required translation sections exist in both files."""
        required_sections = [
            "common",
            "borrower",
            "borrowers",
            "catalog",
            "admin",
            "errors"
        ]

        en_file = LOCALES_DIR / "en.json"
        fr_file = LOCALES_DIR / "fr.json"

        with open(en_file, 'r', encoding='utf-8') as f:
            en_data = json.load(f)

        with open(fr_file, 'r', encoding='utf-8') as f:
            fr_data = json.load(f)

        for section in required_sections:
            assert section in en_data, f"Section '{section}' missing in en.json"
            assert section in fr_data, f"Section '{section}' missing in fr.json"
