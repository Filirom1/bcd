"""Unit tests for settings_service.py"""

import pytest

from src.bcd_api.core.exceptions import NotFoundError
from src.bcd_api.models.system_settings import SystemSettings
from src.bcd_api.services import settings_service


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_success(self, db_session):
        """Test getting settings when they exist."""
        # Create settings
        settings = SystemSettings(
            id=1,
            library_name="Test Library",
            language="fr",
        )
        db_session.add(settings)
        db_session.commit()

        # Get settings
        result = settings_service.get_settings(db_session)

        assert result.id == 1
        assert result.library_name == "Test Library"
        assert result.language == "fr"

    def test_get_settings_not_found(self, db_session):
        """Test error when settings don't exist."""
        with pytest.raises(NotFoundError) as exc_info:
            settings_service.get_settings(db_session)

        assert "SystemSettings" in str(exc_info.value)


class TestUpdateSettings:
    """Test update_settings function."""

    def test_update_single_field(self, db_session):
        """Test updating a single field."""
        # Create settings
        settings = SystemSettings(id=1, library_name="Old Name")
        db_session.add(settings)
        db_session.commit()

        # Update
        result = settings_service.update_settings(
            db_session,
            {"library_name": "New Name"}
        )

        assert result.library_name == "New Name"

    def test_update_multiple_fields(self, db_session):
        """Test updating multiple fields."""
        settings = SystemSettings(id=1, library_name="Test", language="fr")
        db_session.add(settings)
        db_session.commit()

        result = settings_service.update_settings(
            db_session,
            {
                "library_name": "Updated Library",
                "language": "en",
                "loan_duration_days": 21,
            }
        )

        assert result.library_name == "Updated Library"
        assert result.language == "en"
        assert result.loan_duration_days == 21

    def test_update_ignores_invalid_fields(self, db_session):
        """Test that invalid field names are ignored."""
        settings = SystemSettings(id=1, library_name="Test")
        db_session.add(settings)
        db_session.commit()

        result = settings_service.update_settings(
            db_session,
            {
                "library_name": "Valid",
                "invalid_field": "Should be ignored",
                "another_bad": 123,
            }
        )

        assert result.library_name == "Valid"
        assert not hasattr(result, "invalid_field")
        assert not hasattr(result, "another_bad")

    def test_update_empty_dict(self, db_session):
        """Test updating with empty dictionary."""
        settings = SystemSettings(id=1, library_name="Unchanged")
        db_session.add(settings)
        db_session.commit()

        result = settings_service.update_settings(db_session, {})

        assert result.library_name == "Unchanged"

    def test_update_not_found(self, db_session):
        """Test error when settings don't exist."""
        with pytest.raises(NotFoundError):
            settings_service.update_settings(db_session, {"library_name": "Test"})


class TestResetToDefaults:
    """Test reset_to_defaults function."""

    def test_reset_all_fields(self, db_session):
        """Test that all fields are reset to defaults."""
        # Create modified settings
        settings = SystemSettings(
            id=1,
            library_name="Custom Library",
            language="en",
            loan_duration_days=30,
            loan_limit_default=5,
            catalog_medium_types="CustomType1, CustomType2",
        )
        db_session.add(settings)
        db_session.commit()

        # Reset
        result = settings_service.reset_to_defaults(db_session)

        # Verify defaults
        assert result.library_name == "Bibliothèque que Claude a Développée"
        assert result.language == "fr"
        assert result.loan_duration_days == 14
        assert result.loan_limit_default == 2
        assert result.loan_limit_teacher == 5
        assert result.renewal_limit == 2
        assert result.catalog_medium_types == "Livre, Périodique, Audio, Vidéo, Jeu, Numérique, Autre"
        assert result.catalog_call_number_rules is not None

    def test_reset_persists(self, db_session):
        """Test that reset persists to database."""
        settings = SystemSettings(id=1, library_name="Custom")
        db_session.add(settings)
        db_session.commit()

        settings_service.reset_to_defaults(db_session)

        # Re-fetch from database
        refreshed = settings_service.get_settings(db_session)
        assert refreshed.library_name == "Bibliothèque que Claude a Développée"

    def test_reset_not_found(self, db_session):
        """Test error when settings don't exist."""
        with pytest.raises(NotFoundError):
            settings_service.reset_to_defaults(db_session)


class TestDefaultCallNumberRules:
    """Test default call number rules and the presence of `{SER1}` for Bandes dessinées."""

    def test_default_rules_use_ser1_for_comics(self, db_session):
        """Test that default call number rules have the BD rule with {SER1}."""
        settings = settings_service.initialize_default_settings(db_session)
        assert settings.catalog_call_number_rules is not None
        assert "BD {SER1}" in settings.catalog_call_number_rules
        assert "BD {AUT1}" not in settings.catalog_call_number_rules


class TestStructuredSettingsSerialization:
    """Test that structured settings are properly serialized and parsed."""

    def test_update_structured_fields(self, db_session):
        """Test updating dewey_colors, shelf_locations, and call_number_rules with structured Python objects."""
        from src.bcd_api.schemas.system_settings import SystemSettingsResponse

        # Create settings
        settings = SystemSettings(id=1)
        db_session.add(settings)
        db_session.commit()

        # Update with actual lists and dicts
        colors_list = ["#111111", "#222222"]
        shelves_list = [{"label": "Novel", "color": "#ff0000"}]
        rules_list = [{"medium_type": "Book", "shelf_location": "Novel", "pattern": "R {AUT3}"}]

        result = settings_service.update_settings(
            db_session,
            {
                "dewey_colors": colors_list,
                "catalog_shelf_locations": shelves_list,
                "catalog_call_number_rules": rules_list,
            }
        )

        # Assert database has them stored as JSON strings
        assert isinstance(result.dewey_colors, str)
        assert '"#111111"' in result.dewey_colors
        assert '"Novel"' in result.catalog_shelf_locations
        assert '"R {AUT3}"' in result.catalog_call_number_rules

        # Assert Pydantic Response Model parses them correctly as structured types
        response = SystemSettingsResponse.model_validate(result)
        assert response.dewey_colors == colors_list
        assert len(response.catalog_shelf_locations) == 1
        assert response.catalog_shelf_locations[0].label == "Novel"
        assert response.catalog_shelf_locations[0].color == "#ff0000"
        assert len(response.catalog_call_number_rules) == 1
        assert response.catalog_call_number_rules[0].medium_type == "Book"
        assert response.catalog_call_number_rules[0].pattern == "R {AUT3}"

