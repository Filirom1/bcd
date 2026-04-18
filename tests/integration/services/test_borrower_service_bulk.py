"""Integration tests for bulk borrower operations.

This module tests bulk operations on borrowers:
- bulk_change_class: Change class for multiple borrowers
- bulk_change_role: Change role for multiple borrowers
- bulk_delete_borrowers: Delete multiple borrowers

All operations must be atomic (all succeed or all fail with rollback).
"""

import pytest
from datetime import datetime, timedelta
import json

from src.bcd_api.services import borrower_service
from src.bcd_api.core.exceptions import (
    ClassNotFoundException,
    BorrowerNotFoundException,
    BorrowerHasActiveLoansException,
    ValidationError,
)
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.circulation import CirculationTransaction


class TestBulkChangeClass:
    """Integration tests for bulk_change_class operation."""

    def test_bulk_change_class_success(self, db_session):
        """Test successful bulk class change for multiple borrowers."""
        # Arrange: Create classes
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        ce1_a = Class(name="CE1-A", homeroom_teacher="Mme Dupont")
        db_session.add_all([cp_a, ce1_a])
        db_session.commit()

        # Create borrowers in CP-A
        borrower_ids = []
        for i in range(1, 6):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )
            borrower_ids.append(borrower.borrower_id)

        # Verify initial student counts
        db_session.refresh(cp_a)
        db_session.refresh(ce1_a)
        assert cp_a.student_count == 5
        assert ce1_a.student_count == 0

        # Act: Bulk change class from CP-A to CE1-A
        result = borrower_service.bulk_change_class(
            db=db_session,
            borrower_ids=borrower_ids,
            new_class_id=ce1_a.id
        )

        # Assert: Verify all borrowers moved
        assert result["total_count"] == 5
        assert result["successful_count"] == 5
        assert result["failed_count"] == 0

        # Verify borrowers have new class
        for borrower_id in borrower_ids:
            borrower = borrower_service.get_borrower_by_id(db_session, borrower_id)
            assert borrower.class_id == ce1_a.id

        # Verify student counts updated correctly
        db_session.refresh(cp_a)
        db_session.refresh(ce1_a)
        assert cp_a.student_count == 0
        assert ce1_a.student_count == 5

    def test_bulk_change_class_unassign_from_class(self, db_session):
        """Test bulk change class to None (unassign from class)."""
        # Arrange: Create class and borrowers
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        db_session.add(cp_a)
        db_session.commit()

        borrower_ids = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )
            borrower_ids.append(borrower.borrower_id)

        db_session.refresh(cp_a)
        assert cp_a.student_count == 3

        # Act: Unassign all from class (set to None)
        result = borrower_service.bulk_change_class(
            db=db_session,
            borrower_ids=borrower_ids,
            new_class_id=None
        )

        # Assert: All borrowers unassigned
        assert result["successful_count"] == 3
        for borrower_id in borrower_ids:
            borrower = borrower_service.get_borrower_by_id(db_session, borrower_id)
            assert borrower.class_id is None

        # Student count decremented
        db_session.refresh(cp_a)
        assert cp_a.student_count == 0

    def test_bulk_change_class_invalid_class_id_rolls_back(self, db_session):
        """Test that invalid class ID causes rollback of entire operation."""
        # Arrange: Create valid class and borrowers
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        db_session.add(cp_a)
        db_session.commit()

        borrower_ids = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )
            borrower_ids.append(borrower.borrower_id)

        # Act & Assert: Try to change to non-existent class
        with pytest.raises(ClassNotFoundException):
            borrower_service.bulk_change_class(
                db=db_session,
                borrower_ids=borrower_ids,
                new_class_id=99999  # Non-existent class
            )

        # Verify NO changes were made (transaction rolled back)
        # After exception, test transaction rollback will restore state
        for borrower_id in borrower_ids:
            borrower = db_session.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
            assert borrower is not None
            assert borrower.class_id == cp_a.id  # Still in original class

        # Re-fetch class from db
        cp_a_refreshed = db_session.query(Class).filter(Class.id == cp_a.id).first()
        assert cp_a_refreshed.student_count == 3  # Count unchanged

    def test_bulk_change_class_invalid_borrower_id_rolls_back(self, db_session):
        """Test that one invalid borrower ID causes rollback of entire operation."""
        # Arrange
        ce1_a = Class(name="CE1-A", homeroom_teacher="Mme Dupont")
        db_session.add(ce1_a)
        db_session.commit()

        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Valid",
            last_name="STUDENT",
            role="student",
        )
        original_class_id = borrower.class_id

        # Act & Assert: Include one invalid borrower ID
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.bulk_change_class(
                db=db_session,
                borrower_ids=["101", "999"],  # 999 doesn't exist
                new_class_id=ce1_a.id
            )

        # Verify NO changes were made (re-fetch from db)
        borrower_refreshed = db_session.query(Borrower).filter(Borrower.borrower_id == "101").first()
        assert borrower_refreshed is not None
        assert borrower_refreshed.class_id == original_class_id  # Unchanged

    def test_bulk_change_class_only_affects_students(self, db_session):
        """Test that class changes only affect student role borrowers."""
        # Arrange: Create class
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        db_session.add(cp_a)
        db_session.commit()

        # Create student
        student = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ONE",
            role="student",
        )

        # Create teacher (teachers don't affect student_count)
        teacher = borrower_service.create_borrower(
            db=db_session,
            borrower_id="201",
            first_name="Teacher",
            last_name="ONE",
            role="teacher",
        )

        # Act: Bulk change class for both
        result = borrower_service.bulk_change_class(
            db=db_session,
            borrower_ids=["101", "201"],
            new_class_id=cp_a.id
        )

        # Assert: Both assigned but only student affects count
        assert result["successful_count"] == 2
        db_session.refresh(student)
        db_session.refresh(teacher)
        assert student.class_id == cp_a.id
        assert teacher.class_id == cp_a.id

        db_session.refresh(cp_a)
        assert cp_a.student_count == 1  # Only student counted


