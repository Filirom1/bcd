"""Logging configuration for BCD API."""

import logging
import logging.config
from pathlib import Path

from .config import settings


class CleanLoggerNameFormatter(logging.Formatter):
    """Custom formatter that cleans up confusing logger names."""

    def format(self, record):
        # Replace "uvicorn.error" with "uvicorn" to avoid confusion
        # (uvicorn uses "uvicorn.error" logger even for INFO messages)
        if record.name == "uvicorn.error":
            record = logging.makeLogRecord(record.__dict__)
            record.name = "uvicorn"
        return super().format(record)


def _get_log_dir() -> Path:
    """Return the log directory, portable-aware."""
    try:
        from .portable import get_app_dir, is_portable
        if is_portable():
            return get_app_dir() / "logs"
    except ImportError:
        pass
    return Path("logs")


def _rotate_log(log_file: Path) -> None:
    """Rotate log on startup: bcd.log.1 is deleted, bcd.log becomes bcd.log.1."""
    backup = Path(str(log_file) + ".1")
    if backup.exists():
        backup.unlink()
    if log_file.exists():
        log_file.rename(backup)


def setup_logging() -> dict:
    """Configure logging and return a uvicorn-compatible log_config dict.

    The same dict is passed to uvicorn.Config / uvicorn.run so that uvicorn's
    own loggers (uvicorn.access, uvicorn.error) also write to the log file.
    """
    log_dir = _get_log_dir()
    if log_dir.exists() and not log_dir.is_dir():
        # Path occupied by a non-directory (e.g. a stale file) — use sibling
        log_dir = log_dir.with_name("bcd_logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bcd.log"
    _rotate_log(log_file)
    level = settings.log_level.upper()

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "()": CleanLoggerNameFormatter,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "standard",
                "filename": str(log_file),
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                # In production, suppress per-request access logs to avoid
                # constant HDD seeks on every API call.
                "level": "WARNING" if settings.environment == "production" else "INFO",
                "propagate": False,
            },
            "urllib3": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
        "root": {
            "handlers": ["console", "file"],
            "level": level,
        },
    }

    logging.config.dictConfig(log_config)
    return log_config
