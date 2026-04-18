# Data Model: Collection Inventory Page (008)

**Date**: 2026-04-02  
**Branch**: `008-inventory-page`  
**Source**: Derived from actual `src/bcd_api/models/` codebase

---

## Schema Changes

### New Column: `item.last_inventoried_at`

**Migration**: `migrations/versions/<hash>_add_item_last_inventoried_at.py`

| Property | Value |
|---|---|
| Table | `item` |
| Column | `last_inventoried_at` |
| Type | `DateTime` (timezone-aware UTC) |
| Nullable | `True` |
| Default | `NULL` |
| Index | `True` — enables filtering `IS NULL` and `< date` |

**Semantics**: Timestamp of most recent physical presence verification via inventory page. Distinct from:
- `last_borrowed_at` — updated by circulation_service (loans)
- `updated_at` — updated by ANY modification

**Initial value**: `NULL` for all existing items (never inventoried).

**Migration code**:
```python
"""Add item.last_inventoried_at for collection inventory tracking

Revision ID: <hash>
Revises: 46877dbfbe26
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa

revision = '<hash>'
down_revision = '46877dbfbe26'

def upgrade() -> None:
    op.add_column('item', sa.Column(
        'last_inventoried_at',
        sa.DateTime(),
        nullable=True
    ))
    op.create_index(
        'ix_item_last_inventoried_at',
        'item',
        ['last_inventoried_at']
    )

def downgrade() -> None:
    op.drop_index('ix_item_last_inventoried_at', table_name='item')
    op.drop_column('item', 'last_inventoried_at')
```

---

## Existing Model: Item (Updated)

**File**: `src/bcd_api/models/item.py`

Fields relevant to inventory (existing unless marked **NEW**):

| Field | Type | Nullable | Indexed | Constraint | Notes |
|---|---|---|---|---|---|
| `id` | Integer | No | PK | autoincrement | Internal ID |
| `item_id` | String(20) | No | Unique | — | Barcode (user-facing ID) |
| `bibliographic_record_id` | Integer | No | FK | CASCADE | Parent title |
| `call_number` | String(50) | Yes | Yes | — | Dewey/CDU classification |
| `shelf_location` | String(100) | Yes | No | — | Physical location |
| `condition` | String(20) | No | Yes | `good` \| `damaged` | Physical state |
| `status` | String(20) | No | Yes | 6 values (see below) | Circulation state |
| `loanable` | Boolean | No | Yes | — | Can be borrowed |
| `acquisition_date` | Date | Yes | No | — | When acquired |
| `funding_source` | String(100) | Yes | No | — | Budget source |
| `circulation_count` | Integer | No | No | default: 0 | Denormalized all-time count |
| `last_borrowed_at` | DateTime | Yes | No | — | Latest checkout timestamp |
| **`last_inventoried_at`** | **DateTime** | **Yes** | **Yes** | **—** | **NEW** — latest physical verification |
| `created_at` | DateTime | No | No | UTC default | Audit timestamp |
| `updated_at` | DateTime | No | No | UTC auto-update | Audit timestamp |

**Status Values** (CHECK constraint):
- `available` — on shelf, can be borrowed
- `on_loan` — checked out to borrower
- `on_hold` — reserved for borrower
- `in_repair` — temporarily unavailable
- `lost` — missing/presumed lost
- `withdrawn` — weeded/deaccessioned

**Condition Values** (CHECK constraint):
- `good` — acceptable condition
- `damaged` — worn/torn/stained

**Relationships**:
- `bibliographic_record` → BiblographicRecord (many-to-one)
- `circulation_transactions` → CirculationTransaction (one-to-many, cascade delete)

**Property Method**:
- `barcode` → returns `item_id` (frontend adds prefix for display)

---

## Existing Model: BiblographicRecord (No Schema Changes)

**File**: `src/bcd_api/models/bibliographic_record.py`

Fields relevant to inventory (editable via bulk edit or search filters):

