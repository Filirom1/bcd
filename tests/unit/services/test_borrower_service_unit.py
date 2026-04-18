"""Unit tests for borrower_service.py"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.bcd_api.services import borrower_service
from src.bcd_api.core.exceptions import (
    NotFoundError,
    DuplicateError,
    ValidationError,
)
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.system_settings import SystemSettings


class TestCreateBorrower:
    """Test create_borrower function."""

    def test_create_borrower_success(self, db_session):
        """Test successful borrower creation."""
        # Setup system settings
        settings = SystemSettings(
            id=1,
            id_format="numeric",
            id_validation_regex=r"^\d+$",
        )
        db_session.add(settings)
        db_session.commit()

        # Create borrower
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
        )

        assert borrower.borrower_id == "101"
        assert borrower.first_name == "Amira"
        assert borrower.last_name == "BENALI"
        assert borrower.full_name == "Amira BENALI"
        assert borrower.role == "student"
        assert borrower.barcode == "101"  # Barcode = borrower_id (frontend adds prefix)
        assert borrower.active is True

    def test_create_borrower_with_class(self, db_session):
        """Test borrower creation with class assignment."""
        # Setup
        settings = SystemSettings(id=1, id_format="numeric", id_validation_regex=r"^\d+$")
        db_session.add(settings)

        class_obj = Class(
            name="CP-A",
            homeroom_teacher="Mme Martin",
        )
        db_session.add(class_obj)
        db_session.commit()

        # Create borrower with class
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Lucas",
            last_name="DUBOIS",
            role="student",
            class_id=class_obj.id,
        )

        assert borrower.class_id == class_obj.id
        assert borrower.borrower_id == "102"

    def test_create_borrower_duplicate_id(self, db_session):
        """Test that duplicate borrower_id raises error."""
        settings = SystemSettings(id=1, id_format="numeric", id_validation_regex=r"^\d+$")
        db_session.add(settings)

        # Create first borrower
        borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
        )

        # Try to create duplicate
        with pytest.raises(DuplicateError) as exc_info:
            borrower_service.create_borrower(
                db=db_session,
                borrower_id="101",
                first_name="Lucas",
                last_name="DUBOIS",
                role="student",
            )

        assert "already exists" in str(exc_info.value.detail)

    def test_create_borrower_invalid_role(self, db_session):
        """Test that invalid role raises error."""
        settings = SystemSettings(id=1, id_format="numeric", id_validation_regex=r"^\d+$")
        db_session.add(settings)

        with pytest.raises(ValidationError) as exc_info:
            borrower_service.create_borrower(
                db=db_session,
                borrower_id="101",
                first_name="Amira",
                last_name="BENALI",
                role="invalid_role",
            )

        assert "Invalid role" in str(exc_info.value.detail)

    def test_create_borrower_invalid_id_format(self, db_session):
        """Test that invalid ID format raises error."""
        settings = SystemSettings(
            id=1,
            id_format="numeric",
            id_validation_regex=r"^\d+$",
        )
        db_session.add(settings)
        db_session.commit()

        with pytest.raises(ValidationError) as exc_info:
            borrower_service.create_borrower(
                db=db_session,
                borrower_id="ABC101",  # Alphanumeric ID when numeric required
                first_name="Amira",
                last_name="BENALI",
                role="student",
            )

        # Check for the actual error message format
        assert "Invalid borrower_id format" in str(exc_info.value.detail)

    def test_create_borrower_class_not_found(self, db_session):
        """Test that non-existent class_id raises error."""
        settings = SystemSettings(id=1, id_format="numeric", id_validation_regex=r"^\d+$")
        db_session.add(settings)
        db_session.commit()

        with pytest.raises(NotFoundError) as exc_info:
            borrower_service.create_borrower(
                db=db_session,
                borrower_id="101",
                first_name="Amira",
                last_name="BENALI",
                role="student",
                class_id=999,  # Non-existent class
            )

        assert "Class not found: 999" in str(exc_info.value.detail)

    def test_create_teacher_borrower(self, db_session):
        """Test creating a teacher borrower."""
        settings = SystemSettings(id=1, id_format="numeric", id_validation_regex=r"^\d+$")
        db_session.add(settings)
        db_session.commit()

        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="001",  # Use numeric ID for teachers too
            first_name="Marie",
            last_name="MARTIN",
            role="teacher",
            email="marie.martin@school.fr",
            phone="0123456789",
        )

        assert borrower.role == "teacher"
        assert borrower.class_id is None  # Teachers don't have a class
        assert borrower.email == "marie.martin@school.fr"
        assert borrower.phone == "0123456789"


class TestGetBorrowerById:
    """Test get_borrower_by_id function."""

    def test_get_borrower_success(self, db_session):
        """Test successful borrower retrieval."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        result = borrower_service.get_borrower_by_id(db_session, "101")

        assert result.borrower_id == "101"
        assert result.full_name == "Amira BENALI"

    def test_get_borrower_not_found(self, db_session):
        """Test that non-existent borrower raises error."""
        with pytest.raises(NotFoundError) as exc_info:
            borrower_service.get_borrower_by_id(db_session, "999")

        assert "Borrower not found: 999" in str(exc_info.value.detail)


