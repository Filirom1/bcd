"""
Integration tests for circulation service

Tests complete workflows including database transactions, business logic,
and data validation according to User Story 1 acceptance scenarios.
"""

from datetime import date, timedelta

import pytest

from src.bcd_api.core.exceptions import (
    BorrowerBlockedException,
    ConflictError,
    ItemNotLoanableException,
    ItemNotOnLoanException,
    LoanLimitExceededException,
    LoanLimitWarningExceededException,
    NotFoundException,
)
from src.bcd_api.models.circulation import CirculationTransaction
from src.bcd_api.services import circulation_service


class TestCheckoutScenarios:
    """Test checkout scenarios from User Story 1."""

    def test_checkout_success_single_item(self, db_session, test_borrower_student, test_item_available):
        """
        Acceptance Scenario 1: Checkout items successfully
        Given: Borrower exists and item is available
        When: Librarian scans borrower ID then item barcode
        Then: Item is checked out with due date assigned
        """
        # Arrange
        borrower_id = test_borrower_student.borrower_id
        item_id = test_item_available.item_id

        # Act
        response = circulation_service.checkout_items(
            db=db_session,
            borrower_id=borrower_id,
            item_ids=[item_id],
            checked_out_by="librarian@test.fr"
        )

        # Assert
        assert response.borrower_id == borrower_id
        assert response.borrower_name == "Amira BENALI"
        assert response.items_checked_out == 1
        assert len(response.transactions) == 1
        assert response.transactions[0]["item_id"] == item_id

        # Verify due date is 14 days from today (default setting)
        expected_due_date = date.today() + timedelta(days=14)
        assert response.due_date == expected_due_date

        # Verify item status changed to on_loan
        db_session.refresh(test_item_available)
        assert test_item_available.status == "on_loan"

        # Verify transaction created in database
        transaction = db_session.query(CirculationTransaction).filter(
            CirculationTransaction.item_id == test_item_available.id
        ).first()
        assert transaction is not None
        assert transaction.borrower_id == test_borrower_student.id
        assert transaction.return_date is None
        assert transaction.status == "active"

    def test_checkout_success_multiple_items(self, db_session, test_borrower_student,
                                            test_item_available, test_item_available_2):
        """
        Acceptance Scenario 1 (extended): Checkout multiple items
        Given: Borrower exists and 2 items are available
        When: Librarian scans borrower ID then scans 2 item barcodes
        Then: Both items are checked out with due dates assigned
        """
        # Arrange
        borrower_id = test_borrower_student.borrower_id
        item_ids = [test_item_available.item_id, test_item_available_2.item_id]

        # Act
        response = circulation_service.checkout_items(
            db=db_session,
            borrower_id=borrower_id,
            item_ids=item_ids
        )

        # Assert
        assert response.items_checked_out == 2
        assert len(response.transactions) == 2

        # Verify both items are now on loan
        db_session.refresh(test_item_available)
        db_session.refresh(test_item_available_2)
        assert test_item_available.status == "on_loan"
        assert test_item_available_2.status == "on_loan"

    def test_checkout_item_already_on_loan(self, db_session, test_borrower_student,
                                          test_item_available, multiple_borrowers):
        """
        Acceptance Scenario 3: Item already on loan to another borrower
        Given: Item is on loan to borrower A
        When: Librarian attempts to check it out to borrower B
        Then: System displays error showing who has the item and due date
        """
        # Arrange - Checkout item to first borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Act & Assert - Try to checkout same item to second borrower
        with pytest.raises(ConflictError) as exc_info:
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=multiple_borrowers[0].borrower_id,
                item_ids=[test_item_available.item_id]
            )

        # Verify error message contains borrower info
        error_detail = str(exc_info.value.detail)
        assert "already on loan" in error_detail
        assert "Amira BENALI" in error_detail
        assert test_item_available.item_id in error_detail

    def test_checkout_borrower_blocked_with_overdue(self, db_session, test_borrower_blocked,
                                                     test_item_available):
        """
        Acceptance Scenario 4: Borrower has overdue items
        Given: Borrower has overdue items (blocked)
        When: Librarian scans borrower ID
        Then: System displays error before allowing new checkouts
        """
        # Act & Assert
        with pytest.raises(BorrowerBlockedException) as exc_info:
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_blocked.borrower_id,
                item_ids=[test_item_available.item_id]
            )

        # Verify error message indicates blocked status
        error_detail = str(exc_info.value.detail)
        assert "blocked" in error_detail.lower() or "inactive" in error_detail.lower()

    def test_checkout_exceeds_limit_student(self, db_session, test_borrower_student, multiple_items):
        """
        Acceptance Scenario 5: Borrower reaches maximum allowed checkouts
        Given: Borrower has 2 items checked out (student limit = 2)
        When: Librarian attempts to check out another item
        Then: System prevents checkout and displays loan limit
        """
        # Arrange - Checkout 2 items (student limit)
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[multiple_items[0].item_id, multiple_items[1].item_id]
        )

        # Act & Assert - Try to checkout 3rd item
        with pytest.raises(LoanLimitExceededException) as exc_info:
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_student.borrower_id,
                item_ids=[multiple_items[2].item_id]
            )

        # Verify error message mentions limit
        error_detail = str(exc_info.value.detail)
        assert "limit" in error_detail.lower()
        assert "2" in error_detail  # Student limit

    def test_checkout_teacher_higher_limit(self, db_session, test_borrower_teacher, multiple_items):
        """
        Test that teachers have higher checkout limits (5 items vs 2 for students)
        """
        # Arrange - Create 5 items
        extra_items = []
        for i in range(3, 6):
            from src.bcd_api.models.item import Item
            item = Item(
                item_id=f"80{i}",
                bibliographic_record_id=multiple_items[0].bibliographic_record_id,
                call_number="800.000",
                status="available",
                condition="good",
                loanable=True
            )
            db_session.add(item)
            extra_items.append(item)
        db_session.commit()

        all_items = multiple_items + extra_items
        item_ids = [item.item_id for item in all_items[:5]]

        # Act - Checkout 5 items (should succeed for teacher)
        response = circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_teacher.borrower_id,
            item_ids=item_ids
        )

        # Assert
        assert response.items_checked_out == 5

    def test_checkout_item_not_loanable(self, db_session, test_borrower_student, test_item_not_loanable):
        """
        Edge Case: Attempt to checkout reference-only item
        Given: Item is marked as not loanable
        When: Librarian attempts checkout
        Then: System prevents checkout with error
        """
        # Act & Assert
        with pytest.raises(ItemNotLoanableException) as exc_info:
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_student.borrower_id,
                item_ids=[test_item_not_loanable.item_id]
            )

        error_detail = str(exc_info.value.detail)
        assert "not loanable" in error_detail.lower()

    def test_checkout_borrower_not_found(self, db_session, test_item_available):
        """
        Edge Case: Borrower ID not in system
        Given: Invalid borrower ID
        When: Librarian scans borrower ID
        Then: System displays borrower not found error
        """
        # Act & Assert
        with pytest.raises(NotFoundException):
            circulation_service.checkout_items(
                db=db_session,
                borrower_id="INVALID999",
                item_ids=[test_item_available.item_id]
            )

    def test_checkout_soft_limit_warning_godot_blocked(self, db_session, test_borrower_student, multiple_items):
        """
        Test that checking out past the soft warning limit blocks in the Godot kids client
        """
        from src.bcd_api.models.system_settings import SystemSettings
        settings = db_session.query(SystemSettings).filter(SystemSettings.id == 1).first()
        settings.loan_limit_warning = 1
        db_session.commit()

        # Checkout first item (brings student to warning limit of 1)
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[multiple_items[0].item_id],
            checked_out_by="godot-ui"
        )

        # Act & Assert - Try to checkout 2nd item from Godot client (should block)
        with pytest.raises(LoanLimitWarningExceededException) as exc_info:
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_student.borrower_id,
                item_ids=[multiple_items[1].item_id],
                checked_out_by="godot-ui"
            )

        # Verify exception details
        assert exc_info.value.error_code == "LOAN_LIMIT_WARNING_EXCEEDED"
        assert exc_info.value.context["current"] == 1
        assert exc_info.value.context["limit"] == 1

    def test_checkout_soft_limit_warning_web_ui_allowed(self, db_session, test_borrower_student, multiple_items):
        """
        Test that checking out past the soft warning limit is allowed in the Web UI / VueJS client
        """
        from src.bcd_api.models.system_settings import SystemSettings
        settings = db_session.query(SystemSettings).filter(SystemSettings.id == 1).first()
        settings.loan_limit_warning = 1
        db_session.commit()

        # Checkout first item (brings student to warning limit of 1)
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[multiple_items[0].item_id],
            checked_out_by="web-ui"
        )

        # Act - Try to checkout 2nd item from Web UI (should succeed)
        response = circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[multiple_items[1].item_id],
            checked_out_by="web-ui"
        )

        # Assert
        assert response.items_checked_out == 1

    def test_checkout_item_not_found(self, db_session, test_borrower_student):
        """
        Edge Case: Item ID not in system
        Given: Invalid item ID
        When: Librarian scans item barcode
        Then: System displays item not found error
        """
        # Act & Assert
        with pytest.raises(NotFoundException):
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_student.borrower_id,
                item_ids=["INVALID999"]
            )