| Field | Type | Nullable | Indexed | Notes |
|---|---|---|---|---|
| `id` | Integer | No | PK | Internal ID |
| `isbn` | String(17) | Yes | Unique | ISBN-10/13 or ISSN |
| `title` | String(500) | No | Yes | Full title |
| `authors` | Text | Yes | No | JSON array (stored as string) |
| `publication_year` | Integer | Yes | Yes | Constraint: 1000-2100 |
| `category` | String(100) | Yes | Yes | **Bulk editable** |
| `genre` | String(100) | Yes | Yes | **Bulk editable** |
| `level` | String(50) | Yes | No | **Bulk editable** (reading level) |
| `target_audience` | String(20) | Yes | Yes | **Bulk editable** (`child`\|`youth`\|`adult`) |
| `medium_type` | String(50) | No | Yes | Livre, CD, DVD, etc. (NO constraint) |
| `total_items` | Integer | No | No | Denormalized counter — updated on delete |

**Relationships**:
- `items` → Item (one-to-many, cascade delete)

**Denormalized Counter Updates**:
- `total_items` decremented when item deleted
- If reaches 0 → record becomes "orphan" (targetable by FR-037 cleanup)

---

## Working Table (Client-Side Only)

**Storage**: Browser `localStorage` under key `bcd_inventory_table`  
**Lifetime**: Survives page refresh + tab close on same device (FR-024b)  
**Scope**: Per-user, per-device (not synced across devices)

**Shape** (JSON array of objects):
```json
[
  {
    "item_id": "0785",
    "title": "Le Seigneur des Anneaux",
    "condition": "good",
    "status": "available",
    "last_inventoried_at": "2026-04-02T09:30:00Z"
  },
  ...
]
```

**Operations**:
- Add (deduplicate by `item_id`)
- Remove selected
- Clear all
- Restore on page load

**Size Estimate**: ~200 bytes/item × 3,000 items = ~600KB (well under localStorage 5MB limit)

---

## State Transitions: Item Status vs. Inventory Actions

| Current Status | Bulk Status Change Allowed? | Bulk Delete Allowed? | Notes (FR-029, FR-033) |
|---|---|---|---|
| `available` | ✅ Yes | ✅ Yes | — |
| `on_hold` | ✅ Yes (with warning) | ✅ Yes | Hold not auto-cancelled by status change; only by deletion (FR-034) |
| `in_repair` | ✅ Yes | ✅ Yes | — |
| `lost` | ✅ Yes | ✅ Yes | — |
| `withdrawn` | ✅ Yes | ✅ Yes | — |
| `on_loan` | ❌ No (silently excluded) | ❌ No (silently excluded) | Count shown in confirmation modal; excluded from operation |

---

## Query Patterns

### 1. Inventory Search with Rotation Filter (FR-016)

**SQLAlchemy pseudo-code**:
```python
from sqlalchemy import func, case, and_, or_
from sqlalchemy.orm import aliased

# Subquery: count loans in period
loan_subquery = (
    db.query(
        CirculationTransaction.item_id,
        func.count().label('period_count')
    )
    .filter(CirculationTransaction.checkout_date >= since_date)
    .group_by(CirculationTransaction.item_id)
    .subquery()
)

# Main query
query = (
    db.query(
        Item,
        BiblographicRecord.title,
        BiblographicRecord.authors,
        func.coalesce(loan_subquery.c.period_count, 0).label('period_loan_count')
    )
    .join(BiblographicRecord)
    .outerjoin(loan_subquery, loan_subquery.c.item_id == Item.id)
    .filter(
        # Text filter (optional)
        or_(
            BiblographicRecord.title.ilike(f'%{q}%'),
            BiblographicRecord.authors.ilike(f'%{q}%'),
            Item.call_number.ilike(f'%{q}%')
        ) if q else True,
        
        # Item filters
        Item.status == status if status else True,
        Item.condition == condition if condition else True,
        Item.shelf_location.ilike(f'%{shelf_location}%') if shelf_location else True,
        
        # Inventory filter
        Item.last_inventoried_at.is_(None) if never_inventoried else True,
        Item.last_inventoried_at < before_date if before_date else True,
        
        # Record filters
        BiblographicRecord.medium_type == medium_type if medium_type else True,
        BiblographicRecord.level.ilike(f'%{level}%') if level else True,
        BiblographicRecord.publication_year.between(year_min, year_max) if year_min and year_max else True,
        
        # Rotation filter
        func.coalesce(loan_subquery.c.period_count, 0) <= max_borrows if max_borrows is not None else True
    )
    .limit(200)
)
```

