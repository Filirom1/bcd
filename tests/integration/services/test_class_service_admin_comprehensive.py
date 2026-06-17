"""
Comprehensive integration tests for class service admin operations (User Story 2).

Tests cover CRUD operations, delete with unassignment, and student_count denormalized counter.
"""

import pytest
from sqlalchemy import func

from src.bcd_api.services import class_service, borrower_service
from src.bcd_api.core.exceptions import (
    ClassNotFoundException,
    NotFoundException,
    DuplicateError,
)
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.borrower import Borrower


class TestClassCRUDOperations:
    """Integration tests for Class CRUD operations."""

    def test_create_class_success(self, db_session):
        """Test successful class creation with all fields."""
        # Arrange & Act
        class_obj = class_service.create_class(
            db=db_session,
            name="CP-A",
            homeroom_teacher="Mme. Dupont",
            notes="Classe de 24 élèves",
        )

        # Assert
        assert class_obj.id is not None
        assert class_obj.name == "CP-A"
        assert class_obj.homeroom_teacher == "Mme. Dupont"
        assert class_obj.notes == "Classe de 24 élèves"
        assert class_obj.created_at is not None
        assert class_obj.updated_at is not None

    def test_create_class_minimal_fields(self, db_session):
        """Test class creation with minimal required fields."""
        # Arrange & Act
        class_obj = class_service.create_class(
            db=db_session,
            name="CE1-B",
        )

        # Assert
        assert class_obj.name == "CE1-B"
        assert class_obj.homeroom_teacher is None
        assert class_obj.notes is None

    def test_create_class_duplicate_name(self, db_session):
        """Test that creating a class with duplicate name fails."""
        # Arrange
        class_service.create_class(db=db_session, name="CP-A")

        # Act & Assert
        with pytest.raises(DuplicateError) as exc_info:
            class_service.create_class(db=db_session, name="CP-A")

        assert "already exists" in str(exc_info.value.detail)

    def test_get_class_by_id_success(self, db_session):
        """Test successful retrieval of class by ID."""
        # Arrange
        created = class_service.create_class(db=db_session, name="CP-A")

        # Act
        result = class_service.get_class_by_id(db_session, created.id)

        # Assert
        assert result.id == created.id
        assert result.name == "CP-A"

    def test_get_class_by_id_not_found(self, db_session):
        """Test that retrieving non-existent class raises NotFoundException."""
        # Act & Assert
        with pytest.raises(NotFoundException) as exc_info:
            class_service.get_class_by_id(db_session, 99999)

        assert "Class not found: 99999" in str(exc_info.value.detail)

    def test_get_class_by_name_success(self, db_session):
        """Test successful retrieval of class by name."""
        # Arrange
        class_service.create_class(db=db_session, name="CP-A")

        # Act
        result = class_service.get_class_by_name(db_session, "CP-A")

        # Assert
        assert result is not None
        assert result.name == "CP-A"

    def test_get_class_by_name_not_found(self, db_session):
        """Test that retrieving non-existent class by name returns None."""
        # Act
        result = class_service.get_class_by_name(db_session, "NonExistent")

        # Assert
        assert result is None

    def test_update_class_success(self, db_session):
        """Test successful class update."""
        # Arrange
        class_obj = class_service.create_class(
            db=db_session,
            name="CP-A",
            homeroom_teacher="Mme. Martin",
        )

        # Act
        updated = class_service.update_class(
            db=db_session,
            class_id=class_obj.id,
            name="CP-Bilingue",
            homeroom_teacher="Mme. Dubois",
            notes="Section bilingue",
        )

        # Assert
        assert updated.name == "CP-Bilingue"
        assert updated.homeroom_teacher == "Mme. Dubois"
        assert updated.notes == "Section bilingue"

    def test_update_class_partial_update(self, db_session):
        """Test updating only some fields."""
        # Arrange
        class_obj = class_service.create_class(
            db=db_session,
            name="CP-A",
            homeroom_teacher="Mme. Martin",
            notes="Original notes",
        )

        # Act - Only update homeroom teacher
        updated = class_service.update_class(
            db=db_session,
            class_id=class_obj.id,
            homeroom_teacher="Mme. Dubois",
        )

        # Assert - Name and notes unchanged
        assert updated.name == "CP-A"
        assert updated.homeroom_teacher == "Mme. Dubois"
        assert updated.notes == "Original notes"

    def test_update_class_not_found(self, db_session):
        """Test that updating non-existent class raises NotFoundException."""
        # Act & Assert
        with pytest.raises(NotFoundException):
            class_service.update_class(
                db=db_session,
                class_id=99999,
                name="Test",
            )

    def test_update_class_duplicate_name(self, db_session):
        """Test that updating to duplicate name fails."""
        # Arrange
        class_a = class_service.create_class(db=db_session, name="CP-A")
        class_b = class_service.create_class(db=db_session, name="CP-B")

        # Act & Assert
        with pytest.raises(DuplicateError):
            class_service.update_class(
                db=db_session,
                class_id=class_b.id,
                name="CP-A",  # Duplicate name
            )

    def test_list_classes_empty(self, db_session):
        """Test listing classes when none exist."""
        # Act
        classes = class_service.list_classes(db_session)

        # Assert
        assert classes == []

    def test_list_classes_multiple(self, db_session):
        """Test listing multiple classes."""
        # Arrange
        for i, name in enumerate(["CP-A", "CP-B", "CE1-A", "CE1-B", "CM2-A"]):
            class_service.create_class(db=db_session, name=name)

        # Act
        classes = class_service.list_classes(db_session)

        # Assert
        assert len(classes) == 5
        # Classes should be ordered by name
        assert classes[0].name == "CE1-A"
        assert classes[4].name == "CP-B"

    def test_list_classes_pagination(self, db_session):
        """Test class listing pagination."""
        # Arrange - Create 25 classes
        for i in range(25):
            class_service.create_class(db=db_session, name=f"Class-{i:02d}")

        # Act
        page1 = class_service.list_classes(db_session, limit=10, offset=0)
        page2 = class_service.list_classes(db_session, limit=10, offset=10)
        page3 = class_service.list_classes(db_session, limit=10, offset=20)

        # Assert
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5
        # Verify different results
        assert page1[0].name != page2[0].name