class TestReturnScenarios:
    """Test return scenarios from User Story 1."""

    def test_return_on_time(self, db_session, test_borrower_student, test_item_available):
        """
        Acceptance Scenario 2: Return items on time
        Given: Borrower has checked out items
        When: Librarian scans item barcodes at return desk
        Then: Items are marked as returned and removed from borrower's list
        """
        # Arrange - Checkout item
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Act - Return item
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[test_item_available.item_id],
            returned_by="librarian@test.fr"
        )

        # Assert
        assert response.items_returned == 1
        assert len(response.items) == 1

        returned_item = response.items[0]
        assert returned_item["item_id"] == test_item_available.item_id
        assert returned_item["was_overdue"] is False
        assert returned_item["days_overdue"] == 0

        # Verify item status changed back to available
        db_session.refresh(test_item_available)
        assert test_item_available.status == "available"

        # Verify transaction has return date
        transaction = db_session.query(CirculationTransaction).filter(
            CirculationTransaction.item_id == test_item_available.id
        ).first()
        assert transaction.return_date is not None
        assert transaction.status == "returned"

    def test_return_overdue_auto_block(self, db_session, test_borrower_student, test_item_available):
        """
        Test that returning all overdue items does NOT block borrower
        (Blocking happens during checkout attempt, not during return)
        Given: Borrower has overdue items
        When: Librarian processes return of all overdue items
        Then: Borrower remains active (no blocking during return)
        """
        # Arrange - Checkout item
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Manually set due date to past to simulate overdue
        transaction = db_session.query(CirculationTransaction).filter(
            CirculationTransaction.item_id == test_item_available.id,
            CirculationTransaction.return_date.is_(None)
        ).first()
        transaction.due_date = date.today() - timedelta(days=5)  # 5 days overdue
        db_session.commit()

        # Act - Return overdue item
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[test_item_available.item_id]
        )

        # Assert
        returned_item = response.items[0]
        assert returned_item["was_overdue"] is True
        assert returned_item["days_overdue"] == 5

    def test_return_item_not_on_loan(self, db_session, test_item_available):
        """
        Edge Case: Attempt to return item that's not checked out
        """
        # Act & Assert
        with pytest.raises(ItemNotOnLoanException) as exc_info:
            circulation_service.return_items(
                db=db_session,
                item_ids=[test_item_available.item_id]
            )

        error_detail = str(exc_info.value.detail)
        assert "not currently on loan" in error_detail.lower()


