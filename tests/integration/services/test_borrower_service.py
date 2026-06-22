"""Integration tests for borrower service."""

import json
from datetime import datetime, timedelta

from src.bcd_api.models.bibliographic_record import BiblographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.models.class_model import Class
from src.bcd_api.models.item import Item
from src.bcd_api.services import borrower_service


class TestBorrowerCreationIntegration:
    """Integration tests for borrower creation with real database."""

    def test_create_borrower_full_workflow(self, db_session):
        """Test complete borrower creation workflow."""
        # System settings already exist from fixture
        # Create class
        class_obj = Class(
            name="CP-A",
            homeroom_teacher="Mme Martin",
        )
        db_session.add(class_obj)
        db_session.commit()

        # Create borrower
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
            class_id=class_obj.id,
            email="amira.benali@school.fr",
        )

        # Verify all fields
        assert borrower.id is not None
        assert borrower.borrower_id == "101"
        assert borrower.full_name == "Amira BENALI"
        assert borrower.class_id == class_obj.id
        assert borrower.barcode == "101"  # Barcode = borrower_id (frontend adds prefix)
        assert borrower.active is True
        assert borrower.email == "amira.benali@school.fr"
        assert borrower.created_at is not None

    def test_create_multiple_borrowers_same_class(self, db_session):
        """Test creating multiple borrowers in the same class."""
        # System settings already exist from fixture
        class_obj = Class(name="CP-A")
        db_session.add(class_obj)
        db_session.commit()

        # Create 5 borrowers
        borrowers = []
        for i in range(1, 6):
            borrower = borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"Student{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=class_obj.id,
            )
            borrowers.append(borrower)

        # Verify all created
        assert len(borrowers) == 5
        # Verify all have same class
        assert all(b.class_id == class_obj.id for b in borrowers)

    def test_create_borrowers_different_roles(self, db_session):
        """Test creating borrowers with different roles."""
        # System settings already exist from fixture

        # Create student
        student = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
        )

        # Create teacher
        teacher = borrower_service.create_borrower(
            db=db_session,
            borrower_id="201",
            first_name="Marie",
            last_name="MARTIN",
            role="teacher",
        )

        # Create staff
        staff = borrower_service.create_borrower(
            db=db_session,
            borrower_id="301",
            first_name="Jean",
            last_name="DUPONT",
            role="staff",
        )

        assert student.role == "student"
        assert teacher.role == "teacher"
        assert staff.role == "staff"


class TestBorrowerListingIntegration:
    """Integration tests for borrower listing and filtering."""

    def test_list_borrowers_comprehensive(self, db_session):
        """Test comprehensive borrower listing with various filters."""
        # System settings already exist from fixture

        # Create two classes
        cp_a = Class(name="CP-A")
        ce1_a = Class(name="CE1-A")
        db_session.add_all([cp_a, ce1_a])
        db_session.commit()

        # Create students in CP-A
        for i in range(1, 4):
            borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"StudentCP{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=cp_a.id,
            )

        # Create students in CE1-A
        for i in range(4, 7):
            borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"10{i}",
                first_name=f"StudentCE1{i}",
                last_name=f"LAST{i}",
                role="student",
                class_id=ce1_a.id,
            )

        # Create teachers
        for i in range(1, 3):
            borrower_service.create_borrower(
                db=db_session,
                borrower_id=f"20{i}",
                first_name=f"Teacher{i}",
                last_name=f"TEACH{i}",
                role="teacher",
            )

        # Test: List all
        all_borrowers, total = borrower_service.list_borrowers(db_session)
        assert len(all_borrowers) == 8
        assert total == 8

        # Test: Filter by class
        cp_a_students, cp_total = borrower_service.list_borrowers(db_session, class_id=cp_a.id)
        assert len(cp_a_students) == 3
        assert cp_total == 3

        # Test: Filter by role
        students, student_total = borrower_service.list_borrowers(db_session, role="student")
        teachers, teacher_total = borrower_service.list_borrowers(db_session, role="teacher")
        assert len(students) == 6
        assert student_total == 6
        assert len(teachers) == 2
        assert teacher_total == 2


