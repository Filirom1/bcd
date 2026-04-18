# Developer Quickstart: Collection Inventory Page (008)

**Date**: 2026-04-02  
**Branch**: `008-inventory-page`  
**For**: Developers implementing this feature

---

## Prerequisites

1. **Read these files in order**:
   - `spec.md` — understand user stories and requirements
   - `research.md` — understand real-world library workflows and technical decisions
   - `data-model.md` — understand database changes
   - `contracts/api-endpoints.md` — understand API contracts

2. **Read architecture docs**:
   - `.specify/architecture-patterns.md` — mandatory patterns
   - `.specify/memory/constitution.md` — project principles

3. **Development environment**:
   ```bash
   nix-shell  # Recommended (auto-creates venv, sets PYTHONPATH)
   # OR
   python3.11 -m venv venv && source venv/bin/activate
   pip install -e ".[dev]"
   ```

---

## Implementation Order (Follow This Sequence)

### Phase 1: Database (Prerequisite for All)

**File**: `migrations/versions/<hash>_add_item_last_inventoried_at.py`

```bash
# Generate migration
alembic revision -m "Add item.last_inventoried_at for collection inventory tracking"
```

**Edit the generated file**:
```python
def upgrade() -> None:
    op.add_column('item', sa.Column(
        'last_inventoried_at', sa.DateTime(), nullable=True
    ))
    op.create_index(
        'ix_item_last_inventoried_at', 'item', ['last_inventoried_at']
    )

def downgrade() -> None:
    op.drop_index('ix_item_last_inventoried_at', table_name='item')
    op.drop_column('item', 'last_inventoried_at')
```

**Apply migration**:
```bash
alembic upgrade head
```

**Verify**:
```bash
sqlite3 data/bcd.db "PRAGMA table_info(item);" | grep last_inventoried_at
```

---

### Phase 2: Backend — Service Layer (Business Logic)

**File**: `src/bcd_api/services/inventory_service.py`

**Pattern**: Follow `catalog_service.py` structure.

**Functions to implement** (in this order):

1. `mark_item_inventoried(db, item_id) -> Item`
   - Get item by `item_id` (raise `ItemNotFoundException` if not found)
   - Set `item.last_inventoried_at = datetime.now(timezone.utc)`
   - Commit
   - Return item

2. `bulk_mark_inventoried(db, item_ids) -> dict`
   - Query items with `Item.item_id.in_(item_ids)`
   - Update `last_inventoried_at` for all found
   - Return `{items_updated: count, items_not_found: [...], timestamp: ...}`