class TestRenewalScenarios:
    """Test renewal scenarios."""

    def test_renew_success(self, db_session, test_borrower_student, test_item_available):
        """
        Test successful renewal extends due date
        """
        # Arrange - Checkout item
        checkout_response = circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )
        original_due_date = checkout_response.due_date

        # Act - Renew item
        response = circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Assert
        assert response.renewed_count == 1
        assert response.failed_count == 0
        assert len(response.renewed) == 1

        renewed_item = response.renewed[0]
        assert renewed_item["item_id"] == test_item_available.item_id
        assert renewed_item["old_due_date"] == original_due_date
        # New due date should be 14 days after original
        expected_new_due = original_due_date + timedelta(days=14)
        assert renewed_item["new_due_date"] == expected_new_due
        assert renewed_item["renewals_used"] == 1
        assert renewed_item["renewals_remaining"] == 1  # Limit is 2

    def test_renew_exceeds_limit(self, db_session, test_borrower_student, test_item_available):
        """
        Test renewal fails when limit exceeded
        """
        # Arrange - Checkout and renew twice (hit limit of 2)
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # First renewal
        circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Second renewal
        circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Act - Try third renewal (should fail)
        response = circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Assert
        assert response.renewed_count == 0
        assert response.failed_count == 1
        assert len(response.failed) == 1
        assert "limit" in response.failed[0]["reason"].lower()

    def test_renew_item_not_on_loan_to_borrower(self, db_session, test_borrower_student,
                                                 multiple_borrowers, test_item_available):
        """
        Test renewal fails if item not on loan to requesting borrower
        """
        # Arrange - Checkout to different borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=multiple_borrowers[0].borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Act - Try to renew as different borrower
        response = circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Assert
        assert response.renewed_count == 0
        assert response.failed_count == 1