class TestBorrowerWithCirculationIntegration:
    """Integration tests for borrower with circulation data."""

    def test_borrower_details_with_active_loans(self, db_session):
        """Test borrower details including active loans."""
        # System settings already exist from fixture

        # Create borrower
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
        )

        # Create bibliographic record and items
        biblio = BiblographicRecord(
            title="Test Book",
            authors=json.dumps(["Test Author"]),
            isbn="9782080687346",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item1 = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            call_number="800.000",
            status="on_loan",
            loanable=True,
        )
        item2 = Item(
            item_id="786",
            bibliographic_record_id=biblio.id,
            call_number="800.001",
            status="on_loan",
            loanable=True,
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        # Create circulation transactions
        loan1 = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item1.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.now().date(),
            due_date=(datetime.now() + timedelta(days=14)).date(),
            status="active",
        )
        loan2 = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item2.id,
            bibliographic_record_id=biblio.id,
            checkout_date=datetime.now().date(),
            due_date=(datetime.now() + timedelta(days=14)).date(),
            status="active",
        )
        db_session.add_all([loan1, loan2])
        db_session.commit()

        # Get borrower details
        details = borrower_service.get_borrower_details(db_session, "101")

        assert details["borrower"].borrower_id == "101"
        assert details["current_loans_count"] == 2
        assert details["total_checkouts"] == 2
        assert details["overdue_count"] == 0

    def test_borrower_details_with_overdue_items(self, db_session):
        """Test borrower details with overdue items."""
        # System settings already exist from fixture

        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="102",
            first_name="Lucas",
            last_name="DUBOIS",
            role="student",
        )

        # Create item and overdue loan
        biblio = BiblographicRecord(title="Test Book", authors=json.dumps(["Author"]), medium_type="Livre")
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="787",
            bibliographic_record_id=biblio.id,
            call_number="800.002",
            status="on_loan",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Create overdue loan (due date in the past)
        overdue_loan = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=biblio.id,
            checkout_date=(datetime.now() - timedelta(days=20)).date(),
            due_date=(datetime.now() - timedelta(days=6)).date(),  # 6 days overdue
            status="active",
        )
        db_session.add(overdue_loan)
        db_session.commit()

        # Get details
        details = borrower_service.get_borrower_details(db_session, "102")

        assert details["current_loans_count"] == 1
        assert details["overdue_count"] == 1


class TestBorrowerUpdateIntegration:
    """Integration tests for borrower updates."""

    def test_update_borrower_move_class(self, db_session):
        """Test moving borrower from one class to another."""
        # System settings already exist from fixture
        cp_a = Class(name="CP-A")
        cp_b = Class(name="CP-B")
        db_session.add_all([cp_a, cp_b])
        db_session.commit()

        # Create borrower in CP-A
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
            class_id=cp_a.id,
        )
        assert borrower.class_id == cp_a.id

        # Move to CP-B
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            class_id=cp_b.id,
        )
        assert updated.class_id == cp_b.id

    def test_block_unblock_workflow(self, db_session):
        """Test complete block/unblock workflow."""
        # System settings already exist from fixture
        db_session.commit()

        # Create borrower
        borrower = borrower_service.create_borrower(
            db=db_session,
            borrower_id="103",
            first_name="Test",
            last_name="USER",
            role="student",
        )
        assert borrower.active is True

        # Block borrower
        blocked = borrower_service.block_borrower(
            db=db_session,
            borrower_id="103",
            reason="Overdue items - 3 books",
        )
        assert blocked.active is False
        assert blocked.blocked_reason == "Overdue items - 3 books"

        # Verify can't create new checkouts (would be tested in circulation service)

        # Unblock borrower
        unblocked = borrower_service.unblock_borrower(db_session, "103")
        assert unblocked.active is True
        assert unblocked.blocked_reason is None


class TestBorrowerCompleteScenarios:
    """End-to-end scenarios for borrower management."""

    def test_complete_student_lifecycle(self, db_session):
        """Test complete student lifecycle from creation to deletion."""
        # Setup
        # System settings already exist from fixture
        cp_class = Class(name="CP-A")
        ce1_class = Class(name="CE1-A")
        db_session.add_all([cp_class, ce1_class])
        db_session.commit()

        # Year 1: Create student in CP
        student = borrower_service.create_borrower(
            db=db_session,
            borrower_id="101",
            first_name="Amira",
            last_name="BENALI",
            role="student",
            class_id=cp_class.id,
        )
        assert student.class_id == cp_class.id

        # Year 2: Move to CE1
        updated = borrower_service.update_borrower(
            db=db_session,
            borrower_id="101",
            class_id=ce1_class.id,
        )
        assert updated.class_id == ce1_class.id

        # Student gets blocked for overdue
        blocked = borrower_service.block_borrower(
            db=db_session,
            borrower_id="101",
            reason="Books overdue",
        )
        assert blocked.active is False

        # Returns books and gets unblocked
        unblocked = borrower_service.unblock_borrower(db_session, "101")
        assert unblocked.active is True

        # Verify final state
        final_details = borrower_service.get_borrower_details(db_session, "101")
        assert final_details["borrower"].class_id == ce1_class.id
        assert final_details["borrower"].active is True


