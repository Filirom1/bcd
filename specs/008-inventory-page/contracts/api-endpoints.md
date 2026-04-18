# API Contracts: Collection Inventory Page (008)

**Date**: 2026-04-02  
**Pattern Source**: Existing `src/bcd_api/api/v1/` routers  
**Schema Source**: Existing `src/bcd_api/schemas/` patterns

---

## Router: `/api/v1/inventory`

**New file**: `src/bcd_api/api/v1/inventory.py`  
**Prefix**: `/inventory`  
**Tag**: `inventory`

---

### 1. Mark Single Item as Inventoried

**Endpoint**: `PATCH /inventory/items/{item_id}`  
**Purpose**: Update `last_inventoried_at` for a single item (barcode scan)  
**Auth**: Any authenticated user (per clarification)

**Path Parameters**:
```json
{
  "item_id": {
    "type": "string",
    "description": "Item barcode (e.g., '0785')",
    "example": "0785"
  }
}
```

**Request Body**: None

**Response 200** (`ItemInventoryResponse`):
```json
{
  "item_id": "0785",
  "title": "Le Seigneur des Anneaux",
  "status": "available",
  "condition": "good",
  "last_inventoried_at": "2026-04-02T14:30:00Z"
}
```

**Errors**:
- `404 ItemNotFoundException` — item_id not found

**Service Call**: `inventory_service.mark_item_inventoried(db, item_id)`

---

### 2. Bulk Mark Items as Inventoried

**Endpoint**: `POST /inventory/items/bulk-mark`  
**Purpose**: Update `last_inventoried_at` for multiple items (file import, search add)  
**Auth**: Any authenticated user

**Request Body** (`BulkInventoryRequest`):
```json
{
  "item_ids": ["0785", "0784", "0312", "..."]
}
```

**Response 200** (`BulkInventoryResponse`):
```json
{
  "items_updated": 117,
  "items_not_found": ["0099", "0100", "0101"],
  "timestamp": "2026-04-02T14:30:00Z"
}
```

**Service Call**: `inventory_service.bulk_mark_inventoried(db, item_ids)`

---

### 3. Search Items with Inventory Filters

**Endpoint**: `GET /inventory/items/search`  
**Purpose**: Find items matching inventory criteria (rotation, last inventoried, condition, etc.)  
**Auth**: Any authenticated user

**Query Parameters** (all optional):

| Parameter | Type | Description | Example |
|---|---|---|---|
| `q` | string | Free text (title, author, ISBN, call number) | "Harry Potter" |
| `status` | string | Item status filter | "available" |
| `condition` | string | Item condition filter | "damaged" |
| `shelf_location` | string | Partial match on location | "Room B" |
| `never_inventoried` | boolean | Only items with NULL `last_inventoried_at` | true |
| `inventoried_before` | string (ISO date) | Items not inventoried since this date | "2025-01-01" |
| `medium_type` | string | Bibliographic medium type | "Livre" |
| `target_audience` | string | child, youth, adult | "child" |
| `category` | string | Partial match on category | "Fiction" |
| `genre` | string | Partial match on genre | "Adventure" |
| `level` | string | Partial match on reading level | "CP" |
| `publication_year_min` | integer | Min publication year | 2010 |
| `publication_year_max` | integer | Max publication year | 2024 |
| `max_borrows` | integer | Max loans in period (rotation filter) | 2 |
| `since_date` | string (ISO date) | Start date for rotation filter | "2022-04-01" |

**Response 200** (`InventorySearchResponse`):
```json
{
  "items": [
    {
      "item_id": "0785",
      "title": "Le Seigneur des Anneaux",
      "authors": ["J.R.R. Tolkien"],
      "call_number": "SF TOL",
      "shelf_location": "Room A - Fantasy",
      "status": "available",
      "condition": "good",
      "last_borrowed_at": "2024-03-15T10:00:00Z",
      "last_inventoried_at": null,
      "period_loan_count": 1
    }
  ],
  "total_count": 347,
  "displayed_count": 200,
  "capped": true,
  "archive_cutoff_date": "2021-04-02T00:00:00Z"
}
```

**Field Notes**:
- `period_loan_count` — only present when `max_borrows` + `since_date` provided
- `capped` — `true` if `total_count > 200`
- `archive_cutoff_date` — `MIN(checkout_date)` from `circulation_transaction`; `null` if no transactions

**Limit**: Returns maximum 200 items (FR-019b).

**Service Call**: `inventory_service.search_items(db, **filters)`

---

### 4. Bulk Update Items and Records

