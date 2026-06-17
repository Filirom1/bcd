"""BiblographicRecord model - represents the intellectual content/metadata of a title."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship

from src.bcd_api.core.database import Base
from src.shared.constants import TargetAudience, BindingType


class BiblographicRecord(Base):
    """Represents the intellectual content/metadata of a title (one record per title)."""

    __tablename__ = "bibliographic_record"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Identifiers
    isbn = Column(String(22), nullable=True, index=True)
    cover_image = Column(String(50), nullable=True)  # local filename: '{isbn}.jpg'

    # Title information
    title = Column(String(500), nullable=False, index=True)
    subtitle = Column(String(500), nullable=True)

    # Creator information (JSON arrays)
    authors = Column(Text, nullable=True)  # JSON array
    illustrators = Column(Text, nullable=True)  # JSON array

    # Publication information
    publisher = Column(String(200), nullable=True)
    publication_year = Column(Integer, nullable=True, index=True)
    collection = Column(String(200), nullable=True)
    series_number = Column(String(50), nullable=True)

    # Language and format (from BNF API)
    language = Column(String(10), nullable=True, index=True)
    country_code = Column(String(5), nullable=True)
    binding_type = Column(String(20), nullable=True)

    # Classification and categorization
    genre = Column(String(100), nullable=True, index=True)
    level = Column(String(50), nullable=True)
    medium_type = Column(String(50), nullable=False, index=True)
    target_audience = Column(String(20), nullable=True, index=True)

    # Dewey classification (from BnF 676$a)
    dewey_number = Column(Text, nullable=True)

    # Subject and description
    keywords = Column(Text, nullable=True)  # JSON array
    description = Column(Text, nullable=True)

    # Physical characteristics (from BNF API)
    page_count = Column(Integer, nullable=True)
    has_illustrations = Column(Boolean, nullable=True)
    dimensions = Column(String(50), nullable=True)
    physical_size = Column(String(100), nullable=True)

    # Denormalized item count (kept: used in orphan detection)
    total_items = Column(Integer, nullable=False, default=0)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        # NOTE: medium_type has NO constraint per spec FR-014 (plain text storage without normalization)
        # This allows values like "CD Audio", "DVD Vidéo", "Livre + CD", "Bande dessinée", etc.
        # Do NOT add CHECK constraint here - it violates the spec requirement for flexibility!

        CheckConstraint(
            f"target_audience IN ('{TargetAudience.CHILD.value}', '{TargetAudience.YOUTH.value}', "
            f"'{TargetAudience.ADULT.value}') OR target_audience IS NULL",
            name="check_target_audience"
        ),
        CheckConstraint(
            f"binding_type IN ('{BindingType.HARDCOVER.value}', '{BindingType.PAPERBACK.value}', "
            f"'{BindingType.SPIRAL.value}', '{BindingType.OTHER.value}') OR binding_type IS NULL",
            name="check_binding_type"
        ),
    )

    # Relationships
    items = relationship("Item", back_populates="bibliographic_record", cascade="all, delete-orphan")
    circulation_transactions = relationship(
        "CirculationTransaction",
        back_populates="bibliographic_record",
        cascade="all, delete-orphan"
    )
    holds = relationship("Hold", back_populates="bibliographic_record", cascade="all, delete-orphan")

    @property
    def isbn_value(self) -> Optional[str]:
        """ISBN/ISSN value without prefix (isbn: or issn:)."""
        if self.isbn is None:
            return None
        if self.isbn.startswith('isbn:') or self.isbn.startswith('issn:'):
            return self.isbn[5:]
        return self.isbn

    @property
    def identifier_type(self) -> str:
        """Type of identifier: 'issn' for periodicals, 'isbn' otherwise."""
        if self.isbn and self.isbn.startswith('issn:'):
            return 'issn'
        return 'isbn'

    def __repr__(self):
        return f"<BiblographicRecord(id={self.id}, isbn={self.isbn}, title={self.title})>"
