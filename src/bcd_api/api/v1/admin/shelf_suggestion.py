"""Administration endpoints for the shelf suggestion model."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....core.deps import get_db
from ....schemas.shelf_suggestion import (
    ShelfSuggestionStatus,
    ShelfSuggestionTrainResponse,
)
from ....services.shelving import suggestion as suggestion_service

router = APIRouter()


def _status_payload(db: Session, status: str | None = None) -> dict:
    info = suggestion_service.get_status(db)
    return {
        "enabled": suggestion_service.is_enabled(),
        "trained_at": info.trained_at,
        "trained_on_records": info.trained_on_records,
        "ready": info.ready,
        "status": status or info.status,
    }


@router.get("/shelf-suggestion/status", response_model=ShelfSuggestionStatus)
def get_shelf_suggestion_status(db: Session = Depends(get_db)):
    """Return model readiness and training metadata."""
    payload = _status_payload(db)
    payload.pop("status", None)
    return payload


@router.post("/shelf-suggestion/train", response_model=ShelfSuggestionTrainResponse)
def train_shelf_suggestion(db: Session = Depends(get_db)):
    """Train the shelf model synchronously and return when it is complete.

    This endpoint deliberately does not use ``BackgroundTasks``: the admin
    action is a blocking operation, so the UI can show a single determinate
    spinner and immediately display the resulting status.
    """
    info = suggestion_service.train(db)
    return _status_payload(db, info.status)
