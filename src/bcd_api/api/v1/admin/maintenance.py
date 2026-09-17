"""Data-maintenance administration endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....core.deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/data-maintenance/set-acquisition-dates")
def set_acquisition_dates_from_publication_year(db: Session = Depends(get_db)):
    """Set missing acquisition dates from publication years."""
    from . import admin_service

    result = admin_service.set_acquisition_dates_from_publication_year(db)
    logger.info("Acquisition date maintenance: %s items updated", result["updated_count"])
    return result
