"""Unit tests for settings_service.py"""

import pytest

from src.bcd_api.services import settings_service
from src.bcd_api.core.exceptions import NotFoundError
from src.bcd_api.models.system_settings import SystemSettings


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
            catalog_genres="CustomGenre1, CustomGenre2",
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
        assert result.catalog_genres == "Album, Roman, Conte, Poésie, Théâtre, Bande dessinée, Manga, Documentaire, Autre"

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
