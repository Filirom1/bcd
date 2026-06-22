"""
Archive Service

Business logic for archiving old circulation transactions to prevent database bloat.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.circulation import CirculationTransaction

logger = logging.getLogger(__name__)


def archive_old_transactions(
    db: Session,
    older_than_years: int = 5,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Archive circulation transactions older than specified years.

    Args:
        db: Database session
        older_than_years: Archive transactions older than this many years (default: 5)
        dry_run: If True, only return count without actually archiving

    Returns:
        Dict with archived_count, oldest_date, newest_date, size_reduction_estimate

    Raises:
        ValueError: If older_than_years is invalid
    """
    if older_than_years < 1:
        raise ValueError("older_than_years must be at least 1")

    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_years * 365)

    # Count transactions to be archived
    count_query = db.query(CirculationTransaction).filter(
        CirculationTransaction.checkout_date < cutoff_date
    )
    total_count = count_query.count()

    if total_count == 0:
        return {
            "archived_count": 0,
            "oldest_date": None,
            "newest_date": None,
            "size_reduction_estimate_mb": 0,
            "dry_run": dry_run
        }

    # Get date range of transactions to be archived
    oldest = count_query.order_by(CirculationTransaction.checkout_date.asc()).first()
    newest = count_query.order_by(CirculationTransaction.checkout_date.desc()).first()

    oldest_date = oldest.checkout_date if oldest else None
    newest_date = newest.checkout_date if newest else None

    # Estimate size reduction (rough estimate: ~500 bytes per transaction)
    size_reduction_mb = (total_count * 500) / (1024 * 1024)

    if dry_run:
        return {
            "archived_count": total_count,
            "oldest_date": oldest_date,
            "newest_date": newest_date,
            "size_reduction_estimate_mb": round(size_reduction_mb, 2),
            "dry_run": True
        }

    # Perform actual archiving using INSERT ... SELECT
    archived_at = datetime.now(timezone.utc)

    # Use raw SQL for efficient bulk insert
    archive_sql = text("""
        INSERT INTO circulation_transaction_archive (
            id, borrower_id, item_id, bibliographic_record_id,
            checkout_date, due_date, return_date, status, renewal_count,
            checked_out_by, returned_by, notes, created_at, updated_at, archived_at
        )
        SELECT
            id, borrower_id, item_id, bibliographic_record_id,
            checkout_date, due_date, return_date, status, renewal_count,
            checked_out_by, returned_by, notes, created_at, updated_at, :archived_at
        FROM circulation_transaction
        WHERE checkout_date < :cutoff_date
    """)

    db.execute(archive_sql, {"archived_at": archived_at, "cutoff_date": cutoff_date})

    # Delete archived transactions from main table
    delete_sql = text("""
        DELETE FROM circulation_transaction
        WHERE checkout_date < :cutoff_date
    """)

    result = db.execute(delete_sql, {"cutoff_date": cutoff_date})
    db.commit()

    return {
        "archived_count": total_count,
        "oldest_date": oldest_date,
        "newest_date": newest_date,
        "size_reduction_estimate_mb": round(size_reduction_mb, 2),
        "dry_run": False
    }


def get_archived_transactions(
    db: Session,
    borrower_id: Optional[int] = None,
    item_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Query archived circulation transactions.

    Args:
        db: Database session
        borrower_id: Filter by borrower ID (optional)
        item_id: Filter by item ID (optional)
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List of archived transaction dictionaries
    """
    # Build query
    query = text("""
        SELECT
            id, borrower_id, item_id, bibliographic_record_id,
            checkout_date, due_date, return_date, status, renewal_count,
            checked_out_by, returned_by, notes, created_at, updated_at, archived_at
        FROM circulation_transaction_archive
        WHERE 1=1
        """ + (
            " AND borrower_id = :borrower_id" if borrower_id else ""
        ) + (
            " AND item_id = :item_id" if item_id else ""
        ) + """
        ORDER BY checkout_date DESC
        LIMIT :limit OFFSET :offset
    """)

    params = {"limit": limit, "offset": offset}
    if borrower_id:
        params["borrower_id"] = borrower_id
    if item_id:
        params["item_id"] = item_id

    result = db.execute(query, params)

    return [dict(row._mapping) for row in result]


def get_archive_stats(db: Session) -> Dict[str, Any]:
    """
    Get statistics about archived transactions.

    Args:
        db: Database session

    Returns:
        Dict with count, oldest_archived, newest_archived, total_size_mb
    """
    stats_query = text("""
        SELECT
            COUNT(*) as total_count,
            MIN(checkout_date) as oldest_date,
            MAX(checkout_date) as newest_date,
            MIN(archived_at) as first_archived_at,
            MAX(archived_at) as last_archived_at
        FROM circulation_transaction_archive
    """)

    result = db.execute(stats_query).fetchone()

    if not result or result[0] == 0:
        return {
            "total_archived": 0,
            "oldest_transaction_date": None,
            "newest_transaction_date": None,
            "first_archived_at": None,
            "last_archived_at": None,
            "estimated_size_mb": 0
        }

    total_count = result[0]
    estimated_size_mb = (total_count * 500) / (1024 * 1024)

    return {
        "total_archived": total_count,
        "oldest_transaction_date": result[1],
        "newest_transaction_date": result[2],
        "first_archived_at": result[3],
        "last_archived_at": result[4],
        "estimated_size_mb": round(estimated_size_mb, 2)
    }