class TestDeleteClassWithUnassignment:
    """Integration tests for delete_class_with_unassignment service method."""

    def test_delete_class_with_unassignment_no_students(self, db_session):
        """Test deleting a class with no students (clean delete)."""
        # Arrange
        class_obj = class_service.create_class(db=db_session, name="CP-A")
        class_id = class_obj.id

        # Act
        class_service.delete_class_with_unassignment(db_session, class_id)

        # Assert - Class is deleted
        result = db_session.query(Class).filter(Class.id == class_id).first()
        assert result is None

    def test_delete_class_with_unassignment_with_students(self, db_session):
        """Test deleting a class with students unassigns them first."""
        # Arrange - Create class and students
        class_obj = class_service.create_class(db=db_session, name="CP-A")

        student1 = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Alice",
            last_name="BENALI",
            role="student",
            class_id=class_obj.id,
        )

        student2 = borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Bob",
            last_name="MARTIN",
            role="student",
            class_id=class_obj.id,
        )

        # Verify students are assigned
        assert student1.class_id == class_obj.id
        assert student2.class_id == class_obj.id

        # Act
        class_service.delete_class_with_unassignment(db_session, class_obj.id)

        # Assert - Class is deleted
        result = db_session.query(Class).filter(Class.id == class_obj.id).first()
        assert result is None

        # Assert - Students still exist but are unassigned
        student1_updated = borrower_service.get_borrower_by_id(db_session, "101")
        student2_updated = borrower_service.get_borrower_by_id(db_session, "102")

        assert student1_updated is not None
        assert student1_updated.class_id is None
        assert student2_updated is not None
        assert student2_updated.class_id is None

    def test_delete_class_with_unassignment_not_found(self, db_session):
        """Test deleting non-existent class raises ClassNotFoundException."""
        # Act & Assert
        with pytest.raises(ClassNotFoundException) as exc_info:
            class_service.delete_class_with_unassignment(db_session, 99999)

        assert exc_info.value.context["class_id"] == 99999
        assert exc_info.value.error_code == "CLASS_NOT_FOUND"


