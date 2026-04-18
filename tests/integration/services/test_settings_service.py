"""Integration tests for settings service."""

import pytest

from src.bcd_api.services import settings_service
from src.bcd_api.core.exceptions import NotFoundError
from src.bcd_api.models.system_settings import SystemSettings


class TestGetSettings:
    """Test getting system settings."""

    def test_get_settings_success(self, db_session):
        """Test getting existing settings."""
        # Settings should already exist from fixture
        settings = settings_service.get_settings(db_session)

        assert settings is not None
        assert isinstance(settings, SystemSettings)
        assert settings.library_name is not None
        assert settings.language is not None

    def test_get_settings_not_found(self, db_session):
        """Test error when settings don't exist."""
        # Delete all settings
        db_session.query(SystemSettings).delete()
        db_session.commit()

        # Should raise NotFoundError
        with pytest.raises(NotFoundError, match="SystemSettings"):
            settings_service.get_settings(db_session)


class TestUpdateSettings:
    """Test updating system settings."""

    def test_update_settings_single_field(self, db_session):
        """Test updating a single setting."""
        # Update library name
        updates = {"library_name": "My New Library"}
        settings = settings_service.update_settings(db_session, updates)

        assert settings.library_name == "My New Library"

        # Verify it persisted
        db_session.refresh(settings)
        assert settings.library_name == "My New Library"

    def test_update_settings_multiple_fields(self, db_session):
        """Test updating multiple settings."""
        updates = {
            "library_name": "Test Library",
            "language": "en",
            "loan_duration_days": 21,
            "loan_limit_default": 3,
        }
        settings = settings_service.update_settings(db_session, updates)

        assert settings.library_name == "Test Library"
        assert settings.language == "en"
        assert settings.loan_duration_days == 21
        assert settings.loan_limit_default == 3

    def test_update_settings_loan_limits(self, db_session):
        """Test updating loan limits for different roles."""
        updates = {
            "loan_limit_default": 3,
            "loan_limit_teacher": 10,
        }
        settings = settings_service.update_settings(db_session, updates)

        assert settings.loan_limit_default == 3
        assert settings.loan_limit_teacher == 10

    def test_update_settings_duration_and_renewals(self, db_session):
        """Test updating loan duration and renewal settings."""
        updates = {
            "loan_duration_days": 28,
            "renewal_limit": 3,
        }
        settings = settings_service.update_settings(db_session, updates)

        assert settings.loan_duration_days == 28
        assert settings.renewal_limit == 3

    def test_update_settings_hold_expiration(self, db_session):
        """Test updating hold expiration days."""
        updates = {"hold_expiration_days": 5}
        settings = settings_service.update_settings(db_session, updates)

        assert settings.hold_expiration_days == 5

    def test_update_settings_barcode_type(self, db_session):
        """Test updating barcode type."""
        updates = {"barcode_type": "code128"}
        settings = settings_service.update_settings(db_session, updates)

        assert settings.barcode_type == "code128"

    def test_update_settings_id_format(self, db_session):
        """Test updating ID format and validation."""
        updates = {
            "id_format": "alphanumeric",
            "id_validation_regex": r"^[A-Z0-9]+$",
        }
        settings = settings_service.update_settings(db_session, updates)

        assert settings.id_format == "alphanumeric"
        assert settings.id_validation_regex == r"^[A-Z0-9]+$"

    def test_update_settings_academic_year(self, db_session):
        """Test updating academic year."""
        updates = {"academic_year_current": "2026-2027"}
        settings = settings_service.update_settings(db_session, updates)

        assert settings.academic_year_current == "2026-2027"

    def test_update_settings_ignores_invalid_fields(self, db_session):
        """Test that invalid fields are ignored."""
        # Get original settings
        original = settings_service.get_settings(db_session)
        original_name = original.library_name

        # Try to update with invalid field
        updates = {
            "library_name": "Valid Update",
            "invalid_field": "Should be ignored",
            "another_bad_field": 123,
        }
        settings = settings_service.update_settings(db_session, updates)

        # Valid field should be updated
        assert settings.library_name == "Valid Update"

        # Invalid fields should not exist or affect the object
        assert not hasattr(settings, "invalid_field")
        assert not hasattr(settings, "another_bad_field")

    def test_update_settings_empty_updates(self, db_session):
        """Test updating with empty dictionary."""
        original = settings_service.get_settings(db_session)
        original_name = original.library_name

        # Update with empty dict
        updates = {}
        settings = settings_service.update_settings(db_session, updates)

        # Nothing should change
        assert settings.library_name == original_name