3. `search_items(db, q, status, condition, ...) -> dict`
   - Build query with LEFT JOIN subquery for rotation filter (see data-model.md Query #1)
   - Apply all filters
   - Limit 200
   - Compute `archive_cutoff_date` = `db.query(func.min(CirculationTransaction.checkout_date)).scalar()`
   - Return `{items: [...], total_count: X, displayed_count: Y, capped: bool, archive_cutoff_date: ...}`

4. `bulk_update_items(db, item_ids, item_updates, record_updates) -> dict`
   - Fetch items by `item_id.in_(item_ids)`
   - Apply `item_updates` to each (skip status changes for `on_loan` items)
   - Deduplicate records: `record_ids = {item.bibliographic_record_id for item in items}`
   - Apply `record_updates` to each unique record
   - Count other copies: `total_copies_affected = sum([record.total_items for record in records]) - len(items)`
   - Atomic transaction
   - Return counts

5. `delete_items_bulk(db, item_ids) -> dict`
   - Fetch items, exclude `on_loan`
   - Cancel holds: `db.query(Hold).filter(Hold.item_id.in_([...]))`  
   - Delete items
   - Update parent `record.total_items` counters
   - Atomic transaction
   - Return counts

6. `get_items_csv(db, item_ids) -> str`
   - Fetch items with joined bibliographic_record
   - Format as CSV string (FR-036 columns)
   - Return string

7. `get_orphan_records(db) -> dict`
   - Query `BiblographicRecord.filter_by(total_items=0)`
   - Return `{count: X, records: [...]}`

8. `delete_orphan_records(db) -> dict`
   - Get orphan record IDs
   - Call `catalog_service.bulk_delete_records(db, record_ids)`
   - Return `{records_deleted: X}`

**Test each function** in `tests/integration/services/test_inventory_service.py` (AAA pattern).

---

### Phase 3: Backend — Pydantic Schemas

**File**: `src/bcd_api/schemas/inventory.py`

Copy schema definitions from `contracts/api-endpoints.md`.

**Pattern**: Follow `schemas/item.py`, `schemas/bibliographic_record.py`.

**Key validators**:
- `from_attributes = True` for ORM compatibility
- JSON deserialization for `authors` field (use `@field_validator` like in `BiblographicRecordResponse`)

---

### Phase 4: Backend — API Routes

**File**: `src/bcd_api/api/v1/inventory.py`

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from ...core.deps import get_db
from ...schemas.inventory import *
from ...services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.patch("/items/{item_id}", response_model=ItemInventoryResponse)
def mark_item_inventoried(item_id: str, db: Session = Depends(get_db)):
    """Mark a single item as inventoried (barcode scan)."""
    return inventory_service.mark_item_inventoried(db, item_id)

@router.post("/items/bulk-mark", response_model=BulkInventoryResponse)
def bulk_mark_inventoried(request: BulkInventoryRequest, db: Session = Depends(get_db)):
    """Mark multiple items as inventoried (file import)."""
    return inventory_service.bulk_mark_inventoried(db, request.item_ids)

# ... (6 more endpoints, see contracts/api-endpoints.md)
```

**Add to router aggregator** (`src/bcd_api/api/v1/router.py`):
```python
from src.bcd_api.api.v1 import inventory
api_router.include_router(inventory.router)
```

**Admin routes** in `src/bcd_api/api/v1/admin.py`:
```python
@router.get("/catalog/orphan-records", response_model=OrphanRecordsResponse)
def get_orphan_records(db: Session = Depends(get_db)):
    """Get count and list of orphan records."""
    return inventory_service.get_orphan_records(db)

@router.delete("/catalog/orphan-records", response_model=OrphanDeleteResponse)
def delete_orphan_records(db: Session = Depends(get_db)):
    """Delete all orphan records."""
    return inventory_service.delete_orphan_records(db)
```

**Test**: Start server, visit `http://127.0.0.1:8000/api/v1/docs` — verify 8 new endpoints appear.

---

### Phase 5: Frontend — Composables

**File**: `src/bcd_web_vue/js/composables/useInventoryTable.js`

**Pattern**: Follow `useColumnSettings.js` (localStorage with safe access).

```javascript
import { ref, watch } from 'vue';

const STORAGE_KEY = 'bcd_inventory_table';

export function useInventoryTable() {
    // Load from localStorage
    const items = ref([]);
    
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            items.value = JSON.parse(stored);
        }
    } catch (e) {
        console.warn('Failed to load inventory table from localStorage', e);
    }
    
    // Save to localStorage when changed
    watch(items, (newValue) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(newValue));
        } catch (e) {
            console.warn('Failed to save inventory table to localStorage', e);
        }
    }, { deep: true });
    
    // Operations
    function addItem(item) {
        const exists = items.value.find(i => i.item_id === item.item_id);
        if (!exists) {
            items.value.unshift(item);  // Add to top
        } else {
            // Move existing to top, highlight
            items.value = [exists, ...items.value.filter(i => i.item_id !== item.item_id)];
        }
    }
    
    function removeItems(item_ids) {
        items.value = items.value.filter(i => !item_ids.includes(i.item_id));
    }
    
    function clearAll() {
        items.value = [];
    }
    
    return { items, addItem, removeItems, clearAll };
}
```

---

### Phase 6: Frontend — Components

Create under `src/bcd_web_vue/js/components/inventory/`:

1. **`ScanTab.js`** — Barcode input with `autofocus`, `@submit.prevent`, clear + refocus after scan
2. **`FileTab.js`** — File picker, parse on change, show preview (valid/unknown counts)
3. **`SearchTab.js`** — Filter form + results list (capped at 200)
4. **`WorkingTable.js`** — Checkbox table (use `useSelection()`)
5. **`BulkEditPanel.js`** — Item/record update form

**Pattern**: Follow components in `catalog/`, `circulation/`.

---

### Phase 7: Frontend — Main Page

**File**: `src/bcd_web_vue/js/pages/InventoryPage.js`

**Template**: Use `CatalogPage.js` as structure reference.

**Composables**:
```javascript
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useAppState } from '../composables/useAppState.js';
import { useNotification } from '../composables/useNotification.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useSelection } from '../composables/useSelection.js';
import { useInventoryTable } from '../composables/useInventoryTable.js';
```

**State**:
```javascript
const { items, addItem, removeItems, clearAll } = useInventoryTable();
const { selectedIds, toggleSelection, clearSelection } = useSelection();
const activeTab = ref('scan');  // 'scan', 'file', 'search'
```

**Key methods**:
- `scanBarcode(item_id)` → `PATCH /inventory/items/{item_id}` → `addItem(response)`
- `importFile(item_ids)` → `POST /inventory/items/bulk-mark` → `addItem(...)` for each
- `searchItems(filters)` → `GET /inventory/items/search` → display results
- `applyBulkEdit(updates)` → `POST /inventory/items/bulk-update`
- `deleteBulk(item_ids)` → `DELETE /inventory/items/bulk`
- `exportCSV()` → `POST /inventory/export-csv` → download

---

### Phase 8: i18n (French + English)

**Files**: `src/bcd_web_vue/locales/en.json`, `fr.json`

Add top-level `inventory` key:
```json
{
  "inventory": {
    "title": "Collection Inventory",
    "tabs": {
      "scan": "Scan",
      "file": "File Import",
      "search": "Search"
    },
    "working_table": {
      "title": "Working Table",
      "item_count": "{count} item(s)"
    },
    "bulk_edit": {
      "apply": "Apply Changes",
      "delete": "Delete Items"
    },
    "search": {
      "never_inventoried": "Never inventoried",
      "rotation_filter": "Low rotation (fewer than {max} loans since {date})",
      "results_capped": "Showing {displayed} of {total} results — refine filters"
    }
  }
}
```

**French equivalents in `fr.json`**.

---

### Phase 9: Routing

**File**: `src/bcd_web_vue/js/router.js`

```javascript
{
  path: '/inventory',
  name: 'inventory',
  component: () => import('./pages/InventoryPage.js')
}
```

**Add to navigation** (`src/bcd_web_vue/js/components/AppNavigation.js`):
```javascript
{ name: 'inventory', icon: 'bi-box-seam', label: t('navigation.inventory') }
```

---

## Testing Strategy

### Backend Tests

**File**: `tests/integration/services/test_inventory_service.py`

```python
def test_mark_item_inventoried_success(db_session):
    """Test marking single item as inventoried."""
    # ARRANGE
    item = create_test_item(db_session, item_id="0785")
    assert item.last_inventoried_at is None
    
    # ACT
    result = inventory_service.mark_item_inventoried(db_session, "0785")
    
    # ASSERT
    assert result.item_id == "0785"
    assert result.last_inventoried_at is not None
    assert (datetime.now(timezone.utc) - result.last_inventoried_at).seconds < 5

def test_bulk_update_excludes_on_loan_from_status_changes(db_session):
    # ... (FR-029 verification)

def test_rotation_filter_counts_loans_in_period(db_session):
    # ... (FR-016 verification)
```

### Frontend E2E Tests (Playwright)

**File**: `tests/e2e/test_inventory_page.py`

```python
def test_scan_barcode_adds_to_working_table(page):
    page.goto('/inventory')
    page.fill('[data-testid="barcode-input"]', '0785')
    page.press('[data-testid="barcode-input"]', 'Enter')
    assert page.locator('[data-testid="working-table-row"]').count() == 1
```

---

## Common Pitfalls

❌ **Don't**: Put business logic in API routes  
✅ **Do**: Put all logic in `inventory_service.py`

❌ **Don't**: Modify `catalog_service.py` for inventory logic  
✅ **Do**: Create separate `inventory_service.py`

❌ **Don't**: Hardcode strings in Vue components  
✅ **Do**: Use `{{ t('inventory.key') }}`

❌ **Don't**: Forget timezone-aware timestamps  
✅ **Do**: Use `datetime.now(timezone.utc)` (not `datetime.now()`)

❌ **Don't**: Skip the migration downgrade() function  
✅ **Do**: Write reversible migrations

---

## Ready to Start?

1. Checkout branch: `git checkout 008-inventory-page`
2. Run migration: `alembic upgrade head`
3. Start backend: `python -m uvicorn src.bcd_api.main:app --reload`
4. Start frontend: Open `http://127.0.0.1:8000` in browser
5. Follow implementation order above
6. Run tests after each phase: `pytest tests/integration/services/test_inventory_service.py -v`

---

## Need Help?

- Architecture questions → see `.specify/architecture-patterns.md`
- Service patterns → read `src/bcd_api/services/catalog_service.py`
- Vue patterns → read `src/bcd_web_vue/js/pages/CatalogPage.js`
- Error handling → see `src/bcd_api/core/exceptions.py`
- i18n → see `src/bcd_web_vue/locales/en.json` structure
