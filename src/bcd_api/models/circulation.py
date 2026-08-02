"""CirculationTransaction model - represents a checkout event."""

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.bcd_api.core.database import Base
from src.shared.constants import CirculationStatus


class CirculationTransaction(Base):
    """Represents a checkout event linking a borrower to an item."""

    __tablename__ = "circulation_transaction"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Relationships
    borrower_id = Column(
        Integer,
        ForeignKey("borrower.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    item_id = Column(
        Integer,
        ForeignKey("item.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    bibliographic_record_id = Column(
        Integer,
        ForeignKey("bibliographic_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction dates
    checkout_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    due_date = Column(Date, nullable=False, index=True)
    return_date = Column(DateTime, nullable=True, index=True)

    # Transaction status
    status = Column(String(20), nullable=False, default=CirculationStatus.ACTIVE.value, index=True)
    renewal_count = Column(Integer, nullable=False, default=0)

    # Audit information
    checked_out_by = Column(String(100), nullable=True)
    returned_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{CirculationStatus.ACTIVE.value}', '{CirculationStatus.RETURNED.value}', "
            f"'{CirculationStatus.OVERDUE.value}', '{CirculationStatus.RENEWED.value}')",
            name="check_circulation_status"
        ),
        CheckConstraint(
            "return_date IS NULL OR return_date >= checkout_date",
            name="check_return_date_after_checkout"
        ),
    )

    # Relationships
    borrower = relationship("Borrower", back_populates="circulation_transactions")
    item = relationship("Item", back_populates="circulation_transactions")
    bibliographic_record = relationship("BiblographicRecord", back_populates="circulation_transactions")

    @property
    def is_overdue(self) -> bool:
        """Check if active transaction is overdue.

        Note: A returned item is never overdue. For completed/historic transactions,
        use the policy helpers in `services.circulation.policy` directly.
        """
        if self.return_date is not None:
            return False
        return self.due_date < date.today()

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue for active loans.

        Note: Always returns 0 for returned items to preserve public contract.
        For completed/historic transactions, use `services.circulation.policy.overdue_days` instead.
        """
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    def __repr__(self):
        return f"<CirculationTransaction(id={self.id}, borrower_id={self.borrower_id}, item_id={self.item_id}, status={self.status})>"