class TestListBorrowers:
    """Test list_borrowers function."""

    def test_list_all_borrowers(self, db_session):
        """Test listing all borrowers."""
        # Create test borrowers
        for i in range(1, 6):
            borrower = Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                full_name=f"Student{i} LAST{i}",
                role="student",
                active=True,
            )
            db_session.add(borrower)
        db_session.commit()

        result, total = borrower_service.list_borrowers(db_session)

        assert len(result) == 5
        assert total == 5

    def test_list_borrowers_by_role(self, db_session):
        """Test filtering borrowers by role."""
        # Create students
        for i in range(1, 4):
            db_session.add(Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                full_name=f"Student{i} LAST{i}",
                role="student",
                active=True,
            ))

        # Create teachers
        for i in range(1, 3):
            db_session.add(Borrower(
                borrower_id=f"T00{i}",
                first_name=f"Teacher{i}",
                last_name=f"TEACH{i}",
                full_name=f"Teacher{i} TEACH{i}",
                role="teacher",
                active=True,
            ))
        db_session.commit()

        students, student_total = borrower_service.list_borrowers(db_session, role="student")
        teachers, teacher_total = borrower_service.list_borrowers(db_session, role="teacher")

        assert len(students) == 3
        assert student_total == 3
        assert len(teachers) == 2
        assert teacher_total == 2

    def test_list_borrowers_by_class(self, db_session):
        """Test filtering borrowers by class."""
        # Create class
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.commit()

        # Create borrowers in class
        for i in range(1, 4):
            db_session.add(Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                full_name=f"Student{i} LAST{i}",
                role="student",
                active=True,
                class_id=class_obj.id,
            ))

        # Create borrowers without class
        db_session.add(Borrower(
            borrower_id="104",
            first_name="Student4",
            last_name="LAST4",
            full_name="Student4 LAST4",
            role="student",
            active=True,
        ))
        db_session.commit()

        result, total = borrower_service.list_borrowers(db_session, class_id=class_obj.id)

        assert len(result) == 3
        assert total == 3

    def test_list_borrowers_active_filter(self, db_session):
        """Test filtering by active status."""
        # Create active borrowers
        for i in range(1, 4):
            db_session.add(Borrower(
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                full_name=f"Student{i} LAST{i}",
                role="student",
                active=True,
            ))

        # Create blocked borrower
        db_session.add(Borrower(
            borrower_id="104",
            first_name="Blocked",
            last_name="STUDENT",
            full_name="Blocked STUDENT",
            role="student",
            active=False,
            blocked_reason="Overdue items",
        ))
        db_session.commit()

        active, active_total = borrower_service.list_borrowers(db_session, active=True)
        blocked, blocked_total = borrower_service.list_borrowers(db_session, blocked=True)

        assert len(active) == 3
        assert active_total == 3
        assert len(blocked) == 1
        assert blocked_total == 1

    def test_list_borrowers_pagination(self, db_session):
        """Test pagination."""
        # Create 25 borrowers
        for i in range(1, 26):
            db_session.add(Borrower(
                borrower_id=f"{i:03d}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                full_name=f"Student{i} LAST{i}",
                role="student",
                active=True,
            ))
        db_session.commit()

        # First page
        page1, total1 = borrower_service.list_borrowers(db_session, limit=10, offset=0)
        # Second page
        page2, total2 = borrower_service.list_borrowers(db_session, limit=10, offset=10)

        assert len(page1) == 10
        assert total1 == 25
        assert len(page2) == 10
        assert total2 == 25
        assert page1[0].borrower_id != page2[0].borrower_id


class TestGetBorrowerDetails:
    """Test get_borrower_details function."""

    def test_get_borrower_details(self, db_session):
        """Test retrieving borrower details with statistics."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        details = borrower_service.get_borrower_details(db_session, "101")

        assert details["borrower"].borrower_id == "101"
        assert "current_loans_count" in details
        assert "total_checkouts" in details
        assert "overdue_count" in details
        assert details["current_loans_count"] == 0
        assert details["total_checkouts"] == 0
        assert details["overdue_count"] == 0


class TestUpdateBorrower:
    """Test update_borrower function."""

    def test_update_borrower_name(self, db_session):
        """Test updating borrower name."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Emma",
            last_name="BERNARD",
        )

        assert updated.first_name == "Emma"
        assert updated.last_name == "BERNARD"
        assert updated.full_name == "Emma BERNARD"

    def test_update_borrower_class(self, db_session):
        """Test updating borrower class."""
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)

        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            class_id=class_obj.id,
        )

        assert updated.class_id == class_obj.id

    def test_update_borrower_not_found(self, db_session):
        """Test updating non-existent borrower."""
        with pytest.raises(NotFoundError):
            borrower_service.update_borrower(
                db=db_session,
                borrower_id="999",
                first_name="Test",
            )


class TestBlockUnblockBorrower:
    """Test block_borrower and unblock_borrower functions."""

    def test_block_borrower(self, db_session):
        """Test blocking a borrower."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=True,
        )
        db_session.add(borrower)
        db_session.commit()

        blocked = borrower_service.block_borrower(
            db=db_session,
            borrower_id="101",
            reason="Overdue items - 3 books",
        )

        assert blocked.active is False
        assert blocked.blocked_reason == "Overdue items - 3 books"

    def test_unblock_borrower(self, db_session):
        """Test unblocking a borrower."""
        borrower = Borrower(
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            full_name="Amira BENALI",
            role="student",
            active=False,
            blocked_reason="Overdue items",
        )
        db_session.add(borrower)
        db_session.commit()

        unblocked = borrower_service.unblock_borrower(db_session, "101")

        assert unblocked.active is True
        assert unblocked.blocked_reason is None

    def test_block_not_found(self, db_session):
        """Test blocking non-existent borrower."""
        with pytest.raises(NotFoundError):
            borrower_service.block_borrower(db_session, "999", "Test reason")

    def test_unblock_not_found(self, db_session):
        """Test unblocking non-existent borrower."""
        with pytest.raises(NotFoundError):
            borrower_service.unblock_borrower(db_session, "999")
