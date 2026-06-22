"""Class model - represents a school class/grade level."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from src.bcd_api.core.database import Base


class Class(Base):
    """Represents a school class/grade level grouping for students."""

    __tablename__ = "class"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, index=True)
    homeroom_teacher = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Average age of students in this class (used for sorting youngest to oldest)
    average_age = Column(Integer, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    borrowers = relationship("Borrower", back_populates="class_")

    def __repr__(self):
        return f"<Class(id={self.id}, name={self.name})>"