class TestBorrowerLoansQuery:
    """Test querying borrower's current loans and history."""

    def test_get_current_loans(self, db_session, test_borrower_student,
                               test_item_available, test_item_available_2):
        """
        Test retrieving borrower's current loans
        """
        # Arrange - Checkout 2 items
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id, test_item_available_2.item_id]
        )

        # Act
        loans = circulation_service.get_borrower_current_loans(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id
        )

        # Assert
        assert len(loans) == 2
        loan1 = loans[0]
        assert "item_id" in loan1
        assert "title" in loan1
        assert "due_date" in loan1
        assert "is_overdue" in loan1
        assert "can_renew" in loan1
        assert loan1["can_renew"] is True  # Haven't renewed yet

    def test_get_circulation_history(self, db_session, test_borrower_student, test_item_available):
        """
        Test retrieving borrower's circulation history
        """
        # Arrange - Checkout and return
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        circulation_service.return_items(
            db=db_session,
            item_ids=[test_item_available.item_id]
        )

        # Act
        history = circulation_service.get_borrower_circulation_history(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id
        )

        # Assert — response is now a BorrowerHistoryResponse Pydantic model
        assert history.borrower_id == test_borrower_student.borrower_id
        assert history.pagination.total_items == 1
        assert len(history.history) == 1


class TestItemCirculationHistory:
    """Test querying item circulation history."""

    def test_get_item_history(self, db_session, test_borrower_student, test_item_available):
        """
        Test retrieving item's circulation history
        """
        # Arrange - Checkout and return
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        circulation_service.return_items(
            db=db_session,
            item_ids=[test_item_available.item_id]
        )

        # Checkout again
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Act
        history = circulation_service.get_item_circulation_history(
            db=db_session,
            item_id=test_item_available.item_id
        )

        # Assert — response is now an ItemHistoryResponse Pydantic model
        assert history.item_id == test_item_available.item_id
        assert history.current_loan is not None
        assert history.current_loan.borrower_name == test_borrower_student.full_name
        assert len(history.history) == 1  # One returned loan


