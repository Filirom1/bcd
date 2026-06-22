"""
Integration Tests for Borrower Edit Service
Tests User Story 4 from specs/006-admin-features/spec.md:
- Edit individual borrower details (name, ID, role, class)
- Validate borrower ID uniqueness
- Validate borrower ID format against system settings
- Update full_name automatically when first/last name changes
- Handle class reassignment with student count updates
"""

import pytest
from sqlalchemy.orm import Session

from src.bcd_api.core.exceptions import (
    DuplicateError,
)
from src.bcd_api.services import borrower_service
from src.shared.constants import BorrowerRole


class TestUpdateBorrowerBasicFields:
    """Test updating basic borrower fields (name, email, phone, notes)."""

    def test_update_borrower_first_name_updates_full_name(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Updating first name automatically updates full_name.

        Arrange: Create borrower "Jean Dupont"
        Act: Update first_name to "Pierre"
        Assert: full_name is "Pierre Dupont"
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont"
        )
        assert borrower.full_name == "Jean Dupont"

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Pierre"
        )

        # Assert
        assert updated.first_name == "Pierre"
        assert updated.last_name == "Dupont"
        assert updated.full_name == "Pierre Dupont"

    def test_update_borrower_last_name_updates_full_name(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Updating last name automatically updates full_name.

        Arrange: Create borrower "Jean Dupont"
        Act: Update last_name to "Martin"
        Assert: full_name is "Jean Martin"
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            last_name="Martin"
        )

        # Assert
        assert updated.first_name == "Jean"
        assert updated.last_name == "Martin"
        assert updated.full_name == "Jean Martin"

    def test_update_borrower_both_names_updates_full_name(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Updating both names automatically updates full_name.

        Arrange: Create borrower "Jean Dupont"
        Act: Update first_name to "Marie" and last_name to "Martin"
        Assert: full_name is "Marie Martin"
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Marie",
            last_name="Martin"
        )

        # Assert
        assert updated.first_name == "Marie"
        assert updated.last_name == "Martin"
        assert updated.full_name == "Marie Martin"

    def test_update_borrower_email_phone_notes(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Updating email, phone, and notes works correctly.

        Arrange: Create borrower with no contact info
        Act: Update email, phone, notes
        Assert: Fields updated correctly
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            email="jean.dupont@example.com",
            phone="0612345678",
            notes="Test notes"
        )

        # Assert
        assert updated.email == "jean.dupont@example.com"
        assert updated.phone == "0612345678"
        assert updated.notes == "Test notes"


class TestUpdateBorrowerID:
    """Test updating borrower ID with validation."""

    def test_update_borrower_id_to_unique_value_succeeds(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing borrower ID to a unique value succeeds.

        Arrange: Create borrower with ID "101"
        Act: Change borrower_id to "102"
        Assert: borrower_id is "102"
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            new_borrower_id="102"
        )

        # Assert
        assert updated.borrower_id == "102"
        # Verify we can retrieve by new ID
        retrieved = borrower_service.get_borrower_by_id(db_session, "102")
        assert retrieved.id == borrower.id

    def test_update_borrower_id_to_duplicate_value_fails(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing borrower ID to a duplicate value fails.

        Arrange: Create borrowers with IDs "101" and "102"
        Act: Try to change "101" to "102"
        Assert: DuplicateError raised with BORROWER_ID_NOT_AVAILABLE
        """
        # Arrange
        borrower1 = borrower_factory.create(borrower_id="101")
        borrower2 = borrower_factory.create(borrower_id="102")

        # Act & Assert
        with pytest.raises(DuplicateError) as exc_info:
            borrower_service.update_borrower(
                db=db_session,
                borrower_id="101",
                new_borrower_id="102"
            )

        assert "102" in str(exc_info.value)

    def test_update_borrower_id_to_invalid_format_fails(
        self,
        db_session: Session,
        borrower_factory,
        system_settings,
    ):
        """
        Changing borrower ID to invalid format fails.

        Arrange: Create borrower with valid ID "101"
        Act: Try to change to invalid format "ABC"
        Assert: ValidationError raised
        """
        from src.bcd_api.core.exceptions import InvalidIDFormatException

        # Arrange
        borrower = borrower_factory.create(borrower_id="101")

        # Act & Assert
        with pytest.raises(InvalidIDFormatException):
            borrower_service.update_borrower(
                db=db_session,
                borrower_id="101",
                new_borrower_id="ABC"
            )

    def test_update_borrower_id_to_same_value_succeeds(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing borrower ID to the same value succeeds (no-op).

        Arrange: Create borrower with ID "101"
        Act: Change borrower_id to "101" (same)
        Assert: No error, borrower_id unchanged
        """
        # Arrange
        borrower = borrower_factory.create(borrower_id="101")

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            new_borrower_id="101"
        )

        # Assert
        assert updated.borrower_id == "101"


