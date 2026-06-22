"""Dependency injection for FastAPI endpoints."""

from typing import Generator

from sqlalchemy.orm import Session

from src.bcd_api.core.database import SessionLocal
from src.bcd_api.models.system_settings import SystemSettings


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings(db: Session) -> SystemSettings:
    """
    Get system settings (singleton).

    Args:
        db: Database session

    Returns:
        SystemSettings: System settings instance

    Raises:
        NotFoundException: If settings not found (should never happen)
    """
    settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()

    if not settings:
        # Create default settings if they don't exist
        settings = SystemSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings
