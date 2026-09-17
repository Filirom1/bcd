"""System settings administration endpoints."""

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ....core.deps import get_db
from ....schemas.system_settings import SystemSettingsResponse, SystemSettingsUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


class SettingsUpdate(BaseModel):
    """Envelope for a partial system-settings update.

    The envelope is kept for compatibility with the web client. The actual
    fields are validated by ``SystemSettingsUpdate`` before they reach the
    service layer.
    """

    updates: Dict[str, Any]


@router.get("/env")
def get_env_file_content():
    """Read the contents of the current .env file."""
    from ....core.config import _get_env_file_path

    path = Path(_get_env_file_path())
    if not path.exists():
        return {"content": ""}
    return {"content": path.read_text(encoding="utf-8")}


@router.put("/env")
def update_env_file_content(payload: dict):
    """Overwrite the contents of the current .env file."""
    from ....core.config import _get_env_file_path

    path = Path(_get_env_file_path())
    content = payload.get("content", "")
    path.write_text(content, encoding="utf-8")
    return {"content": content}


@router.get("/settings", response_model=SystemSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get the current system settings."""
    from . import settings_service

    return settings_service.get_settings(db)


@router.put("/settings", response_model=SystemSettingsResponse)
async def update_settings(
    settings_update: SettingsUpdate,
    db: Session = Depends(get_db),
):
    """Validate and update system settings, restarting mDNS if needed."""
    from . import app_settings, mdns_module, settings_service

    validated_update = SystemSettingsUpdate.model_validate(settings_update.updates)
    updates = validated_update.model_dump(exclude_unset=True)
    settings = settings_service.update_settings(db, updates)

    if "library_code" in updates:
        try:
            new_library_code = getattr(settings, "library_code", None)
            port = mdns_module.get_server_port(app_settings.api_port)
            await mdns_module.restart_mdns(new_library_code, port)
        except Exception as exc:
            logger.warning("mDNS restart after settings update failed (non-fatal): %s", exc)

    return settings


@router.post("/settings/reset", response_model=SystemSettingsResponse)
def reset_settings(db: Session = Depends(get_db)):
    """Reset all settings to their default values."""
    from . import settings_service

    return settings_service.reset_to_defaults(db)
