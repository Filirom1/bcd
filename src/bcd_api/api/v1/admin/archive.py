"""Archive and health administration endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ....core.deps import get_db

router = APIRouter()


def _services():
    from . import admin_service, archive_service

    return admin_service, archive_service


@router.get("/archive/stats")
def get_archive_stats(db: Session = Depends(get_db)):
    """Get statistics about archived circulation transactions."""
    _, archive_service = _services()
    try:
        return archive_service.get_archive_stats(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get archive stats: {str(exc)}")


@router.post("/archive")
def archive_transactions(
    older_than_years: int = 5,
    dry_run: bool = False,
    db: Session = Depends(get_db),
):
    """Archive old circulation transactions."""
    _, archive_service = _services()
    try:
        return archive_service.archive_old_transactions(
            db=db,
            older_than_years=older_than_years,
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Archive operation failed: {str(exc)}")


@router.get("/archive/transactions")
def get_archived_transactions(
    borrower_id: int = None,
    item_id: int = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Query archived circulation transactions."""
    _, archive_service = _services()
    try:
        transactions = archive_service.get_archived_transactions(
            db=db,
            borrower_id=borrower_id,
            item_id=item_id,
            limit=limit,
            offset=offset,
        )
        return {"transactions": transactions, "limit": limit, "offset": offset}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to query archived transactions: {str(exc)}"
        )


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check system health and database connectivity."""
    admin_service, _ = _services()
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "counts": admin_service.get_health_stats(db),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(exc)}")