class TestBulkChangeRole:
    """Integration tests for bulk_change_role operation."""

    def test_bulk_change_role_success(self, db_session):
        """Test successful bulk role change for multiple borrowers."""
        # Arrange: Create borrowers
        borrower_ids = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"User{i}",
                last_name=f"LAST{i}",
                role="student",
            )
            borrower_ids.append(borrower.borrower_id)

        # Act: Change all to staff
        result = borrower_service.bulk_change_role(
            db=db_session,
            borrower_ids=borrower_ids,
            new_role="staff"
        )

        # Assert: All roles changed
        assert result["total_count"] == 3
        assert result["successful_count"] == 3
        assert result["failed_count"] == 0

        for borrower_id in borrower_ids:
            borrower = borrower_service.get_borrower_by_id(db_session, borrower_id)
            assert borrower.role == "staff"

    def test_bulk_change_role_invalid_role_raises_error(self, db_session):
        """Test that invalid role value raises ValidationError."""
        # Arrange
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ONE",
            role="student",
        )

        # Act & Assert: Invalid role
        with pytest.raises(ValidationError):
            borrower_service.bulk_change_role(
                db=db_session,
                borrower_ids=["101"],
                new_role="invalid_role"
            )

        # Verify no changes (re-fetch from db)
        borrower_refreshed = db_session.query(Borrower).filter(Borrower.borrower_id == "101").first()
        assert borrower_refreshed is not None
        assert borrower_refreshed.role == "student"

    def test_bulk_change_role_student_to_teacher_with_class_assignment(self, db_session):
        """Test changing student to teacher maintains class assignment but affects count."""
        # Arrange: Create class and student
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        db_session.add(cp_a)
        db_session.commit()

        student = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ONE",
            role="student",
            class_id=cp_a.id,
        )

        db_session.refresh(cp_a)
        assert cp_a.student_count == 1

        # Act: Change to teacher
        result = borrower_service.bulk_change_role(
            db=db_session,
            borrower_ids=["101"],
            new_role="teacher"
        )

        # Assert: Role changed, class maintained, count updated
        assert result["successful_count"] == 1
        db_session.refresh(student)
        assert student.role == "teacher"
        assert student.class_id == cp_a.id  # Class preserved

        db_session.refresh(cp_a)
        assert cp_a.student_count == 0  # Count decremented (no longer student)

    def test_bulk_change_role_invalid_borrower_rolls_back(self, db_session):
        """Test that one invalid borrower causes rollback of entire operation."""
        # Arrange
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ONE",
            role="student",
        )

        # Act & Assert
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.bulk_change_role(
                db=db_session,
                borrower_ids=["101", "999"],  # 999 doesn't exist
                new_role="staff"
            )

        # Verify no changes (re-fetch from db)
        borrower_refreshed = db_session.query(Borrower).filter(Borrower.borrower_id == "101").first()
        assert borrower_refreshed is not None
        assert borrower_refreshed.role == "student"


