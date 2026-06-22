"""Export Schemas

Pydantic schemas for catalog export and import operations.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ExportResponse(BaseModel):
    """Response schema for catalog export."""

    filename: str = Field(
        ...,
        description="Suggested filename for the export",
        example="catalog_export_2026-02-06.csv"
    )
    content_type: str = Field(
        default="text/csv; charset=utf-8",
        description="MIME type of the exported file"
    )
    record_count: int = Field(
        ...,
        description="Total number of bibliographic records exported",
        ge=0
    )
    item_count: int = Field(
        ...,
        description="Total number of physical items (rows) exported",
        ge=0
    )
    encoding: str = Field(
        default="utf-8",
        description="Character encoding of the CSV file"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "filename": "catalog_export_2026-02-06.csv",
                "content_type": "text/csv; charset=utf-8",
                "record_count": 150,
                "item_count": 180,
                "encoding": "utf-8"
            }
        }


class ExportStats(BaseModel):
    """Statistics for an export operation."""

    total_records: int = Field(..., description="Total bibliographic records processed")
    total_items: int = Field(..., description="Total items exported")
    records_with_items: int = Field(..., description="Records with at least one item")
    records_without_items: int = Field(..., description="Records with no items")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "total_records": 150,
                "total_items": 180,
                "records_with_items": 145,
                "records_without_items": 5,
                "execution_time_ms": 1250
            }
        }


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    DUBLIN_CORE = "dublin_core"
    BCD_BORROWER = "bcd_borrower"


class ImportError(BaseModel):
    """Individual import error for a specific row."""

    row_number: int = Field(..., description="Row number (1-indexed)")
    error: str = Field(..., description="Error description")
    raw_data: Optional[dict] = Field(None, description="Raw row data (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "row_number": 42,
                "error": "Missing required field: dc.title",
                "raw_data": {"dc.identifier": "isbn:123", "dc.creator": "Smith"}
            }
        }


class ImportResponse(BaseModel):
    """Response for import operations."""

    total_rows: int = Field(..., description="Total rows in CSV file")
    successful_rows: int = Field(..., description="Number of rows successfully imported")
    failed_rows: int = Field(..., description="Number of rows that failed")
    records_created: int = Field(default=0, description="Number of bibliographic records created")
    items_created: int = Field(default=0, description="Number of items created")
    records_updated: int = Field(default=0, description="Number of records updated (for upsert operations)")
    errors: List[ImportError] = Field(default_factory=list, description="List of import errors")

    class Config:
        json_schema_extra = {
            "example": {
                "total_rows": 250,
                "successful_rows": 245,
                "failed_rows": 5,
                "records_created": 180,
                "items_created": 245,
                "records_updated": 0,
                "errors": [
                    {
                        "row_number": 42,
                        "error": "Missing required field: dc.title"
                    },
                    {
                        "row_number": 87,
                        "error": "Duplicate item ID: BK123"
                    }
                ]
            }
        }


class BorrowerImportResponse(BaseModel):
    """Response for borrower import operations."""

    total_rows: int = Field(..., description="Total rows in CSV file")
    successful_rows: int = Field(..., description="Number of rows successfully imported")
    failed_rows: int = Field(..., description="Number of rows that failed")
    borrowers_created: int = Field(default=0, description="Number of new borrowers created")
    borrowers_updated: int = Field(default=0, description="Number of existing borrowers updated")
    errors: List[ImportError] = Field(default_factory=list, description="List of import errors")

    class Config:
        json_schema_extra = {
            "example": {
                "total_rows": 120,
                "successful_rows": 115,
                "failed_rows": 5,
                "borrowers_created": 85,
                "borrowers_updated": 30,
                "errors": [
                    {
                        "row_number": 12,
                        "error": "Invalid role: 'parent' (must be student, teacher, or staff)"
                    }
                ]
            }
        }
