"""
Report Service

Business logic for generating library reports and statistics.
"""

import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, case

from ..models.circulation import CirculationTransaction
from ..models.borrower import Borrower
from ..models.bibliographic_record import BiblographicRecord
from ..models.item import Item
from ..models.class_model import Class
from ..models.hold import Hold


def _deserialize_authors(authors) -> str:
    """Helper function to deserialize authors JSON field."""
    if isinstance(authors, str):
        try:
            authors_list = json.loads(authors)
            return ", ".join(authors_list) if authors_list else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def get_collection_stats(
    db: Session,
    crew_method: str = "never_borrowed",
    min_age_years: float = 0.0,
    exclude_periodicals: bool = True,
    genre: Optional[str] = None,
    medium_type: Optional[str] = None,
    target_audience: Optional[str] = None,
    condition: Optional[str] = None,
    pub_year_min: Optional[int] = None,
    pub_year_max: Optional[int] = None,
    acq_year_min: Optional[int] = None,
    acq_year_max: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute aggregation stats for the collection report (breakdowns + histograms).

    Returns GROUP BY counts by genre, medium_type, target_audience, condition,
    plus histograms by publication_year and acquisition_year.

    Args:
        db: Database session
        crew_method: 'never_borrowed' or 'low_circulation' or 'damaged_old' etc.
        min_age_years: Minimum age in collection (years); 0 = no filter
        exclude_periodicals: Exclude items with medium_type = 'Périodique'
        genre: Cross-filter by genre
        medium_type: Cross-filter by medium_type
        target_audience: Cross-filter by target_audience
        condition: Cross-filter by condition
        pub_year_min: Cross-filter by publication_year (min)
        pub_year_max: Cross-filter by publication_year (max)
        acq_year_min: Cross-filter by acquisition year (min)
        acq_year_max: Cross-filter by acquisition year (max)

    Returns:
        dict with breakdowns and histograms
    """
    today = date.today()

    def _base_query(db, exclude_genre=False, exclude_medium_type=False,
                    exclude_target_audience=False, exclude_condition=False,
                    exclude_pub_year=False, exclude_acq_year=False):
        """Build the base filtered query for aggregations."""
        q = db.query(Item, BiblographicRecord).join(
            BiblographicRecord, Item.bibliographic_record_id == BiblographicRecord.id
        )

        # CREW method filter
        if crew_method == "never_borrowed":
            q = q.filter(Item.last_borrowed_at.is_(None))
        elif crew_method == "low_circulation":
            since = date(today.year - 2, today.month, today.day)
            loan_counts = (
                db.query(CirculationTransaction.item_id, func.count().label("cnt"))
                .filter(CirculationTransaction.checkout_date >= since)
                .group_by(CirculationTransaction.item_id)
                .subquery()
            )
            q = q.outerjoin(loan_counts, loan_counts.c.item_id == Item.id)
            q = q.filter(func.coalesce(loan_counts.c.cnt, 0) <= 2)
        elif crew_method == "damaged_old":
            q = q.filter(Item.condition == "damaged")
            if min_age_years <= 0:
                cutoff = date(today.year - 3, today.month, today.day)
                q = q.filter(Item.acquisition_date <= cutoff)
        elif crew_method == "never_inventoried":
            q = q.filter(Item.last_inventoried_at.is_(None))

        # Ancienneté filter (skip if already applied by damaged_old)
        if min_age_years > 0 and crew_method != "damaged_old":
            days = int(min_age_years * 365.25)
            cutoff = today - timedelta(days=days)
            q = q.filter(Item.acquisition_date.isnot(None))
            q = q.filter(Item.acquisition_date <= cutoff)

        # Exclude periodicals
        if exclude_periodicals:
            q = q.filter(BiblographicRecord.medium_type != "Périodique")

        # Cross-filters (each excluded for its own breakdown query)
        if genre and not exclude_genre:
            q = q.filter(BiblographicRecord.genre == genre)
        if medium_type and not exclude_medium_type:
            q = q.filter(BiblographicRecord.medium_type == medium_type)
        if target_audience and not exclude_target_audience:
            q = q.filter(BiblographicRecord.target_audience == target_audience)
        if condition and not exclude_condition:
            q = q.filter(Item.condition == condition)
        if pub_year_min is not None and not exclude_pub_year:
            q = q.filter(BiblographicRecord.publication_year >= pub_year_min)
        if pub_year_max is not None and not exclude_pub_year:
            q = q.filter(BiblographicRecord.publication_year <= pub_year_max)
        if acq_year_min is not None and not exclude_acq_year:
            q = q.filter(func.strftime("%Y", Item.acquisition_date) >= str(acq_year_min))
        if acq_year_max is not None and not exclude_acq_year:
            q = q.filter(func.strftime("%Y", Item.acquisition_date) <= str(acq_year_max))

        return q

    def _breakdown(q, group_col, label_col=None):
        """Run a GROUP BY count + damaged_count on the query."""
        col = label_col or group_col
        rows = (
            q.with_entities(
                col,
                func.count(Item.id).label("count"),
                func.sum(case((Item.condition == "damaged", 1), else_=0)).label("damaged_count"),
            )
            .filter(col.isnot(None))
            .group_by(col)
            .order_by(func.count(Item.id).desc())
            .all()
        )
        return [{"value": r[0], "count": r[1], "damaged_count": r[2] or 0} for r in rows]

    # Each breakdown excludes its own filter so the full distribution is visible
    genre_rows = _breakdown(_base_query(db, exclude_genre=True), BiblographicRecord.genre)
    medium_rows = _breakdown(_base_query(db, exclude_medium_type=True), BiblographicRecord.medium_type)
    audience_rows = _breakdown(_base_query(db, exclude_target_audience=True), BiblographicRecord.target_audience)
    condition_rows = _breakdown(_base_query(db, exclude_condition=True), Item.condition)

    # Publication year histogram (pub_year is INTEGER — direct GROUP BY)
    pub_q = _base_query(db, exclude_pub_year=True)
    pub_rows = (
        pub_q.with_entities(
            BiblographicRecord.publication_year,
            func.count(Item.id).label("count"),
            func.sum(case((Item.condition == "damaged", 1), else_=0)).label("damaged_count"),
        )
        .filter(BiblographicRecord.publication_year.isnot(None))
        .group_by(BiblographicRecord.publication_year)
        .order_by(BiblographicRecord.publication_year)
        .all()
    )
    pub_histogram = [{"year": r[0], "count": r[1], "damaged_count": r[2] or 0} for r in pub_rows]

    # Acquisition year histogram (acquisition_date is Date — use strftime)
    acq_q = _base_query(db, exclude_acq_year=True)
    acq_rows = (
        acq_q.with_entities(
            func.strftime("%Y", Item.acquisition_date).label("acq_year"),
            func.count(Item.id).label("count"),
            func.sum(case((Item.condition == "damaged", 1), else_=0)).label("damaged_count"),
        )
        .filter(Item.acquisition_date.isnot(None))
        .group_by("acq_year")
        .order_by("acq_year")
        .all()
    )
    acq_histogram = [{"year": int(r[0]), "count": r[1], "damaged_count": r[2] or 0} for r in acq_rows]

    # Total count (all filters applied)
    total = _base_query(db).count()

    return {
        "total_count": total,
        "breakdowns": {
            "genre": genre_rows,
            "medium_type": medium_rows,
            "target_audience": audience_rows,
            "condition": condition_rows,
        },
        "pub_year_histogram": pub_histogram,
        "acq_year_histogram": acq_histogram,
    }


def get_overdue_items(
    db: Session,
    class_name: Optional[str] = None,
    academic_year: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all currently overdue items.

    Args:
        db: Database session
        class_name: Optional filter by class name
        academic_year: Deprecated (Class model no longer has academic_year field)

    Returns:
        List of overdue items with borrower and item details
    """
    today = datetime.utcnow().date()

    # Query for active loans that are overdue
    query = db.query(
        CirculationTransaction,
        Borrower,
        Item,
        BiblographicRecord,
        Class,
    ).join(
        Borrower, CirculationTransaction.borrower_id == Borrower.id
    ).join(
        Item, CirculationTransaction.item_id == Item.id
    ).join(
        BiblographicRecord, Item.bibliographic_record_id == BiblographicRecord.id
    ).outerjoin(
        Class, Borrower.class_id == Class.id
    ).filter(
        and_(
            CirculationTransaction.return_date.is_(None),  # Not returned
            CirculationTransaction.due_date < today,  # Overdue
        )
    )

    # Apply filters
    if class_name:
        query = query.filter(Class.name == class_name)
    # Note: academic_year filter removed - Class model no longer has this field

    # Order by due date (oldest first)
    query = query.order_by(CirculationTransaction.due_date)

    results = query.all()

    # Format results
    overdue_items = []
    for circ, borrower, item, biblio, class_obj in results:
        days_overdue = (today - circ.due_date).days

        overdue_items.append({
            "circulation_id": circ.id,
            "borrower_id": borrower.borrower_id,
            "borrower_name": borrower.full_name,
            "class_name": class_obj.name if class_obj else None,
            "item_id": item.item_id,
            "record_id": biblio.id,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "checkout_date": circ.checkout_date.date(),
            "due_date": circ.due_date,
            "days_overdue": days_overdue,
        })

    return overdue_items


def get_overdue_summary_by_class(
    db: Session,
    academic_year: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get summary of overdue items grouped by class.

    Args:
        db: Database session
        academic_year: Deprecated (Class model no longer has academic_year field)

    Returns:
        List of class summaries with overdue counts
    """
    today = datetime.utcnow().date()

    # Query for overdue counts by class
    query = db.query(
        Class.name,
        func.count(CirculationTransaction.id).label("overdue_count"),
    ).join(
        Borrower, Class.id == Borrower.class_id
    ).join(
        CirculationTransaction, Borrower.id == CirculationTransaction.borrower_id
    ).filter(
        and_(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < today,
        )
    ).group_by(Class.name)

    # Note: academic_year filter removed - Class model no longer has this field

    query = query.order_by(Class.name)

    results = query.all()

    return [
        {"class_name": class_name, "overdue_count": count}
        for class_name, count in results
    ]


def get_never_borrowed_items(
    db: Session,
    academic_year: Optional[str] = None,
    genre: Optional[str] = None,
    level: Optional[str] = None,
    target_audience: Optional[str] = None,
    medium_type: Optional[str] = None,
    min_age_days: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get items that have never been borrowed with advanced filtering.

    Args:
        db: Database session
        academic_year: Optional filter by academic year (acquisition date)
        genre: Filter by genre
        level: Filter by reading level
        target_audience: Filter by target audience (child/youth/adult)
        medium_type: Filter by medium type
        min_age_days: Minimum days since acquisition (e.g., 180 for 6 months)
        limit: Maximum number of results

    Returns:
        List of never-borrowed items with detailed information
    """
    # Subquery to get items that have been borrowed
    borrowed_items = db.query(CirculationTransaction.item_id).distinct()

    # Query for items never borrowed
    query = db.query(
        BiblographicRecord,
        Item,
    ).join(
        Item, BiblographicRecord.id == Item.bibliographic_record_id
    ).filter(
        Item.id.notin_(borrowed_items)
    )

    # Filter by acquisition year if specified
    if academic_year:
        # Parse academic year (e.g., "2025-2026" -> start in 2025)
        if "-" in academic_year:
            start_year = int(academic_year.split("-")[0])
            start_date = date(start_year, 9, 1)  # September 1st
            end_date = date(start_year + 1, 8, 31)  # August 31st next year

            query = query.filter(
                and_(
                    Item.acquisition_date >= start_date,
                    Item.acquisition_date <= end_date,
                )
            )

    # Filter by genre
    if genre:
        query = query.filter(BiblographicRecord.genre.ilike(f"%{genre}%"))

    # Filter by level
    if level:
        query = query.filter(BiblographicRecord.level.ilike(f"%{level}%"))

    # Filter by target audience
    if target_audience:
        query = query.filter(BiblographicRecord.target_audience == target_audience)

    # Filter by medium type
    if medium_type:
        query = query.filter(BiblographicRecord.medium_type == medium_type)

    # Filter by minimum age
    if min_age_days:
        cutoff_date = date.today() - timedelta(days=min_age_days)
        query = query.filter(Item.acquisition_date <= cutoff_date)

    query = query.order_by(BiblographicRecord.title).limit(limit)

    results = query.all()

    never_borrowed = []
    today = date.today()

    for biblio, item in results:
        # Calculate age in days
        age_days = None
        if item.acquisition_date:
            age_days = (today - item.acquisition_date).days

        never_borrowed.append({
            "bibliographic_record_id": biblio.id,
            "item_id": item.item_id,
            "item_barcode": item.item_id,  # Alias for template compatibility
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "publisher": biblio.publisher,
            "genre": biblio.genre,
            "level": biblio.level,
            "target_audience": biblio.target_audience,
            "medium_type": biblio.medium_type,
            "language": biblio.language,
            "publication_year": biblio.publication_year,
            "acquisition_date": item.acquisition_date,
            "age_days": age_days,
            "call_number": item.call_number,
            "shelf_location": item.shelf_location,
            "status": item.status,
            "condition": item.condition,
            "loanable": item.loanable,
        })

    return never_borrowed


def get_most_borrowed_titles(
    db: Session,
    period: str = "year",  # "month", "year", "all-time"
    limit: int = 20,
    medium_type: Optional[str] = None,
    genre: Optional[str] = None,
    target_audience: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get most borrowed titles by circulation count.

    Args:
        db: Database session
        period: Time period ("month", "year", "all-time")
        limit: Maximum number of results
        medium_type: Optional medium type filter

    Returns:
        List of most borrowed titles with counts
    """
    # Determine date cutoff based on period
    today = datetime.utcnow()
    if period == "week":
        cutoff_date = today - timedelta(days=7)
    elif period == "month":
        cutoff_date = today - timedelta(days=30)
    elif period == "year":
        cutoff_date = today - timedelta(days=365)
    else:  # "all", "all-time"
        cutoff_date = None

    # Query for circulation counts by bibliographic record
    query = db.query(
        BiblographicRecord.id,
        BiblographicRecord.title,
        BiblographicRecord.authors,
        BiblographicRecord.publisher,
        BiblographicRecord.publication_year,
        BiblographicRecord.medium_type,
        BiblographicRecord.genre,
        BiblographicRecord.target_audience,
        func.count(CirculationTransaction.id).label("checkout_count"),
    ).join(
        Item, BiblographicRecord.id == Item.bibliographic_record_id
    ).join(
        CirculationTransaction, Item.id == CirculationTransaction.item_id
    )

    if cutoff_date:
        query = query.filter(CirculationTransaction.checkout_date >= cutoff_date)

    if medium_type:
        query = query.filter(BiblographicRecord.medium_type == medium_type)

    if genre:
        query = query.filter(BiblographicRecord.genre == genre)

    if target_audience:
        query = query.filter(BiblographicRecord.target_audience == target_audience)

    query = query.group_by(
        BiblographicRecord.id,
        BiblographicRecord.title,
        BiblographicRecord.authors,
        BiblographicRecord.publisher,
        BiblographicRecord.publication_year,
        BiblographicRecord.medium_type,
        BiblographicRecord.genre,
        BiblographicRecord.target_audience,
    ).order_by(
        desc("checkout_count")
    ).limit(limit)

    results = query.all()

    most_borrowed = []
    for biblio_id, title, authors, publisher, pub_year, med_type, genre_val, audience_val, count in results:
        # Count total copies for this bibliographic record
        total_copies = db.query(func.count(Item.id)).filter(
            Item.bibliographic_record_id == biblio_id
        ).scalar()

        most_borrowed.append({
            "bibliographic_record_id": biblio_id,
            "title": title,
            "author": _deserialize_authors(authors),
            "publisher": publisher,
            "publication_year": pub_year,
            "medium_type": med_type,
            "genre": genre_val,
            "target_audience": audience_val,
            "checkout_count": count,
            "total_copies": total_copies,
            "rank": len(most_borrowed) + 1,
        })

    return most_borrowed


def get_circulation_statistics(
    db: Session,
    period: str = "year",
) -> Dict[str, Any]:
    """
    Get overall circulation statistics.

    Args:
        db: Database session
        period: Time period ("month", "year", "all-time")

    Returns:
        Dictionary with various statistics
    """
    # Determine date cutoff
    today = datetime.utcnow()
    if period == "month":
        cutoff_date = today - timedelta(days=30)
        period_label = "Last 30 days"
    elif period == "year":
        cutoff_date = today - timedelta(days=365)
        period_label = "Last year"
    else:
        cutoff_date = None
        period_label = "All time"

    # Base query with optional date filter
    base_query = db.query(CirculationTransaction)
    if cutoff_date:
        base_query = base_query.filter(CirculationTransaction.checkout_date >= cutoff_date)

    # Total checkouts
    total_checkouts = base_query.count()

    # Items currently on loan
    items_on_loan = db.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.is_(None)
    ).count()

    # Overdue items
    overdue_count = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < datetime.utcnow().date(),
        )
    ).count()

    # Active borrowers (with current loans)
    active_borrowers = db.query(
        func.count(func.distinct(CirculationTransaction.borrower_id))
    ).filter(
        CirculationTransaction.return_date.is_(None)
    ).scalar()

    # Average loans per day (if period specified)
    avg_loans_per_day = None
    if cutoff_date:
        days = (today - cutoff_date).days
        if days > 0:
            avg_loans_per_day = round(total_checkouts / days, 2)

    # Renewals count
    renewals_count = base_query.filter(CirculationTransaction.renewal_count > 0).count()

    # Late returns (returned after due date)
    late_returns = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.return_date.isnot(None),
            CirculationTransaction.return_date > CirculationTransaction.due_date,
        )
    )
    if cutoff_date:
        late_returns = late_returns.filter(CirculationTransaction.checkout_date >= cutoff_date)
    late_returns_count = late_returns.count()

    # Calculate late return rate
    returned_items = db.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.isnot(None)
    )
    if cutoff_date:
        returned_items = returned_items.filter(CirculationTransaction.checkout_date >= cutoff_date)
    returned_count = returned_items.count()

    late_return_rate = (
        round((late_returns_count / returned_count) * 100, 1) if returned_count > 0 else 0
    )

    return {
        "period": period_label,
        "total_checkouts": total_checkouts,
        "items_on_loan": items_on_loan,
        "overdue_items": overdue_count,
        "active_borrowers": active_borrowers,
        "average_loans_per_day": avg_loans_per_day,
        "renewals": renewals_count,
        "late_returns": late_returns_count,
        "late_return_rate": late_return_rate,
        "returned_items": returned_count,
    }


def get_borrower_statistics(
    db: Session,
    borrower_id: int,
) -> Dict[str, Any]:
    """
    Get statistics for a specific borrower.

    Args:
        db: Database session
        borrower_id: Borrower database ID

    Returns:
        Dictionary with borrower statistics
    """
    # Total checkouts
    total_checkouts = db.query(CirculationTransaction).filter(
        CirculationTransaction.borrower_id == borrower_id
    ).count()

    # Current loans
    current_loans = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.is_(None),
        )
    ).count()

    # Overdue items
    overdue = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date < datetime.utcnow().date(),
        )
    ).count()

    # Total renewals
    total_renewals = db.query(
        func.sum(CirculationTransaction.renewal_count)
    ).filter(
        CirculationTransaction.borrower_id == borrower_id
    ).scalar() or 0

    # Late returns
    late_returns = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.isnot(None),
            CirculationTransaction.return_date > CirculationTransaction.due_date,
        )
    ).count()

    # Returned items
    returned = db.query(CirculationTransaction).filter(
        and_(
            CirculationTransaction.borrower_id == borrower_id,
            CirculationTransaction.return_date.isnot(None),
        )
    ).count()

    # Late return rate
    late_return_rate = round((late_returns / returned) * 100, 1) if returned > 0 else 0

    return {
        "total_checkouts": total_checkouts,
        "current_loans": current_loans,
        "overdue_items": overdue,
        "total_renewals": int(total_renewals),
        "late_returns": late_returns,
        "late_return_rate": late_return_rate,
    }


def get_holds_report(
    db: Session,
    status: Optional[str] = None,
    class_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get holds/reservations report with filtering by status and class.

    By default (no status filter), only returns active holds (waiting, ready, expired)
    to reduce load. Use status filter to see completed holds (fulfilled, cancelled).

    Args:
        db: Database session
        status: Optional filter by status (waiting, ready, expired, fulfilled, cancelled)
                If None, returns only active holds (excludes fulfilled and cancelled)
        class_name: Optional filter by borrower's class name

    Returns:
        List of holds with borrower, bibliographic record, and queue details
    """
    # Build query with joins
    query = db.query(Hold, Borrower, BiblographicRecord, Class).join(
        Borrower, Hold.borrower_id == Borrower.id
    ).join(
        BiblographicRecord, Hold.bibliographic_record_id == BiblographicRecord.id
    ).outerjoin(
        Class, Borrower.class_id == Class.id
    )

    # Apply filters
    if status:
        query = query.filter(Hold.status == status)
    else:
        # By default, exclude completed holds (fulfilled, cancelled) to reduce load
        query = query.filter(Hold.status.in_(["waiting", "ready", "expired"]))

    if class_name:
        query = query.filter(Class.name == class_name)

    # Execute query
    results = query.order_by(Hold.status, Hold.queue_position).all()

    # Format results
    today = date.today()
    holds_list = []
    for hold, borrower, biblio, class_obj in results:
        hold_dict = {
            "hold_id": hold.id,
            "borrower_id": borrower.borrower_id,
            "borrower_name": borrower.full_name,
            "class_name": class_obj.name if class_obj else None,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "status": hold.status,
            "hold_date": hold.hold_date,
            "queue_position": hold.queue_position,
        }

        # Add ready-specific fields
        if hold.status == "ready":
            hold_dict["available_date"] = hold.available_date
            hold_dict["expiration_date"] = hold.expiration_date
            if hold.expiration_date:
                days_until_expiration = (hold.expiration_date - today).days
                hold_dict["days_until_expiration"] = days_until_expiration

        holds_list.append(hold_dict)

    return holds_list


def get_active_loans(
    db: Session,
    class_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all active loans (items currently checked out).

    Args:
        db: Database session
        class_name: Optional filter by borrower's class name

    Returns:
        List of active loans with borrower and item details
    """
    # Build query with joins
    query = db.query(CirculationTransaction, Borrower, Item, BiblographicRecord, Class).join(
        Borrower, CirculationTransaction.borrower_id == Borrower.id
    ).join(
        Item, CirculationTransaction.item_id == Item.id
    ).join(
        BiblographicRecord, CirculationTransaction.bibliographic_record_id == BiblographicRecord.id
    ).outerjoin(
        Class, Borrower.class_id == Class.id
    ).filter(
        CirculationTransaction.return_date.is_(None)  # Active loans only
    )

    # Apply filter
    if class_name:
        query = query.filter(Class.name == class_name)

    # Execute query, order by due date (most urgent first)
    results = query.order_by(CirculationTransaction.due_date).all()

    # Format results
    today = date.today()
    loans_list = []
    for circ, borrower, item, biblio, class_obj in results:
        days_until_due = (circ.due_date - today).days
        is_overdue = circ.due_date < today

        loans_list.append({
            "circulation_id": circ.id,
            "borrower_id": borrower.borrower_id,
            "borrower_name": borrower.full_name,
            "class_name": class_obj.name if class_obj else None,
            "item_id": item.item_id,
            "bibliographic_record_id": biblio.id,
            "title": biblio.title,
            "authors": _deserialize_authors(biblio.authors),
            "checkout_date": circ.checkout_date,
            "due_date": circ.due_date,
            "days_until_due": days_until_due,
            "is_overdue": is_overdue,
            "renewal_count": circ.renewal_count,
        })

    return loans_list