class TestResetToDefaults:
    """Test resetting settings to defaults."""

    def test_reset_to_defaults(self, db_session):
        """Test resetting all settings to default values."""
        # First, modify some settings
        updates = {
            "library_name": "Modified Library",
            "language": "en",
            "loan_duration_days": 30,
            "loan_limit_default": 5,
        }
        settings_service.update_settings(db_session, updates)

        # Reset to defaults
        settings = settings_service.reset_to_defaults(db_session)

        # Verify all reset to defaults
        assert settings.library_name == "Bibliothèque que Claude a Développée"
        assert settings.language == "fr"
        assert settings.loan_duration_days == 14
        assert settings.loan_limit_default == 2
        assert settings.loan_limit_teacher == 5
        assert settings.renewal_limit == 2
        assert settings.hold_expiration_days == 3
        assert settings.barcode_type == "code39"
        assert settings.id_format == "numeric"
        assert settings.id_validation_regex == r"^\d+$"

    def test_reset_to_defaults_persists(self, db_session):
        """Test that reset persists to database."""
        # Modify settings
        updates = {"library_name": "Custom Library", "loan_duration_days": 30}
        settings_service.update_settings(db_session, updates)

        # Reset
        settings_service.reset_to_defaults(db_session)

        # Get fresh from database
        settings = settings_service.get_settings(db_session)

        assert settings.library_name == "Bibliothèque que Claude a Développée"
        assert settings.loan_duration_days == 14


class TestSettingsIntegrationScenarios:
    """Test complete settings management scenarios."""

    def test_complete_settings_workflow(self, db_session):
        """Test a complete workflow of getting, updating, and resetting settings."""
        # 1. Get initial settings
        initial = settings_service.get_settings(db_session)
        assert initial.library_name is not None

        # 2. Update for new school year
        updates = {
            "academic_year_current": "2026-2027",
            "loan_duration_days": 21,
            "loan_limit_default": 3,
        }
        updated = settings_service.update_settings(db_session, updates)
        assert updated.academic_year_current == "2026-2027"
        assert updated.loan_duration_days == 21

        # 3. Further adjustments
        more_updates = {
            "library_name": "École Primaire BCD",
            "hold_expiration_days": 5,
        }
        further_updated = settings_service.update_settings(db_session, more_updates)
        assert further_updated.library_name == "École Primaire BCD"
        assert further_updated.loan_duration_days == 21  # Previous update preserved

        # 4. Reset everything
        reset = settings_service.reset_to_defaults(db_session)
        assert reset.library_name == "Bibliothèque que Claude a Développée"
        assert reset.academic_year_current == "2025-2026"
        assert reset.loan_duration_days == 14

    def test_settings_for_different_library_types(self, db_session):
        """Test configuring settings for different library scenarios."""
        # Scenario 1: Small elementary school
        elementary_config = {
            "library_name": "École Élémentaire BCD",
            "loan_duration_days": 14,
            "loan_limit_default": 2,
            "loan_limit_teacher": 5,
            "renewal_limit": 2,
        }
        settings = settings_service.update_settings(db_session, elementary_config)
        assert settings.loan_limit_default == 2

        # Scenario 2: Larger middle school (more permissive)
        middle_school_config = {
            "library_name": "Collège BCD",
            "loan_duration_days": 21,
            "loan_limit_default": 3,
            "loan_limit_teacher": 10,
            "renewal_limit": 3,
        }
        settings = settings_service.update_settings(db_session, middle_school_config)
        assert settings.loan_limit_default == 3
        assert settings.loan_duration_days == 21

    def test_settings_barcode_configuration_workflow(self, db_session):
        """Test workflow for configuring barcode settings."""
        # Initial: Code 39 with numeric IDs
        initial = settings_service.get_settings(db_session)
        assert initial.barcode_type == "code39"
        assert initial.id_format == "numeric"

        # Switch to Code 128 with alphanumeric IDs
        updates = {
            "barcode_type": "code128",
            "id_format": "alphanumeric",
            "id_validation_regex": r"^[A-Z0-9]{1,10}$",
        }
        settings = settings_service.update_settings(db_session, updates)
        assert settings.barcode_type == "code128"
        assert settings.id_format == "alphanumeric"
        assert settings.id_validation_regex == r"^[A-Z0-9]{1,10}$"