class TestReturnWithHold:
    """Test return scenarios with hold/reservation."""

    def test_return_with_waiting_hold_shows_hold_info(self, db_session):
        """
        Test that returning an item with a waiting hold includes hold information.
        Given: An item on loan and a borrower waiting for it (hold)
        When: The item is returned
        Then: The return response includes hold_ready info with borrower details
        """
        from src.bcd_api.models.bibliographic_record import BibliographicRecord
        from src.bcd_api.models.borrower import Borrower
        from src.bcd_api.models.class_model import Class
        from src.bcd_api.models.item import Item
        from src.bcd_api.services import hold_service

        # Create class
        class_obj = Class(name="CE2-A")
        db_session.add(class_obj)
        db_session.commit()

        # Create first borrower (will checkout the item)
        borrower1 = Borrower(
            borrower_id="101",
            first_name="Lucas",
            last_name="DUBOIS",
            full_name="Lucas DUBOIS",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower1)

        # Create second borrower (will place hold)
        borrower2 = Borrower(
            borrower_id="205",
            first_name="Sophie",
            last_name="MARTIN",
            full_name="Sophie MARTIN",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower2)
        db_session.commit()

        # Create bibliographic record and item
        biblio = BibliographicRecord(
            title="Harry Potter à l'école des sorciers",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="785",
            bibliographic_record_id=biblio.id,
            status="available",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Checkout item to first borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=borrower1.borrower_id,
            item_ids=[item.item_id]
        )

        # Second borrower places hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower2.id,
            bibliographic_record_id=biblio.id,
            created_by="librarian@test.fr",
            notes="Student needs this for homework",
        )

        # Verify hold is in waiting state
        assert hold.status == "waiting"
        assert hold.queue_position == 1

        # Return the item
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[item.item_id],
            returned_by="librarian@test.fr"
        )

        # Assert return was successful
        assert response.items_returned == 1
        assert len(response.items) == 1

        returned_item = response.items[0]
        assert returned_item["item_id"] == item.item_id
        assert returned_item["title"] == biblio.title

        # Assert hold information is included
        assert returned_item["hold_ready"] is not None
        hold_info = returned_item["hold_ready"]
        assert hold_info["borrower_id"] == borrower2.borrower_id
        assert hold_info["borrower_name"] == borrower2.full_name
        assert hold_info["class_name"] == class_obj.name
        assert hold_info["expiration_date"] is not None

        # Verify hold status changed to ready
        db_session.refresh(hold)
        assert hold.status == "ready"

    def test_return_without_hold_shows_no_hold_info(self, db_session, test_borrower_student, test_item_available):
        """
        Test that returning an item without holds shows hold_ready as None.
        """
        # Checkout item
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Return item (no holds exist)
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[test_item_available.item_id]
        )

        # Assert hold_ready is None
        returned_item = response.items[0]
        assert returned_item["hold_ready"] is None

    def test_return_with_hold_uses_system_settings_expiration(self, db_session):
        """
        Test that hold expiration date uses the system settings value.
        """
        from datetime import date, timedelta

        from src.bcd_api.models.bibliographic_record import BibliographicRecord
        from src.bcd_api.models.borrower import Borrower
        from src.bcd_api.models.class_model import Class
        from src.bcd_api.models.item import Item
        from src.bcd_api.models.system_settings import SystemSettings
        from src.bcd_api.services import hold_service

        # Update system settings to use 7 days for hold expiration instead of default 3
        settings = db_session.query(SystemSettings).filter(SystemSettings.id == 1).first()
        settings.hold_expiration_days = 7
        db_session.commit()

        # Create test data
        class_obj = Class(name="CM1-B")
        db_session.add(class_obj)
        db_session.commit()

        borrower1 = Borrower(
            borrower_id="301",
            first_name="Marc",
            last_name="DUPONT",
            full_name="Marc DUPONT",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower1)

        borrower2 = Borrower(
            borrower_id="302",
            first_name="Julie",
            last_name="BERNARD",
            full_name="Julie BERNARD",
            role="student",
            class_id=class_obj.id,
            active=True,
        )
        db_session.add(borrower2)
        db_session.commit()

        biblio = BibliographicRecord(
            title="Le Petit Prince",
            medium_type="Livre",
        )
        db_session.add(biblio)
        db_session.commit()

        item = Item(
            item_id="999",
            bibliographic_record_id=biblio.id,
            status="available",
            loanable=True,
        )
        db_session.add(item)
        db_session.commit()

        # Checkout to first borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=borrower1.borrower_id,
            item_ids=[item.item_id]
        )

        # Second borrower places hold
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=borrower2.id,
            bibliographic_record_id=biblio.id,
            created_by="librarian@test.fr",
        )

        # Return the item
        today = date.today()
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[item.item_id]
        )

        # Verify hold expiration is today + 7 days (from settings)
        returned_item = response.items[0]
        assert returned_item["hold_ready"] is not None
        expected_expiration = today + timedelta(days=7)
        assert returned_item["hold_ready"]["expiration_date"] == expected_expiration

        # Verify in database too
        db_session.refresh(hold)
        assert hold.expiration_date == expected_expiration


class TestReturnItemsIncludesShelfLocation:
    """Test that return_items includes shelf_location in the response."""

    def test_return_items_includes_shelf_location(
        self, db_session, test_borrower_student, test_item_available
    ):
        # Arrange: checkout first
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id],
        )

        # Act
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[test_item_available.item_id],
        )

        # Assert
        returned = response.items[0]
        assert "shelf_location" in returned
        assert returned["shelf_location"] == "Fiction - Section A - Row 3"

    def test_return_items_shelf_location_none_when_not_set(
        self, db_session, test_borrower_student
    ):
        import json

        from src.bcd_api.models.bibliographic_record import BibliographicRecord
        from src.bcd_api.models.item import Item

        # Arrange: item without shelf_location
        record = BibliographicRecord(title="Sans emplacement", authors=json.dumps(["A"]), medium_type="Livre")
        db_session.add(record)
        db_session.flush()
        item = Item(item_id="NO_LOC_99", bibliographic_record_id=record.id, status="available", loanable=True)
        db_session.add(item)
        db_session.flush()

        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[item.item_id],
        )

        # Act
        response = circulation_service.return_items(
            db=db_session,
            item_ids=[item.item_id],
        )

        # Assert
        returned = response.items[0]
        assert "shelf_location" in returned
        assert returned["shelf_location"] is None


