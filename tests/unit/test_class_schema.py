"""Unit tests for Class Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.bcd_api.schemas.class_schema import ClassCreate, ClassUpdate, ClassResponse


class TestClassCreateValidation:
    """Tests for ClassCreate schema validation."""

    def test_class_create_valid_all_fields(self):
        """Test creating class schema with all fields."""
        # Arrange & Act
        data = {
            "name": "CP-A",
            "homeroom_teacher": "Mme. Dupont",
            "notes": "Classe de 24 élèves",
        }
        class_obj = ClassCreate(**data)

        # Assert
        assert class_obj.name == "CP-A"
        assert class_obj.homeroom_teacher == "Mme. Dupont"
        assert class_obj.notes == "Classe de 24 élèves"

    def test_class_create_valid_minimal_fields(self):
        """Test creating class schema with only required fields."""
        # Arrange & Act
        data = {"name": "CE1-B"}
        class_obj = ClassCreate(**data)

        # Assert
        assert class_obj.name == "CE1-B"
        assert class_obj.homeroom_teacher is None
        assert class_obj.notes is None

    def test_class_create_name_required(self):
        """Test that name is required."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ClassCreate()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["type"] == "missing"

    def test_class_create_name_empty_string(self):
        """Test that empty string name is rejected (min_length=1)."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ClassCreate(name="")

        errors = exc_info.value.errors()
        assert any(err["type"] == "string_too_short" for err in errors)

    def test_class_create_name_too_long(self):
        """Test that name exceeding max_length is rejected (max 50 chars)."""
        # Arrange
        long_name = "A" * 51

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ClassCreate(name=long_name)

        errors = exc_info.value.errors()
        assert any(err["type"] == "string_too_long" for err in errors)

    def test_class_create_name_exactly_max_length(self):
        """Test that name at exactly max_length is accepted."""
        # Arrange
        max_name = "A" * 50

        # Act
        class_obj = ClassCreate(name=max_name)

        # Assert
        assert class_obj.name == max_name

    def test_class_create_homeroom_teacher_too_long(self):
        """Test that homeroom_teacher exceeding max_length is rejected (max 100 chars)."""
        # Arrange
        long_teacher = "Mme. " + "A" * 100

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ClassCreate(name="CP-A", homeroom_teacher=long_teacher)

        errors = exc_info.value.errors()
        assert any(err["type"] == "string_too_long" for err in errors)

    def test_class_create_optional_fields_can_be_none(self):
        """Test that optional fields can be None."""
        # Arrange & Act
        class_obj = ClassCreate(
            name="CP-A",
            homeroom_teacher=None,
            notes=None,
        )

        # Assert
        assert class_obj.homeroom_teacher is None
        assert class_obj.notes is None


class TestClassUpdateValidation:
    """Tests for ClassUpdate schema validation."""

    def test_class_update_valid_all_fields(self):
        """Test updating class schema with all fields."""
        # Arrange & Act
        data = {
            "name": "CP-Bilingue",
            "homeroom_teacher": "Mme. Dubois",
            "notes": "Section bilingue",
        }
        update = ClassUpdate(**data)

        # Assert
        assert update.name == "CP-Bilingue"
        assert update.homeroom_teacher == "Mme. Dubois"
        assert update.notes == "Section bilingue"

    def test_class_update_all_fields_optional(self):
        """Test that all fields are optional in update schema."""
        # Arrange & Act
        update = ClassUpdate()

        # Assert
        assert update.name is None
        assert update.homeroom_teacher is None
        assert update.notes is None

    def test_class_update_partial_update(self):
        """Test updating only some fields."""
        # Arrange & Act
        update = ClassUpdate(homeroom_teacher="Mme. Martin")

        # Assert
        assert update.name is None
        assert update.homeroom_teacher == "Mme. Martin"
        assert update.notes is None

    def test_class_update_name_validation(self):
        """Test that name validation applies in update schema."""
        # Test empty string
        with pytest.raises(ValidationError):
            ClassUpdate(name="")

        # Test too long
        with pytest.raises(ValidationError):
            ClassUpdate(name="A" * 51)

        # Valid name
        update = ClassUpdate(name="CE1-A")
        assert update.name == "CE1-A"

    def test_class_update_homeroom_teacher_validation(self):
        """Test that homeroom_teacher validation applies in update schema."""
        # Test too long
        with pytest.raises(ValidationError):
            ClassUpdate(homeroom_teacher="Mme. " + "A" * 100)

        # Valid teacher
        update = ClassUpdate(homeroom_teacher="Mme. Dupont")
        assert update.homeroom_teacher == "Mme. Dupont"

    def test_class_update_notes_can_be_set_to_none(self):
        """Test that notes can be explicitly set to None."""
        # Arrange & Act
        update = ClassUpdate(notes=None)

        # Assert
        assert update.notes is None


class TestClassResponseValidation:
    """Tests for ClassResponse schema validation."""

    def test_class_response_includes_all_fields(self):
        """Test that response schema includes all required fields."""
        # Arrange
        data = {
            "id": 1,
            "name": "CP-A",
            "homeroom_teacher": "Mme. Dupont",
            "notes": "Classe de 24 élèves",
            "student_count": 24,
            "created_at": datetime(2026, 1, 30, 10, 0, 0),
            "updated_at": datetime(2026, 1, 30, 10, 0, 0),
        }

        # Act
        response = ClassResponse(**data)

        # Assert
        assert response.id == 1
        assert response.name == "CP-A"
        assert response.homeroom_teacher == "Mme. Dupont"
        assert response.notes == "Classe de 24 élèves"
        assert response.student_count == 24
        assert response.created_at == datetime(2026, 1, 30, 10, 0, 0)
        assert response.updated_at == datetime(2026, 1, 30, 10, 0, 0)

    def test_class_response_student_count_defaults_to_zero(self):
        """Test that student_count has a default value of 0."""
        # Arrange
        data = {
            "id": 1,
            "name": "CP-A",
            "homeroom_teacher": None,
            "notes": None,
            "created_at": datetime(2026, 1, 30, 10, 0, 0),
            "updated_at": datetime(2026, 1, 30, 10, 0, 0),
        }

        # Act
        response = ClassResponse(**data)

        # Assert
        assert response.student_count == 0

    def test_class_response_from_orm_model(self):
        """Test that response schema works with from_attributes (ORM mode)."""
        # Arrange
        from src.bcd_api.models.class_model import Class

        class_obj = Class(
            id=1,
            name="CP-A",
            homeroom_teacher="Mme. Dupont",
            notes="Test notes",
            student_count=15,
            created_at=datetime(2026, 1, 30, 10, 0, 0),
            updated_at=datetime(2026, 1, 30, 10, 0, 0),
        )

        # Act
        response = ClassResponse.model_validate(class_obj)

        # Assert
        assert response.id == 1
        assert response.name == "CP-A"
        assert response.homeroom_teacher == "Mme. Dupont"
        assert response.student_count == 15

    def test_class_response_optional_fields_can_be_none(self):
        """Test that optional fields can be None in response."""
        # Arrange
        data = {
            "id": 1,
            "name": "CP-A",
            "homeroom_teacher": None,
            "notes": None,
            "student_count": 0,
            "created_at": datetime(2026, 1, 30, 10, 0, 0),
            "updated_at": datetime(2026, 1, 30, 10, 0, 0),
        }

        # Act
        response = ClassResponse(**data)

        # Assert
        assert response.homeroom_teacher is None
        assert response.notes is None

    def test_class_response_id_required(self):
        """Test that id is required in response."""
        # Arrange
        data = {
            "name": "CP-A",
            "homeroom_teacher": None,
            "notes": None,
            "student_count": 0,
            "created_at": datetime(2026, 1, 30, 10, 0, 0),
            "updated_at": datetime(2026, 1, 30, 10, 0, 0),
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ClassResponse(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("id",) for err in errors)

    def test_class_response_timestamps_required(self):
        """Test that created_at and updated_at are required."""
        # Arrange
        data = {
            "id": 1,
            "name": "CP-A",
            "homeroom_teacher": None,
            "notes": None,
            "student_count": 0,
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ClassResponse(**data)

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "created_at" in missing_fields
        assert "updated_at" in missing_fields


class TestClassSchemaEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_class_create_with_unicode_characters(self):
        """Test that Unicode characters are handled correctly."""
        # Arrange & Act
        data = {
            "name": "CP-É",
            "homeroom_teacher": "Mme. Bérénice Müller",
            "notes": "Classe bilingue français/español",
        }
        class_obj = ClassCreate(**data)

        # Assert
        assert class_obj.name == "CP-É"
        assert class_obj.homeroom_teacher == "Mme. Bérénice Müller"
        assert class_obj.notes == "Classe bilingue français/español"

    def test_class_create_with_special_characters(self):
        """Test that special characters are handled correctly."""
        # Arrange & Act
        data = {
            "name": "CP-A/B",
            "homeroom_teacher": "M. O'Brien-Smith",
            "notes": "Note with special chars: &, @, #, $, %",
        }
        class_obj = ClassCreate(**data)

        # Assert
        assert class_obj.name == "CP-A/B"
        assert class_obj.homeroom_teacher == "M. O'Brien-Smith"

    def test_class_response_with_large_student_count(self):
        """Test that large student counts are handled correctly."""
        # Arrange
        data = {
            "id": 1,
            "name": "CP-A",
            "homeroom_teacher": None,
            "notes": None,
            "student_count": 1000,
            "created_at": datetime(2026, 1, 30, 10, 0, 0),
            "updated_at": datetime(2026, 1, 30, 10, 0, 0),
        }

        # Act
        response = ClassResponse(**data)

        # Assert
        assert response.student_count == 1000