class TestBulkDeleteBorrowers:
    """Integration tests for bulk_delete_borrowers operation."""

    def test_bulk_delete_borrowers_success(self, db_session):
        """Test successful bulk deletion of borrowers."""
        # Arrange: Create borrowers
        borrower_ids = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
            )
            borrower_ids.append(borrower.borrower_id)

        # Act: Delete all
        result = borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=borrower_ids
        )

        # Assert: All deleted
        assert result["total_count"] == 3
        assert result["successful_count"] == 3
        assert result["failed_count"] == 0

        # Verify borrowers no longer exist
        for borrower_id in borrower_ids:
            with pytest.raises(BorrowerNotFoundException):
                borrower_service.get_borrower_by_id(db_session, borrower_id)

    def test_bulk_delete_borrowers_cascade_deletes_circulation_history(self, db_session):
        """Test that deleting borrowers CASCADE deletes their circulation history."""
        # Arrange: Create borrower with circulation history
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ONE",
            role="student",
        )

        # Create bibliographic record and item
        biblio = BiblographicRecord(
            title="Test Book",
            authors=json.dumps(["Author"]),
            isbn="9782080687346",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            status="available",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create circulation transaction (RETURNED, not active)
        loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.now() - timedelta(days=20),
            due_date=(datetime.now() - timedelta(days=6)).date(),
            return_date=datetime.now() - timedelta(days=5),  # Returned!
            status="returned",
        )
        db_session.add(loan)
        db_session.commit()
        loan_id = loan.id

        # Verify loan exists
        assert db_session.query(CirculationTransaction).filter_by(id=loan_id).first() is not None

        # Act: Delete borrower (allowed because no active loans)
        result = borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=["101"]
        )

        # Assert: Borrower deleted
        assert result["successful_count"] == 1
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.get_borrower_by_id(db_session, "101")

        # Circulation history CASCADE deleted
        assert db_session.query(CirculationTransaction).filter_by(id=loan_id).first() is None

    def test_bulk_delete_borrowers_updates_class_student_count(self, db_session):
        """Test that deleting students updates class student_count."""
        # Arrange: Create class and students
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        db_session.add(cp_a)
        db_session.commit()

        borrower_ids = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )
            borrower_ids.append(borrower.borrower_id)

        db_session.refresh(cp_a)
        assert cp_a.student_count == 3

        # Act: Delete students
        result = borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=borrower_ids
        )

        # Assert: Class count updated
        assert result["successful_count"] == 3
        db_session.refresh(cp_a)
        assert cp_a.student_count == 0

    def test_bulk_delete_borrowers_invalid_id_rolls_back(self, db_session):
        """Test that one invalid borrower ID causes rollback of entire operation."""
        # Arrange: Create borrowers
        borrower_ids = []
        for i in range(1, 3):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
            )
            borrower_ids.append(borrower.borrower_id)

        # Act & Assert: Include invalid ID
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.bulk_delete_borrowers(
                db=db_session,
                borrower_ids=borrower_ids + ["999"]  # 999 doesn't exist
            )

        # Verify NO deletions occurred (rollback)
        # After exception, all borrowers should still exist
        for borrower_id in borrower_ids:
            borrower = db_session.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
            assert borrower is not None  # Still exists

    def test_bulk_delete_borrowers_mixed_roles(self, db_session):
        """Test bulk delete with mixed borrower roles."""
        # Arrange: Create borrowers with different roles
        student = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ONE",
            role="student",
        )
        teacher = borrower_service.create_borrower(
            db=db_session,
            borrower_id="201",
            first_name="Teacher",
            last_name="ONE",
            role="teacher",
        )
        staff = borrower_service.create_borrower(
            db=db_session,
            borrower_id="301",
            first_name="Staff",
            last_name="ONE",
            role="staff",
        )

        # Act: Delete all
        result = borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=["101", "201", "301"]
        )

        # Assert: All deleted
        assert result["successful_count"] == 3
        for borrower_id in ["101", "201", "301"]:
            with pytest.raises(BorrowerNotFoundException):
                borrower_service.get_borrower_by_id(db_session, borrower_id)

    def test_bulk_delete_empty_list(self, db_session):
        """Test that empty borrower ID list returns zero successful."""
        # Act
        result = borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=[]
        )

        # Assert
        assert result["total_count"] == 0
        assert result["successful_count"] == 0
        assert result["failed_count"] == 0


