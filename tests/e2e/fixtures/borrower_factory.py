"""
Borrower Factory for E2E Tests

Provides flexible test data creation for borrowers with sensible defaults.
"""

from src.bcd_api.models.borrower import Borrower
from src.shared.constants import BorrowerRole


class BorrowerFactory:
    """Factory for creating test borrowers."""

    def __init__(self, db_session):
        self.db = db_session
        self._counter = 1000

    def create(self, **kwargs):
        """
        Create a borrower with sensible defaults.

        Args:
            borrower_id: Student ID (auto-generated if not provided)
            first_name: First name (default: "Test")
            last_name: Last name (default: "Student")
            role: Role (default: "student")
            active: Active status (default: True)
            blocked_reason: Blocking reason (default: None)
            class_id: Class ID (default: None)
            grade_level: Grade level (default: None)

        Returns:
            Borrower: Created borrower instance
        """
        borrower_id = kwargs.get('borrower_id', str(self._counter))
        self._counter += 1

        first_name = kwargs.get('first_name', 'Test')
        last_name = kwargs.get('last_name', 'Student')

        borrower = Borrower(
            borrower_id=borrower_id,
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            role=kwargs.get('role', BorrowerRole.STUDENT.value),
            active=kwargs.get('active', True),
            blocked_reason=kwargs.get('blocked_reason'),
            class_id=kwargs.get('class_id'),
            grade_level=kwargs.get('grade_level'),
        )

        self.db.add(borrower)
        self.db.commit()
        self.db.refresh(borrower)

        return borrower

    def create_blocked(self, reason="Test block", **kwargs):
        """Create a blocked borrower."""
        kwargs['active'] = False
        kwargs['blocked_reason'] = reason
        return self.create(**kwargs)

    def create_batch(self, count=5, **kwargs):
        """Create multiple borrowers."""
        borrowers = []
        for i in range(count):
            borrower = self.create(**kwargs)
            borrowers.append(borrower)
        return borrowers
