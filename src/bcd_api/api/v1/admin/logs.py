"""Administrative endpoint for viewing the current application log."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from ....core.logging_config import _get_log_dir

router = APIRouter()

MAX_LOG_BYTES = 512 * 1024
MAX_LOG_LINES = 1_000


def _get_log_file() -> Path:
    """Return the current log file path using the logging configuration."""
    log_dir = _get_log_dir()
    if log_dir.exists() and not log_dir.is_dir():
        log_dir = log_dir.with_name("bcd_logs")
    return log_dir / "bcd.log"


def _read_log_tail(path: Path) -> tuple[str, bool]:
    """Read a bounded tail of a log file without loading the whole file."""
    if not path.exists():
        return "", False

    with path.open("rb") as log_file:
        log_file.seek(0, 2)
        file_size = log_file.tell()
        truncated = file_size > MAX_LOG_BYTES
        log_file.seek(max(0, file_size - MAX_LOG_BYTES))
        content = log_file.read().decode("utf-8", errors="replace")

    lines = content.splitlines()
    if truncated and lines:
        lines = lines[1:]
    truncated = truncated or len(lines) > MAX_LOG_LINES
    lines = lines[-MAX_LOG_LINES:]
    return "\n".join(lines) + ("\n" if lines else ""), truncated


@router.get("/logs")
def get_logs():
    """Return the most recent lines from the current application log."""
    log_file = _get_log_file()
    content, truncated = _read_log_tail(log_file)
    updated_at = None
    if log_file.exists():
        updated_at = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc).isoformat()

    return {
        "filename": log_file.name,
        "content": content,
        "updated_at": updated_at,
        "truncated": truncated,
    }