class TestStudentCountDenormalizedCounter:
    """Integration tests for student count via live query (formerly denormalized)."""

    def _count_students(self, db, class_id):
        return (
            db.query(func.count(Borrower.id))
            .filter(Borrower.class_id == class_id, Borrower.role == "student")
            .scalar()
        )

    def test_student_count_increments_on_class_assignment(self, db_session):
        """Test that student count increments when students are assigned to class."""
        class_obj = class_service.create_class(db=db_session, name="CP-A")
        assert self._count_students(db_session, class_obj.id) == 0

        borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Alice",
            last_name="BENALI",
            role="student",
            class_id=class_obj.id,
        )
        assert self._count_students(db_session, class_obj.id) == 1

        borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Bob",
            last_name="MARTIN",
            role="student",
            class_id=class_obj.id,
        )
        assert self._count_students(db_session, class_obj.id) == 2

    def test_student_count_decrements_on_class_unassignment(self, db_session):
        """Test that student count decrements when students are unassigned."""
        class_obj = class_service.create_class(db=db_session, name="CP-A")

        borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Alice",
            last_name="BENALI",
            role="student",
            class_id=class_obj.id,
        )
        borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Bob",
            last_name="MARTIN",
            role="student",
            class_id=class_obj.id,
        )
        assert self._count_students(db_session, class_obj.id) == 2

        borrower_service.update_borrower(db=db_session, borrower_id="101", class_id=None)
        assert self._count_students(db_session, class_obj.id) == 1

        borrower_service.update_borrower(db=db_session, borrower_id="102", class_id=None)
        assert self._count_students(db_session, class_obj.id) == 0

    def test_student_count_updates_on_class_change(self, db_session):
        """Test that student count updates correctly when students move between classes."""
        class_a = class_service.create_class(db=db_session, name="CP-A")
        class_b = class_service.create_class(db=db_session, name="CP-B")

        borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Alice",
            last_name="BENALI",
            role="student",
            class_id=class_a.id,
        )
        assert self._count_students(db_session, class_a.id) == 1
        assert self._count_students(db_session, class_b.id) == 0

        borrower_service.update_borrower(db=db_session, borrower_id="101", class_id=class_b.id)
        assert self._count_students(db_session, class_a.id) == 0
        assert self._count_students(db_session, class_b.id) == 1

    def test_student_count_only_counts_students_not_teachers(self, db_session):
        """Test that student count only counts role='student', not teachers/staff."""
        class_obj = class_service.create_class(db=db_session, name="CP-A")

        borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Alice",
            last_name="BENALI",
            role="student",
            class_id=class_obj.id,
        )
        borrower_service.create_borrower(
            db=db_session,
            borrower_id="999",
            first_name="Marie",
            last_name="MARTIN",
            role="teacher",
            class_id=class_obj.id,
        )
        assert self._count_students(db_session, class_obj.id) == 1

    def test_student_count_resets_to_zero_on_delete_with_unassignment(self, db_session):
        """Test that students are unassigned when class is deleted."""
        class_obj = class_service.create_class(db=db_session, name="CP-A")
        class_id = class_obj.id

        borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Alice",
            last_name="BENALI",
            role="student",
            class_id=class_id,
        )
        borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Bob",
            last_name="MARTIN",
            role="student",
            class_id=class_id,
        )
        assert self._count_students(db_session, class_id) == 2

        class_service.delete_class_with_unassignment(db_session, class_id)

        result = db_session.query(Class).filter(Class.id == class_id).first()
        assert result is None

        student1 = borrower_service.get_borrower_by_id(db_session, "101")
        student2 = borrower_service.get_borrower_by_id(db_session, "102")
        assert student1.class_id is None
        assert student2.class_id is None

    def test_student_count_multiple_class_assignments(self, db_session):
        """Test student count with complex scenario of multiple assignments."""
        class_a = class_service.create_class(db=db_session, name="CP-A")
        class_b = class_service.create_class(db=db_session, name="CP-B")
        class_c = class_service.create_class(db=db_session, name="CE1-A")

        for i in range(1, 6):
            borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"TEST{i}",
                role="student",
                class_id=class_a.id,
            )
        for i in range(6, 9):
            borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"TEST{i}",
                role="student",
                class_id=class_b.id,
            )

        assert self._count_students(db_session, class_a.id) == 5
        assert self._count_students(db_session, class_b.id) == 3
        assert self._count_students(db_session, class_c.id) == 0

        borrower_service.update_borrower(db=db_session, borrower_id="101", class_id=class_c.id)
        borrower_service.update_borrower(db=db_session, borrower_id="102", class_id=class_c.id)

        assert self._count_students(db_session, class_a.id) == 3
        assert self._count_students(db_session, class_b.id) == 3
        assert self._count_students(db_session, class_c.id) == 2

        borrower_service.update_borrower(db=db_session, borrower_id="106", class_id=None)

        assert self._count_students(db_session, class_a.id) == 3
        assert self._count_students(db_session, class_b.id) == 2
        assert self._count_students(db_session, class_c.id) == 2