**Endpoint**: `POST /inventory/items/bulk-update`  
**Purpose**: Apply same changes to multiple items + their parent records (bulk edit)  
**Auth**: Any authenticated user

**Request Body** (`BulkUpdateRequest`):
```json
{
  "item_ids": ["0785", "0784", "..."],
  "item_updates": {
    "status": "withdrawn",
    "condition": "damaged",
    "loanable": false,
    "shelf_location": "Archive"
  },
  "record_updates": {
    "category": "Documentaires",
    "genre": "Album",
    "level": "CP",
    "target_audience": "child"
  }
}
```

**Field Notes**:
- All fields in `item_updates` and `record_updates` are optional
- Omitted fields = unchanged
- `null` values = clear field (set to NULL)

**Response 200** (`BulkUpdateResponse`):
```json
{
  "items_updated": 39,
  "items_skipped_on_loan": 3,
  "records_updated": 7,
  "other_copies_affected": 15
}
```

**Field Notes**:
- `items_skipped_on_loan` — items with `status='on_loan'` excluded from status changes only
- `other_copies_affected` — copies of same titles NOT in `item_ids` but affected by `record_updates`

**Service Call**: `inventory_service.bulk_update_items(db, item_ids, item_updates, record_updates)`

---

### 5. Bulk Delete Items

**Endpoint**: `DELETE /inventory/items/bulk`  
**Purpose**: Permanently delete items (leaves parent records intact if other copies exist)  
**Auth**: Any authenticated user

**Request Body** (`BulkDeleteRequest`):
```json
{
  "item_ids": ["0785", "0784", "..."]
}
```

**Response 200** (`BulkDeleteResponse`):
```json
{
  "items_deleted": 39,
  "items_skipped_on_loan": 3,
  "holds_cancelled": 2,
  "orphan_records_created": 1
}
```

**Field Notes**:
- `items_skipped_on_loan` — items with `status='on_loan'` excluded silently
- `holds_cancelled` — active hold reservations cancelled (FR-034)
- `orphan_records_created` — records where `total_items` became 0

**Service Call**: `inventory_service.delete_items_bulk(db, item_ids)`

---

### 6. Export Working Table to CSV

**Endpoint**: `POST /inventory/export-csv`  
**Purpose**: Generate CSV of items in working table  
**Auth**: Any authenticated user

**Request Body** (`ExportCSVRequest`):
```json
{
  "item_ids": ["0785", "0784", "..."]
}
```

**Response 200**:
```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="inventory_2026-04-02.csv"

barcode,title,author,call_number,location,status,condition,last_loan_date,last_inventory_date
.0785,Le Seigneur des Anneaux,J.R.R. Tolkien,SF TOL,Room A,available,good,2024-03-15,2026-04-02
...
```

**Columns** (per FR-036):
1. barcode (with prefix)
2. title
3. author (first author if multiple)
4. call_number
5. location (shelf_location)
6. status
7. condition
8. last_loan_date (`last_borrowed_at` formatted as date)
9. last_inventory_date (`last_inventoried_at` formatted as date)

**Service Call**: `inventory_service.get_items_csv(db, item_ids)`

---

## Router: `/api/v1/admin/catalog` (Extensions)

**Existing file**: `src/bcd_api/api/v1/admin.py`  
**Prefix**: `/admin`

---

### 7. Get Orphan Records Count and List

**Endpoint**: `GET /admin/catalog/orphan-records`  
**Purpose**: Fetch bibliographic records with no items (FR-037, FR-038)  
**Auth**: Any authenticated user (admin menu visible to all, per clarification)

**Query Parameters**: None

**Response 200** (`OrphanRecordsResponse`):
```json
{
  "count": 12,
  "records": [
    {
      "id": 456,
      "title": "Le Petit Prince",
      "isbn": "978-2070408504"
    },
    ...
  ]
}
```

**Service Call**: `inventory_service.get_orphan_records(db)`

---

### 8. Delete Orphan Records

**Endpoint**: `DELETE /admin/catalog/orphan-records`  
**Purpose**: Remove all bibliographic records with `total_items = 0` (FR-039)  
**Auth**: Any authenticated user (confirmation modal gates the action)

**Request Body**: None

**Response 200** (`OrphanDeleteResponse`):
```json
{
  "records_deleted": 12
}
```

**Service Call**: `inventory_service.delete_orphan_records(db)` → calls `catalog_service.bulk_delete_records(db, record_ids)` internally

---

## Pydantic Schemas