class TestBulkOperationsAtomicity:
    """Test atomic transaction behavior across all bulk operations."""

    def test_bulk_change_class_all_or_nothing(self, db_session):
        """Test that bulk change class is truly atomic (all or nothing)."""
        # Arrange: Create multiple borrowers
        cp_a = Class(name="CP-A", homeroom_teacher="Mme Martin")
        db_session.add(cp_a)
        db_session.commit()

        borrowers = []
        for i in range(1, 6):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )
            borrowers.append(borrower)

        # Inject one invalid borrower ID to force failure
        borrower_ids = [b.borrower_id for b in borrowers] + ["999"]

        # Act & Assert: Operation fails
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.bulk_change_class(
                db=db_session,
                borrower_ids=borrower_ids,
                new_class_id=None  # Try to unassign all
            )

        # Verify ALL borrowers still in original class (nothing changed)
        # Re-fetch all borrowers from db
        for borrower in borrowers:
            borrower_refreshed = db_session.query(Borrower).filter(Borrower.borrower_id == borrower.borrower_id).first()
            assert borrower_refreshed is not None
            assert borrower_refreshed.class_id == cp_a.id

        # Re-fetch class
        cp_a_refreshed = db_session.query(Class).filter(Class.id == cp_a.id).first()
        assert cp_a_refreshed.student_count == 5  # Count unchanged

    def test_bulk_change_role_all_or_nothing(self, db_session):
        """Test that bulk change role is truly atomic."""
        # Arrange
        borrowers = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
            )
            borrowers.append(borrower)

        # Inject invalid borrower ID
        borrower_ids = [b.borrower_id for b in borrowers] + ["999"]

        # Act & Assert
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.bulk_change_role(
                db=db_session,
                borrower_ids=borrower_ids,
                new_role="staff"
            )

        # Verify ALL still students (nothing changed)
        for borrower in borrowers:
            borrower_refreshed = db_session.query(Borrower).filter(Borrower.borrower_id == borrower.borrower_id).first()
            assert borrower_refreshed is not None
            assert borrower_refreshed.role == "student"

    def test_bulk_delete_all_or_nothing(self, db_session):
        """Test that bulk delete is truly atomic."""
        # Arrange
        borrowers = []
        for i in range(1, 4):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
            )
            borrowers.append(borrower)

        # Inject invalid borrower ID
        borrower_ids = [b.borrower_id for b in borrowers] + ["999"]

        # Act & Assert
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.bulk_delete_borrowers(
                db=db_session,
                borrower_ids=borrower_ids
            )

        # Verify ALL still exist (nothing deleted)
        for borrower in borrowers:
            # Verify can still be retrieved
            retrieved = db_session.query(Borrower).filter(Borrower.borrower_id == borrower.borrower_id).first()
            assert retrieved is not None
            assert retrieved.id == borrower.id

    def test_bulk_delete_borrowers_with_active_loans_raises_exception(self, db_session):
        """Test that deleting borrowers with active loans raises exception."""
        # Arrange: Create borrower with active loan
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Student",
            last_name="ACTIVE",
            role="student",
        )

        # Create bibliographic record and item
        biblio = BiblographicRecord(
            title="Active Loan Book",
            authors=json.dumps(["Author"]),
            isbn="9782080687346",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="999",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create ACTIVE loan (return_date IS NULL)
        loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.now(),
            due_date=(datetime.now() + timedelta(days=14)).date(),
            status="active",
            return_date=None  # Active loan!
        )
        db_session.add(loan)
        db_session.commit()

        # Act & Assert: Deletion should raise exception
        with pytest.raises(BorrowerHasActiveLoansException) as exc_info:
            borrower_service.bulk_delete_borrowers(
                db=db_session,
                borrower_ids=["101"]
            )

        # Verify exception details
        assert exc_info.value.error_code == "BORROWER_HAS_ACTIVE_LOANS"
        assert exc_info.value.context["borrower_id"] == "101"
        assert exc_info.value.context["active_loan_count"] == 1

        # Verify borrower still exists (transaction rolled back)
        borrower_check = borrower_service.get_borrower_by_id(db_session, "101")
        assert borrower_check is not None

    def test_bulk_delete_borrowers_with_returned_loans_succeeds(self, db_session):
        """Test that deleting borrowers with only historical loans succeeds."""
        # Arrange: Create borrower with RETURNED loan
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Student",
            last_name="HISTORY",
            role="student",
        )

        biblio = BiblographicRecord(
            title="Returned Book",
            authors=json.dumps(["Author"]),
            isbn="9782080687346",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="998",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            status="available",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create HISTORICAL loan (return_date IS NOT NULL)
        loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.now() - timedelta(days=30),
            due_date=(datetime.now() - timedelta(days=16)).date(),
            return_date=datetime.now() - timedelta(days=14),  # Already returned!
            status="returned"
        )
        db_session.add(loan)
        db_session.commit()
        loan_id = loan.id

        # Act: Delete borrower
        result = borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=["102"]
        )

        # Assert: Deletion successful
        assert result["successful_count"] == 1

        # Borrower deleted
        with pytest.raises(BorrowerNotFoundException):
            borrower_service.get_borrower_by_id(db_session, "102")

        # Historical loan CASCADE deleted
        assert db_session.query(CirculationTransaction).filter_by(id=loan_id).first() is None
