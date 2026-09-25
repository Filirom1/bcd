"""
Admin operation schemas for bulk operations.

Provides request/response models for bulk borrower and catalog operations.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.shared.constants import BindingType
from src.shared.validators import clean_call_number


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
    level: Optional[str] = Field(
        None,
        description="Reading level to set (null = no change)"
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
    publisher: Optional[str] = Field(
        None,
        description="Publisher to set (null = no change)"
    )
    collection: Optional[str] = Field(
        None,
        description="Collection/Series to set (null = no change)"
    )
    binding_type: Optional[BindingType] = Field(
        None,
        description="Binding type to set (null = no change)"
    )


class BulkDeleteRecordsRequest(BaseModel):
    """Request schema for bulk catalog record delete operation."""

    record_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of bibliographic record IDs to delete"
    )


class MergeItemUpdate(BaseModel):
    """Location and call-number values for one physical copy."""

    item_id: int = Field(..., description="Physical copy database ID")
    shelf_location: Optional[str] = Field(None, max_length=100)
    call_number: Optional[str] = Field(None, max_length=50)

    @field_validator("call_number", mode="before")
    @classmethod
    def clean_call_number_field(cls, value):
        """Normalize an optional call number."""
        return clean_call_number(value)


class MergeRecordsRequest(BaseModel):
    """Request schema for merging bibliographic records."""

    target_id: int = Field(..., description="Bibliographic record ID to keep")
    source_ids: List[int] = Field(
        ...,
        min_length=1,
        description="Bibliographic record IDs to merge into the target"
    )
    item_updates: List[MergeItemUpdate] = Field(
        default_factory=list,
        description="Optional location and call-number values, one entry per copy"
    )