class TestUpdateBorrowerRole:
    """Test updating borrower role."""

    def test_update_borrower_role_from_student_to_teacher(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing role from student to teacher succeeds.

        Arrange: Create student borrower
        Act: Change role to teacher
        Assert: Role is teacher
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            role="student"
        )
        assert borrower.role == BorrowerRole.STUDENT

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            role=BorrowerRole.TEACHER
        )

        # Assert
        assert updated.role == BorrowerRole.TEACHER

    def test_update_borrower_role_from_teacher_to_staff(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing role from teacher to staff succeeds.

        Arrange: Create teacher borrower
        Act: Change role to staff
        Assert: Role is staff
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            role="teacher"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            role=BorrowerRole.STAFF
        )

        # Assert
        assert updated.role == BorrowerRole.STAFF

    def test_update_borrower_role_to_invalid_value_fails(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing role to invalid value fails.

        Arrange: Create student borrower
        Act: Try to change role to "invalid"
        Assert: ValidationError raised
        """
        from src.bcd_api.core.exceptions import InvalidIDFormatException

        # Arrange
        borrower = borrower_factory.create(borrower_id="101")

        # Act & Assert
        with pytest.raises(InvalidIDFormatException):
            borrower_service.update_borrower(
                db=db_session,
                borrower_id="101",
                role="invalid_role"
            )


class TestUpdateBorrowerClass:
    """Test updating borrower class assignment."""

    def test_update_borrower_class_updates_student_count(
        self,
        db_session: Session,
        borrower_factory,
        class_factory,
    ):
        """
        Changing borrower class updates student counts.

        Arrange: Create 2 classes, create student in class 1
        Act: Change student to class 2
        Assert: Class 1 count decreases, class 2 count increases
        """
        # Arrange
        class1 = class_factory.create(name="CP-A")
        class2 = class_factory.create(name="CE1-A")
        borrower = borrower_factory.create(
            borrower_id="101",
            role="student",
            class_id=class1.id
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            class_id=class2.id
        )

        # Assert
        assert updated.class_id == class2.id

    def test_update_borrower_unassign_class_updates_student_count(
        self,
        db_session: Session,
        borrower_factory,
        class_factory,
    ):
        """
        Unassigning borrower from class updates student count.

        Arrange: Create class with 1 student
        Act: Set class_id to None
        Assert: Class student count decreases
        """
        # Arrange
        class1 = class_factory.create(name="CP-A")
        borrower = borrower_factory.create(
            borrower_id="101",
            role="student",
            class_id=class1.id
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            class_id=None
        )

        # Assert
        assert updated.class_id is None

    def test_update_borrower_class_to_nonexistent_fails(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Changing borrower to nonexistent class fails.

        Arrange: Create borrower
        Act: Try to assign to class_id=9999 (doesn't exist)
        Assert: NotFoundError raised
        """
        from src.bcd_api.core.exceptions import NotFoundException

        # Arrange
        borrower = borrower_factory.create(borrower_id="101")

        # Act & Assert
        with pytest.raises(NotFoundException):
            borrower_service.update_borrower(
                db=db_session,
                borrower_id="101",
                class_id=9999
            )

    def test_update_teacher_class_does_not_affect_student_count(
        self,
        db_session: Session,
        borrower_factory,
        class_factory,
    ):
        """
        Changing class for non-student does not affect student count.

        Arrange: Create teacher with class assignment
        Act: Change teacher's class
        Assert: Student counts unchanged
        """
        # Arrange
        class1 = class_factory.create(name="CP-A")
        class2 = class_factory.create(name="CE1-A")
        teacher = borrower_factory.create(
            borrower_id="T001",
            role="teacher",
            class_id=class1.id
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="T001",
            class_id=class2.id
        )

        # Assert
        assert updated.class_id == class2.id


class TestUpdateBorrowerNotFound:
    """Test error handling when borrower not found."""

    def test_update_nonexistent_borrower_fails(
        self,
        db_session: Session,
    ):
        """
        Updating nonexistent borrower fails.

        Arrange: No borrower exists
        Act: Try to update borrower_id="999"
        Assert: NotFoundError raised
        """
        from src.bcd_api.core.exceptions import BorrowerNotFoundException

        # Act & Assert
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.update_borrower(
                db=db_session,
                borrower_id="999",
                first_name="Test"
            )


class TestUpdateBorrowerCombinedChanges:
    """Test updating multiple fields simultaneously."""

    def test_update_borrower_multiple_fields_simultaneously(
        self,
        db_session: Session,
        borrower_factory,
        class_factory,
    ):
        """
        Updating multiple fields at once works correctly.

        Arrange: Create borrower
        Act: Update name, role, class, email, phone, notes all at once
        Assert: All fields updated correctly
        """
        # Arrange
        class1 = class_factory.create(name="CP-A")
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont",
            role="student"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Marie",
            last_name="Martin",
            role=BorrowerRole.TEACHER,
            class_id=class1.id,
            email="marie.martin@example.com",
            phone="0612345678",
            notes="Updated borrower"
        )

        # Assert
        assert updated.first_name == "Marie"
        assert updated.last_name == "Martin"
        assert updated.full_name == "Marie Martin"
        assert updated.role == BorrowerRole.TEACHER
        assert updated.class_id == class1.id
        assert updated.email == "marie.martin@example.com"
        assert updated.phone == "0612345678"
        assert updated.notes == "Updated borrower"

    def test_update_borrower_id_and_name_simultaneously(
        self,
        db_session: Session,
        borrower_factory,
    ):
        """
        Updating borrower_id and name simultaneously works.

        Arrange: Create borrower "101 Jean Dupont"
        Act: Change to "102 Marie Martin"
        Assert: Both ID and name updated, full_name correct
        """
        # Arrange
        borrower = borrower_factory.create(
            borrower_id="101",
            first_name="Jean",
            last_name="Dupont"
        )

        # Act
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            new_borrower_id="102",
            first_name="Marie",
            last_name="Martin"
        )

        # Assert
        assert updated.borrower_id == "102"
        assert updated.first_name == "Marie"
        assert updated.last_name == "Martin"
        assert updated.full_name == "Marie Martin"
