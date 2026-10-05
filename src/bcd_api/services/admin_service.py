"""Admin Service

Business logic for administrative tasks, health stats, data maintenance, and DB-level updates.
"""

import logging
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.bibliographic_record import BibliographicRecord
from ..models.borrower import Borrower
from ..models.circulation import CirculationTransaction
from ..models.item import Item

logger = logging.getLogger(__name__)


def get_records_without_covers(db: Session) -> list[BibliographicRecord]:
    """Get all bibliographic records that don't have a cover image but have an ISBN."""
    return (
        db.query(BibliographicRecord)
        .filter(
            BibliographicRecord.cover_image.is_(None),
            BibliographicRecord.isbn.isnot(None),
            BibliographicRecord.isbn != "",
        )
        .all()
    )


def get_health_stats(db: Session) -> dict:
    """Get counts of core models in the system to assess health and size."""
    borrower_count = db.query(Borrower).count()
    biblio_count = db.query(BibliographicRecord).count()
    item_count = db.query(Item).count()
    circulation_count = db.query(CirculationTransaction).count()

    return {
        "borrowers": borrower_count,
        "bibliographic_records": biblio_count,
        "items": item_count,
        "circulations": circulation_count,
    }


def _cover_file_exists(covers_dir: Path, filename: str | None) -> bool:
    """Return whether ``filename`` is a regular file in the covers directory.

    ``cover_image`` stores a filename, not an arbitrary path.  Resolving the
    path before checking it also prevents a malformed database value from
    making a file outside the covers directory look like a valid cover.
    """
    if not filename:
        return False

    try:
        covers_root = covers_dir.resolve()
        cover_path = (covers_dir / filename).resolve()
        return cover_path.parent == covers_root and cover_path.is_file()
    except OSError:
        return False


def clean_broken_cover_references(db: Session, covers_dir_path: str | None) -> int:
    """Clear catalog cover references whose image file is no longer present."""
    covers_dir = Path(covers_dir_path) if covers_dir_path else Path("data/covers")
    records = (
        db.query(BibliographicRecord).filter(BibliographicRecord.cover_image.isnot(None)).all()
    )

    cleaned = 0
    for record in records:
        if record.cover_image is not None and not _cover_file_exists(
            covers_dir, record.cover_image
        ):
            record.cover_image = None
            cleaned += 1

    if cleaned:
        db.commit()

    return cleaned


def backfill_covers_logic(db: Session, covers_dir_path: str) -> dict:
    """Clean broken references and associate existing cover files.

    Clearing stale references makes those records eligible for the
    ``Download missing covers`` task again.
    """
    from .external.cover import find_cached_cover

    covers_dir = Path(covers_dir_path) if covers_dir_path else Path("data/covers")
    cleaned = clean_broken_cover_references(db, covers_dir_path)
    records = (
        db.query(BibliographicRecord)
        .filter(
            BibliographicRecord.cover_image.is_(None),
            BibliographicRecord.isbn.isnot(None),
            BibliographicRecord.isbn != "",
        )
        .all()
    )

    updated = 0
    for record in records:
        fname = find_cached_cover(record.isbn, covers_dir=covers_dir)
        if fname:
            record.cover_image = fname
            updated += 1

    if updated:
        db.commit()

    return {"updated": updated, "cleaned": cleaned, "scanned": len(records)}


def set_acquisition_dates_from_publication_year(db: Session) -> dict:
    """Set acquisition_date to publication_year for items missing acquisition_date."""
    # Find items without acquisition_date that have a publication_year
    items = (
        db.query(Item)
        .join(BibliographicRecord)
        .filter(
            Item.acquisition_date is None,
            BibliographicRecord.publication_year is not None,
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