class TestGetNextAvailableId:
    """Tests for get_next_available_id() - reuses freed borrower IDs."""

    def test_empty_database_returns_one(self, db_session):
        """When no borrowers exist, the next available ID is 1."""
        result = borrower_service.get_next_available_id(db_session)
        assert result == "1"

    def test_sequential_ids_returns_next(self, db_session):
        """With IDs 1, 2, 3 in use, should return 4."""
        for i in [1, 2, 3]:
            borrower_service.create_borrower(
                db_session,
                borrower_id=str(i),
                first_name="Élève",
                last_name=f"Test{i}",
                role="student",
            )

        result = borrower_service.get_next_available_id(db_session)
        assert result == "4"

    def test_gap_in_ids_returns_smallest_gap(self, db_session):
        """When ID 1 is freed (deleted), it should be reused before higher IDs."""
        # Create borrowers with IDs 2 and 3 (simulating ID 1 was deleted)
        for i in [2, 3]:
            borrower_service.create_borrower(
                db_session,
                borrower_id=str(i),
                first_name="Élève",
                last_name=f"Test{i}",
                role="student",
            )

        result = borrower_service.get_next_available_id(db_session)
        assert result == "1"

    def test_year_end_cm2_deletion_reuses_ids(self, db_session):
        """Simulates year-end: CM2 students (IDs 1-3) deleted, CP gets ID 1."""
        # CM2 students had IDs 1, 2, 3 — now deleted (we only create 4, 5, 6)
        for i in [4, 5, 6]:
            borrower_service.create_borrower(
                db_session,
                borrower_id=str(i),
                first_name="Élève",
                last_name=f"CE1-{i}",
                role="student",
            )

        result = borrower_service.get_next_available_id(db_session)
        assert result == "1"

    def test_non_numeric_ids_are_ignored(self, db_session):
        """Non-numeric IDs stored in DB should not affect the sequence."""
        # Insert directly bypassing service validation (edge case: data migration)
        from src.bcd_api.models.borrower import Borrower
        db_session.add(Borrower(
            borrower_id="PROF1", first_name="Marie", last_name="Dupont",
            full_name="Marie Dupont", role="teacher", active=True
        ))
        db_session.commit()

        result = borrower_service.get_next_available_id(db_session)
        assert result == "1"

    def test_mixed_numeric_and_non_numeric(self, db_session):
        """With IDs 1, 2, and a non-numeric ID, should return 3."""
        from src.bcd_api.models.borrower import Borrower
        borrower_service.create_borrower(
            db_session, borrower_id="1",
            first_name="A", last_name="B", role="student"
        )
        borrower_service.create_borrower(
            db_session, borrower_id="2",
            first_name="C", last_name="D", role="student"
        )
        # Insert non-numeric ID directly (bypasses format validation)
        db_session.add(Borrower(
            borrower_id="PROF1", first_name="Marie", last_name="Dupont",
            full_name="Marie Dupont", role="teacher", active=True
        ))
        db_session.commit()

        result = borrower_service.get_next_available_id(db_session)
        assert result == "3"


class TestBorrowerSearchAccentInsensitive:
    """Tests for accent-insensitive name search in list_borrowers."""

    def _create_student(self, db_session, borrower_id, first_name, last_name):
        db_session.add(Borrower(
            borrower_id=borrower_id,
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            role="student",
            active=True,
        ))
        db_session.commit()

    def test_search_accented_first_name_without_accent(self, db_session):
        """Typing 'elea' finds 'Eléa'."""
        self._create_student(db_session, "1", "Eléa", "MARTIN")
        results, total = borrower_service.list_borrowers(db_session, search="elea")
        assert total == 1
        assert results[0].first_name == "Eléa"

    def test_search_accented_last_name_without_accent(self, db_session):
        """Typing 'francois' finds 'François'."""
        self._create_student(db_session, "1", "Jean", "François")
        results, total = borrower_service.list_borrowers(db_session, search="francois")
        assert total == 1
        assert results[0].last_name == "François"

    def test_search_with_accent_finds_accented_name(self, db_session):
        """Typing 'éléa' also finds 'Eléa'."""
        self._create_student(db_session, "1", "Eléa", "MARTIN")
        results, total = borrower_service.list_borrowers(db_session, search="éléa")
        assert total == 1

    def test_search_without_accent_does_not_match_unrelated(self, db_session):
        """'lea' does not match 'Amélie' but matches 'Léa'."""
        self._create_student(db_session, "1", "Léa", "DUPONT")
        self._create_student(db_session, "2", "Amélie", "DURAND")
        results, total = borrower_service.list_borrowers(db_session, search="lea")
        assert total == 1
        assert results[0].first_name == "Léa"

    def test_search_case_insensitive(self, db_session):
        """Search is also case-insensitive."""
        self._create_student(db_session, "1", "Chloé", "BERNARD")
        results, total = borrower_service.list_borrowers(db_session, search="CHLOE")
        assert total == 1