class TestPhase0CharacterizationScenarios:
    """Phase 0: Characterization and robustness tests for circulation."""

    def test_checkout_items_atomic_rollback(
        self, db_session, test_borrower_student, test_item_available, test_item_available_2, multiple_borrowers
    ):
        """
        GIVEN: Borrower exists, and two items (one available, one already checked out to someone else)
        WHEN: Attempting a multi-item checkout
        THEN: The entire transaction is rolled back, and the available item remains available
        """
        # Arrange - Checkout the second item to another borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=multiple_borrowers[0].borrower_id,
            item_ids=[test_item_available_2.item_id]
        )
        assert test_item_available_2.status == "on_loan"
        assert test_item_available.status == "available"

        # Act & Assert - Try to check out both to our main borrower
        with pytest.raises(ConflictError):
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_student.borrower_id,
                item_ids=[test_item_available.item_id, test_item_available_2.item_id]
            )

        # Verify that the available item is still available (atomic rollback check)
        db_session.refresh(test_item_available)
        assert test_item_available.status == "available"

    def test_checkout_duplicate_item_ids_rejected(
        self, db_session, test_borrower_student, test_item_available
    ):
        """
        GIVEN: Borrower exists and one item is available
        WHEN: Attempting a checkout with a duplicate item_id in the list
        THEN: The operation fails or handles it cleanly (we reject duplicate scanning of same ID)
        """
        # Act & Assert
        from src.bcd_api.core.exceptions import ConflictError, ValidationError
        with pytest.raises((ConflictError, ValidationError)):
            circulation_service.checkout_items(
                db=db_session,
                borrower_id=test_borrower_student.borrower_id,
                item_ids=[test_item_available.item_id, test_item_available.item_id]
            )

    def test_renew_blocked_by_active_hold_waiting(
        self, db_session, test_borrower_student, test_item_available, multiple_borrowers
    ):
        """
        GIVEN: An item is checked out to borrower A, and a hold (waiting) is placed on it by borrower B
        WHEN: Borrower A attempts to renew the loan
        THEN: The renewal is blocked because there is a waiting reservation
        """
        from src.bcd_api.services import hold_service

        # Arrange: Checkout item to main borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Place a waiting hold on this bibliographic record by another borrower
        hold_service.create_hold(
            db=db_session,
            borrower_id=multiple_borrowers[0].id,
            bibliographic_record_id=test_item_available.bibliographic_record_id,
            created_by="librarian"
        )

        # Act
        response = circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Assert: The renewal must fail
        assert response.failed_count == 1
        assert response.renewed_count == 0
        reason_lower = response.failed[0]["reason"].lower()
        assert "hold" in reason_lower or "reservation" in reason_lower or "réservation" in reason_lower

    def test_renew_blocked_by_active_hold_ready(
        self, db_session, test_borrower_student, test_item_available, multiple_borrowers
    ):
        """
        GIVEN: An item is checked out to borrower A, and a hold (ready) is placed on it by borrower B
        WHEN: Borrower A attempts to renew the loan
        THEN: The renewal is blocked because there is a ready reservation
        """
        from src.bcd_api.services import hold_service

        # Arrange: Checkout item to main borrower
        circulation_service.checkout_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Create a ready hold for another borrower
        hold = hold_service.create_hold(
            db=db_session,
            borrower_id=multiple_borrowers[0].id,
            bibliographic_record_id=test_item_available.bibliographic_record_id,
            created_by="librarian"
        )
        # Mark hold as ready
        hold_service.mark_hold_ready(db=db_session, hold_id=hold.id)

        # Act
        response = circulation_service.renew_items(
            db=db_session,
            borrower_id=test_borrower_student.borrower_id,
            item_ids=[test_item_available.item_id]
        )

        # Assert: The renewal must fail
        assert response.failed_count == 1
        assert response.renewed_count == 0
        reason_lower = response.failed[0]["reason"].lower()
        assert "hold" in reason_lower or "reservation" in reason_lower or "réservation" in reason_lower


