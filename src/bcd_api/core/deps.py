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
    Get system settings (singleton). Strictly read-only to preserve
    transaction boundaries during circulation commands.

    Args:
        db: Database session

    Returns:
        SystemSettings: System settings instance

    Raises:
        NotFoundError: If settings not found (should never happen)
    """
    from src.bcd_api.core.exceptions import NotFoundError
    settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()

    if not settings:
        raise NotFoundError("SystemSettings", 1)

    return settings
