"""Request schemas for the Find a notice cataloging workflow."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


ExternalSource = Literal["bnf", "google_books", "sudoc"]


class NoticeLookupRequest(BaseModel):
    """Request to call exactly one external catalog source."""

    query: str = Field(..., min_length=1, max_length=200)
    source: ExternalSource


class ExternalSourceTestRequest(BaseModel):
    """Optional identifier used by the Settings source test button."""

    query: Optional[str] = Field(None, max_length=200)
