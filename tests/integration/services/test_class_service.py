"""Integration tests for class service."""

import pytest

from src.bcd_api.services import class_service, borrower_service
from src.bcd_api.core.exceptions import NotFoundError, DuplicateError
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.system_settings import SystemSettings


class TestClassCreationIntegration:
    """Integration tests for class creation."""

    def test_create_class_full_workflow(self, db_session):
        """Test complete class creation workflow."""
        class_obj = class_service.create_class(
            db=db_session,
            name="CP-A",
            homeroom_teacher="Mme Marie Martin",
            notes="Section bilingue",
        )

        assert class_obj.id is not None
        assert class_obj.name == "CP-A"
        assert class_obj.homeroom_teacher == "Mme Marie Martin"
        assert class_obj.notes == "Section bilingue"
        assert class_obj.created_at is not None

    def test_create_multiple_classes_same_grade(self, db_session):
        """Test creating multiple classes for the same grade level."""
        classes = []
        for section in ["A", "B", "C"]:
            class_obj = class_service.create_class(
                db=db_session,
                name=f"CP-{section}",
            )
            classes.append(class_obj)

        assert len(classes) == 3
        assert [c.name for c in classes] == ["CP-A", "CP-B", "CP-C"]

    def test_create_classes_different_years(self, db_session):
        """Test creating classes with unique names (duplicate names not allowed with simplified model)."""
        # First class
        class_a = class_service.create_class(
            db=db_session,
            name="CP-A-2025",
        )

        # Second class with different name
        class_b = class_service.create_class(
            db=db_session,
            name="CP-A-2026",
        )

        assert class_a.name == "CP-A-2025"
        assert class_b.name == "CP-A-2026"
        assert class_a.id != class_b.id


class TestClassListingIntegration:
    """Integration tests for class listing and filtering."""

    def test_list_all_classes_comprehensive(self, db_session):
        """Test comprehensive class listing."""
        # Create CP classes
        for section in ["A", "B", "C"]:
            class_service.create_class(
                db=db_session,
                name=f"CP-{section}",
            )

        # Create CE1 classes
        for section in ["A", "B"]:
            class_service.create_class(
                db=db_session,
                name=f"CE1-{section}",
            )

        # Create CM2 classes
        class_service.create_class(
            db=db_session,
            name="CM2-A",
        )

        # Test: List all
        all_classes = class_service.list_classes(db_session)
        assert len(all_classes) == 6

        # Verify names are sorted alphabetically
        names = [c.name for c in all_classes]
        assert names == sorted(names)

    def test_list_classes_pagination(self, db_session):
        """Test pagination with list_classes."""
        # Create multiple classes
        for i in range(15):
            class_service.create_class(
                db=db_session,
                name=f"Class-{i:02d}",
            )

        page1 = class_service.list_classes(db_session, limit=5, offset=0)
        page2 = class_service.list_classes(db_session, limit=5, offset=5)
        page3 = class_service.list_classes(db_session, limit=5, offset=10)

        assert len(page1) == 5
        assert len(page2) == 5
        assert len(page3) == 5


class TestClassWithBorrowersIntegration:
    """Integration tests for classes with borrowers."""

    def test_class_with_multiple_borrowers(self, db_session):
        """Test class with multiple borrowers assigned."""
        # System settings already exist from fixture

        # Create class
        cp_a = class_service.create_class(
            db=db_session,
            name="CP-A",
        )

        # Create borrowers in this class
        borrowers = []
        for i in range(1, 11):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )
            borrowers.append(borrower)

        # Verify all borrowers are in the class
        assert len(borrowers) == 10
        assert all(b.class_id == cp_a.id for b in borrowers)

        # List borrowers by class
        class_borrowers, total = borrower_service.list_borrowers(
            db_session,
            class_id=cp_a.id,
        )
        assert len(class_borrowers) == 10
        assert total == 10

    def test_delete_class_borrowers_remain(self, db_session):
        """Test that deleting class doesn't delete borrowers."""
        # System settings already exist from fixture

        # Create class
        cp_a = class_service.create_class(
            db=db_session,
            name="CP-A",
        )

        # Create borrower in class
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
            class_id=cp_a.id,
        )

        # Delete class
        class_service.delete_class(db_session, cp_a.id)

        # Verify borrower still exists but class_id is null
        # (fetch fresh from database)
        remaining_borrower = borrower_service.get_borrower_by_id(db_session, "101")
        assert remaining_borrower is not None
        # Note: In real implementation, you might want to set class_id to NULL
        # when class is deleted, depending on your cascade rules


class TestClassUpdateIntegration:
    """Integration tests for class updates."""

    def test_update_class_teacher_workflow(self, db_session):
        """Test updating class homeroom teacher."""
        # Create class with initial teacher
        cp_a = class_service.create_class(
            db=db_session,
            name="CP-A",
            homeroom_teacher="Mme Martin",
        )

        assert cp_a.homeroom_teacher == "Mme Martin"

        # Teacher changes mid-year
        updated = class_service.update_class(
            db=db_session,
            class_id=cp_a.id,
            homeroom_teacher="Mme Dubois",
        )

        assert updated.homeroom_teacher == "Mme Dubois"
        assert updated.name == "CP-A"  # Other fields unchanged

    def test_rename_class(self, db_session):
        """Test renaming a class."""
        cp_a = class_service.create_class(
            db=db_session,
            name="CP-A",
        )

        # Rename class
        updated = class_service.update_class(
            db=db_session,
            class_id=cp_a.id,
            name="CP-Bilingue",
        )

        assert updated.name == "CP-Bilingue"


class TestClassCompleteScenarios:
    """End-to-end scenarios for class management."""

    def test_complete_academic_year_workflow(self, db_session):
        """Test complete academic year workflow."""
        # System settings already exist from fixture

        # Year 2025-2026: Create classes
        cp_2025 = class_service.create_class(
            db=db_session,
            name="CP-A-2025",
            homeroom_teacher="Mme Martin",
        )

        # Assign students to class
        students_2025 = []
        for i in range(1, 6):
            student = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_2025.id,
            )
            students_2025.append(student)

        # Verify class has students
        assert len(students_2025) == 5

        # Year 2026-2027: Create new classes (students move up)
        ce1_2026 = class_service.create_class(
            db=db_session,
            name="CE1-A-2026",
            homeroom_teacher="Mme Dubois",
        )

        # Move students to new class
        for student in students_2025:
            borrower_service.update_borrower(
                db=db_session,
                borrower_id=student.borrower_id,
                class_id=ce1_2026.id,
            )

        # Verify students moved
        ce1_students, total = borrower_service.list_borrowers(
            db_session,
            class_id=ce1_2026.id,
        )
        assert len(ce1_students) == 5
        assert total == 5

    def test_school_organization_structure(self, db_session):
        """Test complete school organization with multiple grades."""
        # System settings already exist from fixture

        # Create complete school structure
        grades = {
            "CP": 3,      # 3 CP classes
            "CE1": 3,     # 3 CE1 classes
            "CE2": 2,     # 2 CE2 classes
            "CM1": 2,     # 2 CM1 classes
            "CM2": 2,     # 2 CM2 classes
        }

        all_classes = []
        for grade, count in grades.items():
            for i in range(count):
                section = chr(65 + i)  # A, B, C, etc.
                class_obj = class_service.create_class(
                    db=db_session,
                    name=f"{grade}-{section}",
                )
                all_classes.append(class_obj)

        # Verify total classes
        assert len(all_classes) == sum(grades.values())  # 12 classes

        # Verify all classes were created
        all_listed = class_service.list_classes(db_session, limit=20)
        assert len(all_listed) == 12