class TestRefactoredCirculationSafety:
    """Regression tests for transaction and policy boundaries."""

    def test_return_hold_promotion_failure_rolls_back(
        self, db_session, test_borrower_student, test_item_available,
        multiple_borrowers, monkeypatch,
    ):
        from src.bcd_api.models.circulation import CirculationTransaction
        from src.bcd_api.services import hold_service
        from src.bcd_api.services.holds import commands as hold_commands

        item_id = test_item_available.item_id
        circulation_service.checkout_items(
            db_session, test_borrower_student.borrower_id, [item_id]
        )
        hold_service.create_hold(
            db_session, multiple_borrowers[0].id,
            test_item_available.bibliographic_record_id, "librarian",
        )

        def fail_promotion(*args, **kwargs):
            raise RuntimeError("promotion failed")

        monkeypatch.setattr(
            hold_commands, "auto_fill_holds_on_return_in_transaction", fail_promotion
        )
        with pytest.raises(RuntimeError, match="promotion failed"):
            circulation_service.return_items(db_session, [item_id])

        from src.bcd_api.models.item import Item
        item = db_session.query(Item).filter(Item.item_id == item_id).one()
        assert item.status == "on_loan"
        assert db_session.query(CirculationTransaction).filter(
            CirculationTransaction.item_id == item.id,
            CirculationTransaction.return_date.is_(None),
        ).count() == 1

    def test_renew_unknown_borrower_raises_not_found(self, db_session, test_item_available):
        from src.bcd_api.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            circulation_service.renew_items(
                db_session, "UNKNOWN-BORROWER", [test_item_available.item_id]
            )

    def test_renew_technical_failure_rolls_back(
        self, db_session, test_borrower_student, test_item_available, monkeypatch,
    ):
        from src.bcd_api.models.circulation import CirculationTransaction

        item_id = test_item_available.item_id
        circulation_service.checkout_items(
            db_session, test_borrower_student.borrower_id, [item_id]
        )
        transaction = db_session.query(CirculationTransaction).filter(
            CirculationTransaction.item_id == test_item_available.id,
            CirculationTransaction.return_date.is_(None),
        ).one()
        old_due_date = transaction.due_date
        old_count = transaction.renewal_count
        original_flush = db_session.flush

        def fail_flush(*args, **kwargs):
            raise RuntimeError("database failure")

        monkeypatch.setattr(db_session, "flush", fail_flush)
        with pytest.raises(RuntimeError, match="database failure"):
            circulation_service.renew_items(
                db_session, test_borrower_student.borrower_id, [item_id]
            )
        monkeypatch.setattr(db_session, "flush", original_flush)
        from src.bcd_api.models.item import Item
        transaction = db_session.query(CirculationTransaction).join(Item).filter(
            Item.item_id == item_id,
            CirculationTransaction.return_date.is_(None),
        ).one()
        assert transaction.due_date == old_due_date
        assert transaction.renewal_count == old_count

    def test_checkout_two_copies_consumes_hold_once(
        self, db_session, test_borrower_student, test_item_available, test_item_available_2,
    ):
        from src.bcd_api.models.hold import Hold
        from src.bcd_api.services import hold_service

        test_item_available_2.bibliographic_record_id = test_item_available.bibliographic_record_id
        db_session.commit()
        hold_service.create_hold(
            db_session, test_borrower_student.id,
            test_item_available.bibliographic_record_id, "librarian",
        )
        circulation_service.checkout_items(
            db_session, test_borrower_student.borrower_id,
            [test_item_available.item_id, test_item_available_2.item_id],
        )
        assert db_session.query(Hold).filter(
            Hold.borrower_id == test_borrower_student.id,
            Hold.bibliographic_record_id == test_item_available.bibliographic_record_id,
            Hold.status.in_(["waiting", "ready"]),
        ).count() == 0

    def test_current_loans_can_renew_false_when_title_has_hold(
        self, db_session, test_borrower_student, test_item_available, multiple_borrowers,
    ):
        from src.bcd_api.services import hold_service

        circulation_service.checkout_items(
            db_session, test_borrower_student.borrower_id, [test_item_available.item_id]
        )
        hold_service.create_hold(
            db_session, multiple_borrowers[0].id,
            test_item_available.bibliographic_record_id, "librarian",
        )
        loans = circulation_service.get_borrower_current_loans(
            db_session, test_borrower_student.borrower_id
        )
        assert loans[0]["can_renew"] is False