**Indexes Used**:
- `Item.status`, `Item.condition`, `Item.last_inventoried_at`
- `CirculationTransaction.checkout_date`, `CirculationTransaction.item_id` (FK index)
- `BiblographicRecord.title`

**Performance**: <2s on legacy hardware at school scale (3,000 items, 20,000 transactions) per SC-003.

---

### 2. Archive Cutoff Detection (FR-018)

**SQL**:
```sql
SELECT MIN(checkout_date) FROM circulation_transaction
```

**Returns**:
- Timestamp — oldest remaining transaction (= archive boundary)
- `NULL` — no transactions yet (no archive warning needed)

**Performance**: O(1) with index on `checkout_date`.

**Usage**: Returned in search response as `archive_cutoff_date` field. Frontend compares to rotation filter's `since_date`:
```javascript
if (since_date < archive_cutoff_date) {
  showWarning("Historical loan records incomplete — some data archived")
}
```

---

### 3. Orphan Record Query (FR-037, FR-038)

**SQL**:
```sql
SELECT id, title, isbn
FROM bibliographic_record
WHERE total_items = 0
```

**No JOIN needed** — uses denormalized `total_items` counter.

**Returns**: List of {id, title, isbn} for confirmation modal.

---

### 4. Bulk Item Delete (FR-032, FR-033)

**Pseudo-code**:
```python
def delete_items_bulk(db, item_ids):
    # Resolve item_ids (barcodes) to DB IDs
    items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    
    # Exclude on_loan
    on_loan_ids = [i.id for i in items if i.status == 'on_loan']
    deletable = [i for i in items if i.status != 'on_loan']
    
    # Cancel holds on deleted items
    db.query(Hold).filter(Hold.item_id.in_([i.id for i in deletable])).delete()
    
    # Delete items
    for item in deletable:
        db.delete(item)
    
    # Update parent record counters
    record_ids = {i.bibliographic_record_id for i in deletable}
    for record_id in record_ids:
        record = db.query(BiblographicRecord).get(record_id)
        record.total_items = db.query(Item).filter_by(bibliographic_record_id=record_id).count()
    
    db.commit()
    
    return {
        'items_deleted': len(deletable),
        'items_skipped_on_loan': len(on_loan_ids),
        'orphan_records_created': len([r for r in records if r.total_items == 0])
    }
```

**Atomic**: Single transaction — all succeed or rollback.

---

## Summary

### New Database Artifacts
- 1 new column: `item.last_inventoried_at`
- 1 new index: `ix_item_last_inventoried_at`
- 1 migration file

### Existing Models Leveraged
- `Item` (7 fields relevant to inventory, 1 new)
- `BiblographicRecord` (4 editable via bulk edit, 5 searchable filters)
- `CirculationTransaction` (for rotation filter subquery)
- `Hold` (cancelled on item deletion)

### Client-Side State
- Working table in localStorage (~600KB at school scale)
- Survives refresh, tab close (per FR-024b clarification)

### Query Complexity
- Search with all filters: 1 query with LEFT JOIN subquery, <2s
- Archive cutoff: 1 query, O(1)
- Orphan records: 1 query, no JOIN
- All queries leverage existing indexes — no new indexes except `last_inventoried_at`
