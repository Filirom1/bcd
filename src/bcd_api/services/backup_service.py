"""
Database Backup and Restore Service

Provides comprehensive backup functionality for the BCD SQLite database.
Implements FR-048: System MUST support backup and restore.

Features:
- Create timestamped backups
- Restore from backup files
- List available backups with metadata
- Cleanup old backups
- Verify backup integrity
"""

import logging
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config import settings
from ..core.database import engine

logger = logging.getLogger(__name__)


class BackupMetadata:
    """Metadata for a backup file"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.filename = file_path.name
        self.size_bytes = file_path.stat().st_size
        self.created_at = datetime.fromtimestamp(file_path.stat().st_mtime)

    @property
    def size_mb(self) -> float:
        """File size in megabytes"""
        return round(self.size_bytes / (1024 * 1024), 2)

    @property
    def age_days(self) -> int:
        """Age of backup in days"""
        return (datetime.now() - self.created_at).days

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "filename": self.filename,
            "file_path": str(self.file_path),
            "size_mb": self.size_mb,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "age_days": self.age_days
        }


def get_database_path() -> Path:
    """Get the path to the SQLite database file"""
    # Extract database path from connection URL
    db_url = settings.database_url

    if db_url.startswith("sqlite:///"):
        # Remove sqlite:/// prefix
        db_path = db_url.replace("sqlite:///", "")
        # Handle relative paths (./bcd.db) and absolute paths
        if db_path.startswith("./"):
            db_path = db_path[2:]  # Remove ./
        return Path(db_path).resolve()
    else:
        raise ValueError("Backup service only supports SQLite databases")


def create_backup(output_path: Optional[str] = None) -> BackupMetadata:
    """
    Create a backup of the database.

    Args:
        output_path: Optional custom backup path. If None, creates timestamped backup
                    in ./backups/ directory

    Returns:
        BackupMetadata: Metadata about the created backup

    Raises:
        ValueError: If database is not SQLite
        IOError: If backup creation fails
    """
    try:
        db_path = get_database_path()

        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

        # Determine output path
        if output_path is None:
            # Create backups directory if it doesn't exist
            backup_dir = Path("./backups")
            backup_dir.mkdir(exist_ok=True)

            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = backup_dir / f"bcd_backup_{timestamp}.db"
        else:
            output_file = Path(output_path)
            # Create parent directory if it doesn't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)

        # Perform backup using SQLite's backup API (more reliable than file copy).
        # No need to close SQLAlchemy connections: the SQLite backup API is designed
        # for online backups and is safe with WAL mode and concurrent connections.
        logger.info(f"Creating backup: {db_path} -> {output_file}")

        # Use SQLite backup API for consistent backup
        source_conn = sqlite3.connect(str(db_path))
        dest_conn = sqlite3.connect(str(output_file))

        with source_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        # Verify backup was created
        if not output_file.exists():
            raise IOError(f"Backup file was not created: {output_file}")

        metadata = BackupMetadata(output_file)
        logger.info(f"Backup created successfully: {output_file} ({metadata.size_mb} MB)")

        return metadata

    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        raise


def restore_backup(backup_file: str) -> bool:
    """
    Restore database from a backup file.

    DANGEROUS OPERATION: This will overwrite the current database!

    Args:
        backup_file: Path to the backup file to restore

    Returns:
        bool: True if restore successful

    Raises:
        FileNotFoundError: If backup file doesn't exist
        ValueError: If backup file is invalid
        IOError: If restore fails
    """
    try:
        backup_path = Path(backup_file)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Verify backup file is valid SQLite database
        if not verify_backup(str(backup_path)):
            raise ValueError(f"Backup file is not a valid SQLite database: {backup_path}")

        db_path = get_database_path()

        # Create a safety backup of current database before restore
        safety_backup_dir = Path("./backups/pre_restore")
        safety_backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_backup = safety_backup_dir / f"pre_restore_{timestamp}.db"

        logger.warning(f"Creating safety backup before restore: {safety_backup}")
        shutil.copy2(db_path, safety_backup)

        # Close all connections
        engine.dispose()

        # Perform restore
        logger.warning(f"Restoring database from backup: {backup_path}")
        shutil.copy2(backup_path, db_path)

        # Verify restored database
        restored_conn = sqlite3.connect(str(db_path))
        cursor = restored_conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        restored_conn.close()

        if result[0] != "ok":
            # Restore failed, rollback to safety backup
            logger.error(f"Restored database integrity check failed: {result}")
            logger.warning("Rolling back to safety backup")
            shutil.copy2(safety_backup, db_path)
            raise IOError("Database restore failed integrity check")

        logger.info(f"Database restored successfully from {backup_path}")
        logger.info(f"Safety backup available at: {safety_backup}")

        return True

    except Exception as e:
        logger.error(f"Database restore failed: {str(e)}")
        raise


def list_backups(backup_dir: str = "./backups") -> List[BackupMetadata]:
    """
    List all available backup files.

    Args:
        backup_dir: Directory to search for backups (default: ./backups)

    Returns:
        List[BackupMetadata]: List of backup metadata, sorted by creation time (newest first)
    """
    backup_path = Path(backup_dir)

    if not backup_path.exists():
        logger.info(f"Backup directory does not exist: {backup_path}")
        return []

    # Find all .db files in backup directory
    backup_files = sorted(
        backup_path.glob("*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Newest first
    )

    backups = [BackupMetadata(f) for f in backup_files]

    logger.info(f"Found {len(backups)} backup files in {backup_path}")
    return backups


def cleanup_old_backups(keep_days: int = 30, backup_dir: str = "./backups") -> int:
    """
    Remove backup files older than specified days.

    Args:
        keep_days: Number of days to keep backups (default: 30)
        backup_dir: Directory containing backups (default: ./backups)

    Returns:
        int: Number of backups deleted
    """
    backups = list_backups(backup_dir)
    deleted_count = 0
    cutoff_date = datetime.now() - timedelta(days=keep_days)

    for backup in backups:
        if backup.created_at < cutoff_date:
            logger.info(f"Deleting old backup: {backup.filename} (age: {backup.age_days} days)")
            try:
                backup.file_path.unlink()
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete {backup.filename}: {str(e)}")

    logger.info(f"Cleanup complete: deleted {deleted_count} old backups (older than {keep_days} days)")
    return deleted_count


def verify_backup(backup_file: str) -> bool:
    """
    Verify backup file integrity using SQLite PRAGMA integrity_check.

    Args:
        backup_file: Path to backup file to verify

    Returns:
        bool: True if backup is valid, False otherwise
    """
    try:
        backup_path = Path(backup_file)

        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        # Open backup file and run integrity check
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()

        is_valid = result[0] == "ok"

        if is_valid:
            logger.info(f"Backup verification passed: {backup_path}")
        else:
            logger.error(f"Backup verification failed: {backup_path} - {result}")

        return is_valid

    except sqlite3.DatabaseError as e:
        logger.error(f"Backup file is not a valid SQLite database: {backup_file} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Backup verification error: {str(e)}")
        return False


def get_database_size() -> Dict[str, float]:
    """
    Get current database size information.

    Returns:
        Dict with database size in bytes and MB
    """
    try:
        db_path = get_database_path()
        size_bytes = db_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        return {
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "path": str(db_path)
        }
    except Exception as e:
        logger.error(f"Failed to get database size: {str(e)}")
        return {"size_bytes": 0, "size_mb": 0.0, "path": "unknown"}
