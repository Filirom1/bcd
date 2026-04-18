"""Item model - represents a physical copy of a bibliographic record."""

from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from src.bcd_api.core.database import Base
from src.shared.constants import ItemStatus, ItemCondition


class Item(Base):
    """Represents a physical copy of a bibliographic record."""

    __tablename__ = "item"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(String(20), nullable=False, unique=True, index=True)
    bibliographic_record_id = Column(
        Integer,
        ForeignKey("bibliographic_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Location and classification
    call_number = Column(String(50), nullable=True, index=True)
    shelf_location = Column(String(100), nullable=True)

    # Item status
    condition = Column(String(20), nullable=False, default=ItemCondition.GOOD.value, index=True)
    status = Column(String(20), nullable=False, default=ItemStatus.AVAILABLE.value, index=True)
    loanable = Column(Boolean, nullable=False, default=True, index=True)

    # Acquisition information
    acquisition_date = Column(Date, nullable=True)
    funding_source = Column(String(100), nullable=True)

    # Statistics (denormalized for performance)
    circulation_count = Column(Integer, nullable=False, default=0)
    last_borrowed_at = Column(DateTime, nullable=True)

    # Inventory tracking
    last_inventoried_at = Column(DateTime, nullable=True, index=True)

    # Audit timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            f"condition IN ('{ItemCondition.GOOD.value}', '{ItemCondition.DAMAGED.value}')",
            name="check_item_condition"
        ),
        CheckConstraint(
            f"status IN ('{ItemStatus.AVAILABLE.value}', '{ItemStatus.ON_LOAN.value}', "
            f"'{ItemStatus.ON_HOLD.value}', '{ItemStatus.IN_REPAIR.value}', "
            f"'{ItemStatus.LOST.value}', '{ItemStatus.WITHDRAWN.value}')",
            name="check_item_status"
        ),
    )

    # Relationships
    bibliographic_record = relationship("BiblographicRecord", back_populates="items")
    circulation_transactions = relationship(
        "CirculationTransaction",
        back_populates="item",
        cascade="all, delete-orphan"
    )

    @property
    def barcode(self) -> str:
        """Barcode is the item_id (frontend adds prefix for display/printing)."""
        return self.item_id

    def __repr__(self):
        return f"<Item(id={self.id}, item_id={self.item_id}, status={self.status})>"
