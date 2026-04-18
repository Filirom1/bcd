"""
Admin operation schemas for bulk operations.

Provides request/response models for bulk borrower and catalog operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BulkChangeClassRequest(BaseModel):
    """Request schema for bulk class change operation."""

    borrower_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of borrower IDs to update"
    )
    target_class_id: Optional[int] = Field(
        None,
        description="Target class ID (null to unassign from class)"
    )


class BulkChangeRoleRequest(BaseModel):
    """Request schema for bulk role change operation."""

    borrower_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of borrower IDs to update"
    )
    target_role: str = Field(
        ...,
        description="Target role (student, teacher, staff)"
    )


class BulkDeleteRequest(BaseModel):
    """Request schema for bulk delete operation."""

    borrower_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of borrower IDs to delete"
    )


class BulkOperationResult(BaseModel):
    """Response schema for bulk operations."""

    operation: str = Field(..., description="Operation type")
    total_count: int = Field(..., description="Total number of records processed")
    successful_count: int = Field(..., description="Number of successful updates")
    failed_count: int = Field(0, description="Number of failed updates")
    details: Optional[dict] = Field(None, description="Additional operation details")

    class Config:
        from_attributes = True


# === Catalog Bulk Operations (US5) ===


class BulkEditRecordsRequest(BaseModel):
    """Request schema for bulk catalog record edit operation."""

    record_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of bibliographic record IDs to update"
    )
    genre: Optional[str] = Field(
        None,
        description="Genre to set (null = no change)"
    )
    target_audience: Optional[str] = Field(
        None,
        description="Target audience to set (null = no change)"
    )
    language: Optional[str] = Field(
        None,
        description="Language to set (null = no change)"
    )
    medium_type: Optional[str] = Field(
        None,
        description="Medium type to set (null = no change)"
    )


class BulkDeleteRecordsRequest(BaseModel):
    """Request schema for bulk catalog record delete operation."""

    record_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of bibliographic record IDs to delete"
    )