**New file**: `src/bcd_api/schemas/inventory.py`

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Response for single item inventory update
class ItemInventoryResponse(BaseModel):
    item_id: str
    title: str
    status: str
    condition: str
    last_inventoried_at: datetime
    
    class Config:
        from_attributes = True

# Bulk inventory marking
class BulkInventoryRequest(BaseModel):
    item_ids: List[str] = Field(..., min_length=1, max_length=500)

class BulkInventoryResponse(BaseModel):
    items_updated: int
    items_not_found: List[str]
    timestamp: datetime

# Search
class InventoryItemResult(BaseModel):
    item_id: str
    title: str
    authors: Optional[List[str]] = None
    call_number: Optional[str] = None
    shelf_location: Optional[str] = None
    status: str
    condition: str
    last_borrowed_at: Optional[datetime] = None
    last_inventoried_at: Optional[datetime] = None
    period_loan_count: Optional[int] = None  # Only when rotation filter active

class InventorySearchResponse(BaseModel):
    items: List[InventoryItemResult]
    total_count: int
    displayed_count: int
    capped: bool
    archive_cutoff_date: Optional[datetime] = None

# Bulk update
class ItemUpdates(BaseModel):
    status: Optional[str] = None
    condition: Optional[str] = None
    loanable: Optional[bool] = None
    shelf_location: Optional[str] = None

class RecordUpdates(BaseModel):
    category: Optional[str] = None
    genre: Optional[str] = None
    level: Optional[str] = None
    target_audience: Optional[str] = None

class BulkUpdateRequest(BaseModel):
    item_ids: List[str] = Field(..., min_length=1)
    item_updates: Optional[ItemUpdates] = None
    record_updates: Optional[RecordUpdates] = None

class BulkUpdateResponse(BaseModel):
    items_updated: int
    items_skipped_on_loan: int
    records_updated: int
    other_copies_affected: int

# Bulk delete
class BulkDeleteRequest(BaseModel):
    item_ids: List[str] = Field(..., min_length=1)

class BulkDeleteResponse(BaseModel):
    items_deleted: int
    items_skipped_on_loan: int
    holds_cancelled: int
    orphan_records_created: int

# Export
class ExportCSVRequest(BaseModel):
    item_ids: List[str]

# Orphan records
class OrphanRecord(BaseModel):
    id: int
    title: str
    isbn: Optional[str] = None

class OrphanRecordsResponse(BaseModel):
    count: int
    records: List[OrphanRecord]

class OrphanDeleteResponse(BaseModel):
    records_deleted: int
```

---

## Error Responses

All endpoints follow existing exception handling patterns (architecture-patterns.md Section 7).

**Common Errors**:

| Status | Exception | error_code | When |
|---|---|---|---|
| 404 | `ItemNotFoundException` | `ITEM_NOT_FOUND` | Item barcode not found |
| 422 | `ValidationError` | `VALIDATION_ERROR` | Invalid request payload |
| 400 | `BusinessRuleViolation` | varies | Business logic violation |

**Example Error Response**:
```json
{
  "detail": "Item 0785 not found",
  "error_code": "ITEM_NOT_FOUND",
  "context": {
    "item_id": "0785"
  }
}
```

**i18n Handling**: Frontend maps `error_code` to translation key `errors.{code}` with variable interpolation from `context`.

---

## Summary

### New Endpoints: 6 in `/inventory`, 2 in `/admin`

| Method | Path | Purpose |
|---|---|---|
| PATCH | `/inventory/items/{item_id}` | Mark single item inventoried |
| POST | `/inventory/items/bulk-mark` | Mark multiple items inventoried |
| GET | `/inventory/items/search` | Search with inventory filters |
| POST | `/inventory/items/bulk-update` | Bulk edit items + records |
| DELETE | `/inventory/items/bulk` | Bulk delete items |
| POST | `/inventory/export-csv` | Export working table CSV |
| GET | `/admin/catalog/orphan-records` | Get orphan count + list |
| DELETE | `/admin/catalog/orphan-records` | Delete orphan records |

### Alignment with Existing Patterns

✅ Follows FastAPI route structure from `catalog.py`, `circulation.py`  
✅ Pydantic schemas match `schemas/item.py`, `schemas/bibliographic_record.py` patterns  
✅ Error handling via `BCDException` with `error_code` + `context`  
✅ Auth: `Depends(get_db)` for all endpoints  
✅ CSV export uses `text/csv` Content-Type like `GET /catalog/export`

### Next: Implement Service Layer

All business logic goes in `src/bcd_api/services/inventory_service.py` (per architecture-patterns.md Section 1).
