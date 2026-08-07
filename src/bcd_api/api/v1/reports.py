"""
Reports API Endpoints

REST API for generating library reports and statistics.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ...core.deps import get_db
from ...services import report as report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/collection-stats")
def get_collection_stats(
    crew_method: str = Query("never_borrowed"),
    min_age_years: float = Query(0.0, ge=0),
    exclude_periodicals: bool = Query(True),
    medium_type: Optional[str] = Query(None),
    target_audience: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    pub_year_min: Optional[int] = Query(None),
    pub_year_max: Optional[int] = Query(None),
    acq_year_min: Optional[int] = Query(None),
    acq_year_max: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Aggregation stats for the collection report (breakdowns + histograms).

    Returns GROUP BY counts by medium_type, target_audience, condition,
    and histograms by publication_year and acquisition_year.
    Cross-filter params (medium_type, etc.) restrict the base dataset;
    each breakdown excludes its own filter to show the full distribution.
    """
    return report_service.get_collection_stats(
        db,
        crew_method=crew_method,
        min_age_years=min_age_years,
        exclude_periodicals=exclude_periodicals,
        medium_type=medium_type,
        target_audience=target_audience,
        condition=condition,
        pub_year_min=pub_year_min,
        pub_year_max=pub_year_max,
        acq_year_min=acq_year_min,
        acq_year_max=acq_year_max,
    )


@router.get("/overdue")
def get_overdue_report(
    class_name: Optional[str] = Query(None, description="Filter by class name"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
):
    """
    Get overdue items report.

    Args:
        class_name: Optional filter by class
        academic_year: Optional filter by academic year
        limit: Number of items per page (default: 50, max: 500)
        offset: Number of items to skip (default: 0)
        db: Database session

    Returns:
        List of overdue items with borrower and item details
    """
    overdue_items, total_count = report_service.get_overdue_items(
        db, class_name=class_name, academic_year=academic_year, limit=limit, offset=offset
    )

    return {
        "total_overdue": total_count,
        "items": overdue_items,
        "limit": limit,
        "offset": offset,
    }


@router.get("/overdue/by-class")
def get_overdue_summary_by_class(
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    db: Session = Depends(get_db),
):
    """
    Get overdue summary grouped by class.

    Args:
        academic_year: Optional filter by academic year
        db: Database session

    Returns:
        List of classes with overdue counts
    """
    summary = report_service.get_overdue_summary_by_class(db, academic_year=academic_year)
    return {
        "classes": summary,
        "total_overdue": sum(c["overdue_count"] for c in summary),
    }


@router.get("/never-borrowed")
def get_never_borrowed_report(
    academic_year: Optional[str] = Query(None, description="Filter by acquisition year"),
    level: Optional[str] = Query(None, description="Filter by reading level"),
    target_audience: Optional[str] = Query(None, description="Filter by target audience (child/youth/adult)"),
    medium_type: Optional[str] = Query(None, description="Filter by medium type"),
    min_age_days: Optional[int] = Query(None, description="Minimum days since acquisition"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
):
    """
    Get items that have never been borrowed with advanced filtering.

    Args:
        academic_year: Optional filter by acquisition year

        level: Filter by reading level
        target_audience: Filter by target audience (child/youth/adult)
        medium_type: Filter by medium type
        min_age_days: Minimum days since acquisition (e.g., 180 for 6 months)
        limit: Number of items per page (default: 50, max: 500)
        offset: Number of items to skip (default: 0)
        db: Database session

    Returns:
        List of never-borrowed items with detailed information
    """
    items, total_count = report_service.get_never_borrowed_items(
        db,
        academic_year=academic_year,
        level=level,
        target_audience=target_audience,
        medium_type=medium_type,
        min_age_days=min_age_days,
        limit=limit,
        offset=offset
    )

    return {
        "total_count": total_count,
        "items": items,
        "limit": limit,
        "offset": offset,
    }


@router.get("/most-borrowed")
def get_most_borrowed_report(
    period: str = Query("year", pattern="^(week|month|year|all|all-time)$"),
    limit: int = Query(default=20, ge=1, le=500, description="Number of items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    medium_type: Optional[str] = Query(None, description="Filter by medium type"),
    target_audience: Optional[str] = Query(None, description="Filter by target audience"),
    db: Session = Depends(get_db),
):
    """
    Get most borrowed titles.

    Args:
        period: Time period (week, month, year, all)
        limit: Number of items per page (default: 20, max: 100)
        offset: Number of items to skip (default: 0)
        medium_type: Optional filter by medium type
        db: Database session

    Returns:
        List of most borrowed titles with circulation counts
    """
    titles, total_count = report_service.get_most_borrowed_titles(
        db, period=period, limit=limit, offset=offset, medium_type=medium_type,
        target_audience=target_audience,
    )

    return {
        "period": period,
        "titles": titles,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/statistics")
def get_circulation_statistics(
    period: str = Query("year", pattern="^(month|year|all-time)$"),
    db: Session = Depends(get_db),
):
    """
    Get overall circulation statistics.

    Args:
        period: Time period (month, year, all-time)
        db: Database session

    Returns:
        Dictionary with various statistics
    """
    stats = report_service.get_circulation_statistics(db, period=period)
    return stats


@router.get("/borrower/{borrower_id}/statistics")
def get_borrower_statistics(
    borrower_id: int,
    db: Session = Depends(get_db),
):
    """
    Get statistics for a specific borrower.

    Args:
        borrower_id: Borrower database ID
        db: Database session

    Returns:
        Dictionary with borrower statistics
    """
    stats = report_service.get_borrower_statistics(db, borrower_id=borrower_id)
    return stats


@router.get("/holds")
def get_holds_report(
    status: Optional[str] = Query(None, pattern="^(waiting|ready|expired|fulfilled|cancelled)$",
                                   description="Filter by hold status"),
    class_name: Optional[str] = Query(None, description="Filter by class name"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
):
    """
    Get holds/reservations report.

    Args:
        status: Optional filter by status (waiting, ready, expired, fulfilled, cancelled)
        class_name: Optional filter by class
        limit: Number of items per page (default: 50, max: 500)
        offset: Number of items to skip (default: 0)
        db: Database session

    Returns:
        List of holds with borrower and bibliographic record details
    """
    # Get all matching holds for total count
    all_holds = report_service.get_holds_report(
        db, status=status, class_name=class_name
    )
    total_count = len(all_holds)

    # Apply pagination
    holds = all_holds[offset:offset+limit]

    return {
        "total_holds": total_count,
        "items": holds,
        "limit": limit,
        "offset": offset,
    }


@router.get("/active-loans")
def get_active_loans_report(
    class_name: Optional[str] = Query(None, description="Filter by class name"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
):
    """
    Get active loans (currently checked out items) report.

    Args:
        class_name: Optional filter by class
        limit: Number of items per page (default: 50, max: 500)
        offset: Number of items to skip (default: 0)
        db: Database session

    Returns:
        List of active loans with borrower and item details
    """
    # Get all active loans for total count
    all_loans = report_service.get_active_loans(db, class_name=class_name)
    total_count = len(all_loans)

    # Apply pagination
    loans = all_loans[offset:offset+limit]

    return {
        "total_active_loans": total_count,
        "items": loans,
        "limit": limit,
        "offset": offset,
    }
