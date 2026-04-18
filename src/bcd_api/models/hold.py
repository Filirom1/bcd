"""Hold model - represents a borrower's request for an item (librarian-mediated)."""

from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship

from src.bcd_api.core.database import Base
from src.shared.constants import HoldStatus


class Hold(Base):
    """Represents a borrower's request for an item currently on loan."""

    __tablename__ = "hold"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Relationships
    borrower_id = Column(
        Integer,
        ForeignKey("borrower.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    bibliographic_record_id = Column(
        Integer,
        ForeignKey("bibliographic_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Hold information
    hold_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    queue_position = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default=HoldStatus.WAITING.value, index=True)

    # Pickup information
    available_date = Column(DateTime, nullable=True)
    expiration_date = Column(Date, nullable=True, index=True)
    fulfilled_date = Column(DateTime, nullable=True)

    # Notifications
    notified = Column(Boolean, nullable=False, default=False)
    notification_method = Column(String(20), nullable=True)

    # Audit information
    created_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{HoldStatus.WAITING.value}', '{HoldStatus.READY.value}', "
            f"'{HoldStatus.FULFILLED.value}', '{HoldStatus.EXPIRED.value}', '{HoldStatus.CANCELLED.value}')",
            name="check_hold_status"
        ),
        CheckConstraint("queue_position > 0", name="check_queue_position_positive"),
    )

    # Relationships
    borrower = relationship("Borrower", back_populates="holds")
    bibliographic_record = relationship("BiblographicRecord", back_populates="holds")

    @property
    def title(self):
        """Title from the related bibliographic record."""
        return self.bibliographic_record.title if self.bibliographic_record else None

    @property
    def authors(self):
        """Authors from the related bibliographic record."""
        return self.bibliographic_record.authors if self.bibliographic_record else None

    @property
    def borrower_name(self):
        """Full name of the borrower."""
        return self.borrower.full_name if self.borrower else None

    @property
    def borrower_string_id(self):
        """String borrower ID of the borrower."""
        return self.borrower.borrower_id if self.borrower else None

    @property
    def borrower_class(self):
        """Class name of the borrower."""
        return self.borrower.class_.name if self.borrower and self.borrower.class_ else None

    def __repr__(self):
        return f"<Hold(id={self.id}, borrower_id={self.borrower_id}, biblio_id={self.bibliographic_record_id}, status={self.status})>"
