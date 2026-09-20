"""API schemas for the lightweight shelf suggestion model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ShelfSuggestionRequest(BaseModel):
    """Metadata used to predict a shelf location during cataloging."""

    title: str = Field(default="", max_length=500)
    subtitle: Optional[str] = Field(default=None, max_length=500)
    collection: Optional[str] = Field(default=None, max_length=200)
    authors: Optional[list[str] | str] = None


class ShelfSuggestionResponse(BaseModel):
    suggested_shelf: Optional[str] = None


class ShelfSuggestionStatus(BaseModel):
    enabled: bool
    trained_at: Optional[datetime] = None
    trained_on_records: Optional[int] = None
    ready: bool


class ShelfSuggestionTrainResponse(ShelfSuggestionStatus):
    status: str
