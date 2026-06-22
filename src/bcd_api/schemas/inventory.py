"""Pydantic schemas for Inventory operations."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# T006: ItemInventoryResponse, BulkInventoryRequest, BulkInventoryResponse

class ItemInventoryResponse(BaseModel):
    """Response schema for single item inventory mark."""

    # Item fields
    item_id: str = Field(..., description="Item barcode")
    bibliographic_record_id: int = Field(..., description="ID of parent bibliographic record")
    status: str = Field(..., description="Item status")
    condition: str = Field(..., description="Item condition")
    loanable: bool = Field(..., description="Whether item can be loaned")
    shelf_location: Optional[str] = Field(None, description="Physical location")
    call_number: Optional[str] = Field(None, description="Call number")
    last_inventoried_at: datetime = Field(..., description="Timestamp when item was marked")

    # Record fields (for display in working table)
    title: str = Field(..., description="Title from bibliographic record")
    level: Optional[str] = Field(None, description="Reading level")
    target_audience: Optional[str] = Field(None, description="Target audience")
    language: Optional[str] = Field(None, description="Language")
    medium_type: str = Field(..., description="Medium type")

    model_config = ConfigDict(from_attributes=True)


class BulkInventoryRequest(BaseModel):
    """Request schema for bulk inventory marking."""

    item_ids: list[str] = Field(..., min_length=1, description="List of item barcodes to mark")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_ids": ["0785", "0784", "0312"]
            }
        }
    )


class BulkInventoryResponse(BaseModel):
    """Response schema for bulk inventory marking."""

    items_updated: int = Field(..., description="Number of items successfully updated")
    items_not_found: list[str] = Field(default_factory=list, description="Item IDs not found in database")
    timestamp: datetime = Field(..., description="Timestamp when items were marked")


# T007: InventoryItemResult, InventorySearchResponse

class InventoryItemResult(BaseModel):
    """Single item result in inventory search."""

    # Item fields
    item_id: str = Field(..., description="Item barcode")
    bibliographic_record_id: int = Field(..., description="ID of parent bibliographic record")
    status: str = Field(..., description="Item status")
    condition: str = Field(..., description="Item condition")
    loanable: bool = Field(..., description="Whether item can be loaned")
    shelf_location: Optional[str] = Field(default=None, description="Physical location")
    acquisition_date: Optional[date] = Field(default=None, description="Acquisition date")
    last_borrowed_at: Optional[datetime] = Field(default=None, description="Last checkout timestamp")
    last_inventoried_at: Optional[datetime] = Field(default=None, description="Last inventory timestamp")

    # Record fields (for display in working table)
    title: str = Field(..., description="Title from bibliographic record")
    authors: Optional[list[str]] = Field(default=None, description="Authors from bibliographic record")
    call_number: Optional[str] = Field(default=None, description="Call number")
    level: Optional[str] = Field(default=None, description="Reading level")
    target_audience: Optional[str] = Field(default=None, description="Target audience")
    language: Optional[str] = Field(default=None, description="Language")
    medium_type: str = Field(..., description="Medium type")
    publication_year: Optional[int] = Field(default=None, description="Publication year")

    # Calculated fields
    age_days: Optional[int] = Field(default=None, description="Age in collection (days since acquisition)")

    # Calculated loan fields
    circulation_count: Optional[int] = Field(default=None, description="Total all-time loan count")
    period_loan_count: Optional[int] = Field(default=None, description="Loans in specified period (rotation filter)")

    model_config = ConfigDict(from_attributes=True)


class InventorySearchResponse(BaseModel):
    """Response schema for inventory item search."""

    items: list[InventoryItemResult] = Field(default_factory=list, description="Search results")
    total_count: int = Field(..., description="Total matching items before limit")
    displayed_count: int = Field(..., description="Number of items in results")
    capped: bool = Field(..., description="True if results were capped at 200")
    archive_cutoff_date: Optional[datetime] = Field(default=None, description="Oldest transaction date (archive boundary)")


# T008: ItemUpdates, RecordUpdates, BulkUpdateRequest, BulkUpdateResponse

class ItemUpdates(BaseModel):
    """Optional item field updates for bulk edit."""

    status: Optional[str] = Field(default=None, description="Item status")
    condition: Optional[str] = Field(default=None, description="Item condition")
    loanable: Optional[bool] = Field(default=None, description="Can be borrowed")
    shelf_location: Optional[str] = Field(default=None, description="Physical location")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "withdrawn",
                "condition": "damaged",
                "loanable": False,
                "shelf_location": "Archive"
            }
        }
    )


class RecordUpdates(BaseModel):
    """Optional bibliographic record field updates for bulk edit."""

    level: Optional[str] = Field(default=None, description="Reading level")
    target_audience: Optional[str] = Field(default=None, description="Target audience (child/youth/adult)")
    language: Optional[str] = Field(default=None, description="Language")
    medium_type: Optional[str] = Field(default=None, description="Medium type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "level": "CP",
                "target_audience": "child",
                "language": "fra",
                "medium_type": "Livre"
            }
        }
    )


class BulkUpdateRequest(BaseModel):
    """Request schema for bulk item and record updates."""

    item_ids: list[str] = Field(..., min_length=1, description="List of item barcodes to update")
    item_updates: Optional[ItemUpdates] = Field(default=None, description="Item field updates")
    record_updates: Optional[RecordUpdates] = Field(default=None, description="Bibliographic record field updates")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_ids": ["0785", "0784"],
                "item_updates": {
                    "status": "withdrawn",
                    "condition": "damaged"
                },
                "record_updates": {
                    "level": "CP"
                }
            }
        }
    )


class BulkUpdateResponse(BaseModel):
    """Response schema for bulk item and record updates."""

    items_updated: int = Field(..., description="Number of items successfully updated")
    items_skipped_on_loan: int = Field(..., description="Items with status='on_loan' excluded from status changes")
    records_updated: int = Field(..., description="Number of unique bibliographic records updated")
    other_copies_affected: int = Field(..., description="Copies of same titles NOT in item_ids but affected by record updates")


# T009: BulkDeleteRequest, BulkDeleteResponse

class BulkDeleteRequest(BaseModel):
    """Request schema for bulk item deletion."""

    item_ids: list[str] = Field(..., min_length=1, description="List of item barcodes to delete")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_ids": ["0785", "0784", "0312"]
            }
        }
    )


class BulkDeleteResponse(BaseModel):
    """Response schema for bulk item deletion."""

    items_deleted: int = Field(..., description="Number of items successfully deleted")
    items_skipped_on_loan: int = Field(..., description="Items with status='on_loan' excluded from deletion")
    holds_cancelled: int = Field(..., description="Active holds cancelled")
    orphan_records_created: int = Field(..., description="Records where total_items became 0")


# T010: ExportCSVRequest, OrphanRecord, OrphanRecordsResponse, OrphanDeleteResponse

class ExportCSVRequest(BaseModel):
    """Request schema for CSV export."""

    item_ids: list[str] = Field(..., min_length=1, description="List of item barcodes to export")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_ids": ["0785", "0784", "0312"]
            }
        }
    )


class OrphanRecord(BaseModel):
    """Single orphan bibliographic record."""

    id: int = Field(..., description="Record ID")
    title: str = Field(..., description="Title")
    isbn: Optional[str] = Field(default=None, description="ISBN")

    model_config = ConfigDict(from_attributes=True)


class OrphanRecordsResponse(BaseModel):
    """Response schema for orphan records query."""

    count: int = Field(..., description="Number of orphan records")
    records: list[OrphanRecord] = Field(default_factory=list, description="Orphan record details")


class OrphanDeleteResponse(BaseModel):
    """Response schema for orphan record deletion."""

    records_deleted: int = Field(..., description="Number of records deleted")
