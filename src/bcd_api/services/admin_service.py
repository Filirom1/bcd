"""Admin Service

Business logic for administrative tasks, health stats, data maintenance, and DB-level updates.
"""

import logging
from pathlib import Path
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.bibliographic_record import BiblographicRecord
from ..models.borrower import Borrower
from ..models.circulation import CirculationTransaction
from ..models.item import Item

logger = logging.getLogger(__name__)


def get_records_without_covers(db: Session) -> list[BiblographicRecord]:
    """Get all bibliographic records that don't have a cover image but have an ISBN."""
    return db.query(BiblographicRecord).filter(
        BiblographicRecord.cover_image == None,
        BiblographicRecord.isbn != None,
        BiblographicRecord.isbn != "",
    ).all()


def get_health_stats(db: Session) -> dict:
    """Get counts of core models in the system to assess health and size."""
    borrower_count = db.query(Borrower).count()
    biblio_count = db.query(BiblographicRecord).count()
    item_count = db.query(Item).count()
    circulation_count = db.query(CirculationTransaction).count()

    return {
        "borrowers": borrower_count,
        "bibliographic_records": biblio_count,
        "items": item_count,
        "circulations": circulation_count,
    }


def backfill_covers_logic(db: Session, covers_dir_path: str) -> dict:
    """Associate existing cover files with bibliographic records."""
    from .cover_service import find_cached_cover

    covers_dir = Path(covers_dir_path) if covers_dir_path else Path("data/covers")
    records = db.query(BiblographicRecord).filter(
        BiblographicRecord.cover_image == None,
        BiblographicRecord.isbn != None,
        BiblographicRecord.isbn != "",
    ).all()

    updated = 0
    for record in records:
        fname = find_cached_cover(record.isbn, covers_dir=covers_dir)
        if fname:
            record.cover_image = fname
            updated += 1

    if updated:
        db.commit()

    return {"updated": updated, "scanned": len(records)}


def set_acquisition_dates_from_publication_year(db: Session) -> dict:
    """Set acquisition_date to publication_year for items missing acquisition_date."""
    # Find items without acquisition_date that have a publication_year
    items = (
        db.query(Item)
        .join(BiblographicRecord)
        .filter(
            Item.acquisition_date == None,
            BiblographicRecord.publication_year != None,
        )
        .all()
    )

    updated_count = 0
    for item in items:
        year = item.bibliographic_record.publication_year
        if year and 1000 <= year <= 2100:
            item.acquisition_date = date(year, 1, 1)
            updated_count += 1

    if updated_count:
        db.commit()

    return {"updated_count": updated_count}
