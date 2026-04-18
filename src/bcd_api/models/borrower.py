"""Borrower model - represents library users (students, teachers, staff)."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from src.bcd_api.core.database import Base
from src.shared.constants import BorrowerRole


class Borrower(Base):
    """Represents a library user (student, teacher, or staff)."""

    __tablename__ = "borrower"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    borrower_id = Column(String(20), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=False, index=True)

    role = Column(String(20), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("class.id", ondelete="SET NULL"), nullable=True, index=True)
    grade_level = Column(String(20), nullable=True)

    active = Column(Boolean, nullable=False, default=True, index=True)
    blocked_reason = Column(String(200), nullable=True)

    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            f"role IN ('{BorrowerRole.STUDENT.value}', '{BorrowerRole.TEACHER.value}', '{BorrowerRole.STAFF.value}')",
            name="check_borrower_role"
        ),
    )

    # Relationships
    class_ = relationship("Class", back_populates="borrowers")
    circulation_transactions = relationship(
        "CirculationTransaction",
        back_populates="borrower",
        cascade="all, delete-orphan"
    )
    holds = relationship("Hold", back_populates="borrower", cascade="all, delete-orphan")

    @property
    def barcode(self) -> str:
        """Barcode is the borrower_id (frontend adds prefix for display/printing)."""
        return self.borrower_id

    def __repr__(self):
        return f"<Borrower(id={self.id}, borrower_id={self.borrower_id}, name={self.full_name}, role={self.role})>"
