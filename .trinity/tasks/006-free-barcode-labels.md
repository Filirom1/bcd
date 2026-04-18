# Task 6: Free Barcode Label Printing (Fix Item Labels)

## Goal

Redesign the PrintItemLabels component to print FREE barcode IDs (not yet assigned to any books) that librarians will stick on physical books before cataloging them.

**User Workflow:**
1. Print a batch of FREE barcode labels (IDs not assigned to any items yet)
2. Physically stick these labels on new books
3. Later, scan the barcode + ISBN to register the book in the system

This replaces the incorrect implementation that filtered existing items without barcodes.

## Dependencies

- **Task 1** (Infrastructure Setup) must be complete
- **Task 4** (Item Labels) exists but has wrong logic - will be replaced

## Current System Analysis

From codebase exploration:

**Item ID Management:**
- Item IDs are **user-provided**, not auto-generated
- Format is **configurable** via SystemSettings (singleton table, id=1):
  - `id_format`: "numeric" (default) or "alphanumeric"
  - `id_validation_regex`: Default `^\d+$` for numeric only
  - `id_length_min`, `id_length_max`: Default 1-10 characters
- Current sample data uses **pure numeric IDs**: 785, 787, 788, 1151, 1152
- **No separate barcode field** - the item_id itself is what gets encoded as a barcode
- Barcode symbology (CODE39/CODE128) is just the encoding method

**Key Files:**
- `src/bcd_api/models/item.py` - Item model with item_id field
- `src/bcd_api/models/system_settings.py` - ID format configuration
- `src/bcd_api/services/catalog_service.py` - Item creation and ID checking logic

## Files to Read First

| File | Why |
|------|-----|
| `src/bcd_api/models/item.py` | Item model, item_id field definition |
| `src/bcd_api/models/system_settings.py` | ID format configuration fields |
| `src/bcd_api/services/catalog_service.py` | Existing item creation and duplicate checking |
| `src/bcd_api/schemas/item.py` | Item schemas (will add AvailableIDsResponse) |
| `src/bcd_api/api/v1/catalog.py` | Catalog API endpoints (will add new endpoint) |
| `src/bcd_web_vue/js/pages/PrintItemLabels.js` | Current component (needs full redesign) |

## Changes

### 1. Add `AvailableIDsResponse` Schema

**File:** `src/bcd_api/schemas/item.py`

Add new schema at the end of the file, after existing schemas:

```python
class AvailableIDsResponse(BaseModel):
    """Response schema for available item IDs endpoint."""
    start_id: str = Field(..., description="First ID in the generated range")
    end_id: str = Field(..., description="Last ID in the generated range")
    ids: list[str] = Field(..., description="List of available item IDs")
    count: int = Field(..., description="Number of IDs generated")
    id_format: str = Field(..., description="ID format (numeric or alphanumeric)")

    class Config:
        json_schema_extra = {
            "example": {
                "start_id": "2000",
                "end_id": "2029",
                "ids": ["2000", "2001", "2002"],
                "count": 30,
                "id_format": "numeric"
            }
        }
```

### 2. Add Service Function for ID Generation

**File:** `src/bcd_api/services/catalog_service.py`

Add new function after existing functions (around line 600+):

```python
def get_available_item_ids(
    db: Session,
    count: int = 30,
    start_from: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a list of available item IDs that are not currently in use.

    For numeric ID format, generates sequential IDs starting from max+1 or start_from.
    For alphanumeric ID format, raises NotImplementedError (future enhancement).

    Args:
        db: Database session
        count: Number of IDs to generate (1-1000)
        start_from: Optional starting ID (if omitted, auto-detect next available)

    Returns:
        Dictionary with start_id, end_id, ids list, count, and id_format

    Raises:
        NotImplementedError: If id_format is alphanumeric (not yet supported)
        ValueError: If count is out of range or start_from is invalid
    """
    from .settings_service import get_settings
    from sqlalchemy import cast, Integer

    # Get system settings for ID format
    settings = get_settings(db)

    # Validate count
    if count < 1 or count > 1000:
        raise ValueError("Count must be between 1 and 1000")

    if settings.id_format == IDFormat.NUMERIC.value:
        # Find the maximum numeric ID currently in use
        max_item = db.query(Item).order_by(
            cast(Item.item_id, Integer).desc()
        ).first()

        if start_from:
            try:
                next_id = int(start_from)
            except ValueError:
                raise ValueError(f"Invalid start_from value for numeric format: {start_from}")
        else:
            # Auto-detect: start from max+1, or 1 if no items exist
            next_id = (int(max_item.item_id) + 1) if max_item else 1

        # Generate sequential numeric IDs
        ids = [str(next_id + i) for i in range(count)]

        return {
            "start_id": ids[0],
            "end_id": ids[-1],
            "ids": ids,
            "count": count,
            "id_format": settings.id_format
        }

    else:  # alphanumeric
        # For alphanumeric, would need to parse pattern (e.g., ITEM001)
        # and generate next IDs following that pattern
        # Not implemented yet - future enhancement
        raise NotImplementedError(
            "Alphanumeric ID generation not yet implemented. "
            "Please set id_format to 'numeric' in system settings."
        )
```

**Import needed at top of file:**
```python
from typing import Optional, Dict, Any  # Add to existing imports
```

### 3. Add API Endpoint

**File:** `src/bcd_api/api/v1/catalog.py`

Add new endpoint after existing catalog endpoints (around line 600+):

```python
@router.get(
    "/items/available-ids",
    response_model=AvailableIDsResponse,
    summary="Generate available item IDs for pre-printing barcode labels"
)
def get_available_item_ids_endpoint(
    count: int = Query(default=30, ge=1, le=1000, description="Number of IDs to generate"),
    start_from: Optional[str] = Query(default=None, description="Starting ID (optional, auto-detect if omitted)"),
    db: Session = Depends(get_db)
):
    """
    Generate a list of available item IDs that are not currently assigned to any items.

    This endpoint is used by the print labels page to generate free barcode IDs
    that can be pre-printed on sticker labels and applied to books before cataloging.

    **Workflow:**
    1. Librarian calls this endpoint to get a batch of free IDs
    2. Print barcode labels with these IDs
    3. Stick labels on physical books
    4. Later, scan barcode + ISBN to register books in the system

    **ID Format:**
    - Respects system settings (numeric or alphanumeric)
    - Numeric format: sequential IDs from max+1 (e.g., 2000, 2001, 2002...)
    - Alphanumeric format: not yet implemented (raises NotImplementedError)

    **Parameters:**
    - count: How many IDs to generate (default: 30 labels = 2.5 Avery sheets)
    - start_from: Optional starting ID (if omitted, starts from max existing ID + 1)

    **Returns:**
    - start_id: First ID in range
    - end_id: Last ID in range
    - ids: Array of all generated IDs
    - count: Number of IDs generated
    - id_format: Current ID format setting

    **Example Response:**
    ```json
    {
      "start_id": "2000",
      "end_id": "2029",
      "ids": ["2000", "2001", "2002", ..., "2029"],
      "count": 30,
      "id_format": "numeric"
    }
    ```
    """
    try:
        return catalog_service.get_available_item_ids(db, count, start_from)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
```

**Import needed at top of file:**
```python
from ..schemas.item import AvailableIDsResponse  # Add to existing imports
from typing import Optional  # Add if not already imported
```

### 4. Redesign Frontend Component

**File:** `src/bcd_web_vue/js/pages/PrintItemLabels.js`

**Replace entire file contents with:**

```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'PrintItemLabels',

    setup() {
        const { t } = useI18n();
        const startId = ref('');  // Empty = auto-detect next available
        const labelCount = ref(30);  // Default to 30 labels (2.5 Avery sheets)
        const generatedIds = ref([]);
        const loading = ref(false);
        const error = ref(null);
        const settings = ref(null);

        const totalCount = computed(() => generatedIds.value.length);
        const libraryName = computed(() => settings.value?.library_name || 'BCD');

        // Fetch settings on mount
        onMounted(async () => {
            try {
                const settingsRes = await fetch('/api/v1/admin/settings');
                if (settingsRes.ok) {
                    settings.value = await settingsRes.json();
                }
            } catch (err) {
                console.error('Failed to load settings:', err);
            }

            // Auto-generate IDs on page load
            generateIds();
        });

        // Generate available IDs from API
        const generateIds = async () => {
            loading.value = true;
            error.value = null;

            try {
                const params = new URLSearchParams({
                    count: labelCount.value
                });

                if (startId.value && startId.value.trim() !== '') {
                    params.set('start_from', startId.value.trim());
                }

                const response = await fetch(`/api/v1/catalog/items/available-ids?${params}`);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to generate IDs');
                }

                const data = await response.json();
                generatedIds.value = data.ids;
                loading.value = false;

                // Render barcodes after DOM updates
                await nextTick();
                renderBarcodes();
            } catch (err) {
                error.value = err.message;
                loading.value = false;
            }
        };

        const renderBarcodes = () => {
            const format = (settings.value?.barcode_type || 'code39').toUpperCase();
            document.querySelectorAll('.barcode').forEach((svg) => {
                if (svg.dataset.code) {
                    JsBarcode(svg, svg.dataset.code, {
                        format: format,
                        width: 1.5,
                        height: 35,
                        displayValue: false
                    });
                }
            });
        };

        const printPage = () => window.print();

        return {
            t,
            startId,
            labelCount,
            generatedIds,
            loading,
            error,
            totalCount,
            libraryName,
            generateIds,
            printPage
        };
    },

    template: `
        <div class="print-page">
            <!-- Toolbar (hidden when printing) -->
            <div class="print-toolbar no-print">
                <h2>{{ t('admin.print_item_labels') }}</h2>

                <!-- Controls for ID generation -->
                <div class="controls mb-3">
                    <div class="row g-2">
                        <div class="col-md-4">
                            <label class="form-label">Starting ID (optional)</label>
                            <input
                                v-model="startId"
                                type="text"
                                class="form-control"
                                placeholder="Auto-detect next available"
                                :disabled="loading"
                            />
                            <small class="form-text text-muted">
                                Leave empty to start from next available ID
                            </small>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Number of Labels</label>
                            <input
                                v-model.number="labelCount"
                                type="number"
                                class="form-control"
                                min="1"
                                max="1000"
                                :disabled="loading"
                            />
                            <small class="form-text text-muted">
                                30 labels = 2.5 Avery sheets
                            </small>
                        </div>
                        <div class="col-md-3 d-flex align-items-end">
                            <button
                                class="btn btn-secondary"
                                @click="generateIds"
                                :disabled="loading"
                            >
                                <i class="bi bi-arrow-clockwise me-1"></i>
                                Generate IDs
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Print button and counter -->
                <div class="d-flex justify-content-between align-items-center">
                    <span class="text-muted">{{ totalCount }} labels ready to print</span>
                    <button
                        class="btn btn-primary"
                        @click="printPage"
                        :disabled="loading || totalCount === 0"
                    >
                        <i class="bi bi-printer me-1"></i>
                        {{ t('reports.print') }}
                    </button>
                </div>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="text-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted">{{ t('common.loading') }}</p>
            </div>

            <!-- Error -->
            <div v-else-if="error" class="alert alert-danger no-print">{{ error }}</div>

            <!-- Empty state -->
            <div v-else-if="totalCount === 0" class="alert alert-info no-print">
                No IDs generated. Click "Generate IDs" to create barcode labels.
            </div>

            <!-- Label Grid: 3 columns x 4 rows = 12 labels per page -->
            <div v-else class="label-grid">
                <div
                    v-for="id in generatedIds"
                    :key="id"
                    class="item-label"
                >
                    <div class="label-barcode">
                        <svg class="barcode" :data-code="id"></svg>
                    </div>
                    <div class="label-id">{{ id }}</div>
                    <div class="label-library">{{ libraryName }}</div>
                </div>
            </div>
        </div>
    `
});
```

### 5. Update CSS for Controls

**File:** `src/bcd_web_vue/css/print-labels.css`

Add at the end of the file, before the closing comment:

```css
/* --- Controls Section (Item Labels Page) --- */

.print-toolbar .controls {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 4px;
    border: 1px solid #dee2e6;
    margin-bottom: 15px;
}

.print-toolbar .controls .form-label {
    font-weight: 600;
    font-size: 0.9em;
    margin-bottom: 4px;
}

.print-toolbar .controls .form-text {
    font-size: 0.75em;
}

@media print {
    .controls {
        display: none !important;
    }
}
```

## Key Technical Details

- **ID Generation**: Backend generates sequential numeric IDs from max+1
- **No Gap Filling**: If IDs 785, 787, 788 exist, next batch starts at 789 (not 786). Sequential is simpler and safer.
- **Alphanumeric Format**: Not implemented yet. Raises NotImplementedError if id_format is "alphanumeric". Future enhancement.
- **Concurrent Users**: If two librarians generate labels simultaneously, they might get overlapping ID ranges. This is acceptable - when books are registered later, the system will detect duplicates and reject them.
- **Default Count**: 30 labels = 2.5 Avery 5160 sheets (12 labels per sheet)
- **Max Count**: 1000 labels to prevent abuse
- **Auto-Load**: Page auto-generates IDs on mount for immediate printing

## Verification

1. **Start server:**
   ```bash
   python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
   ```

2. **Test API endpoint directly:**
   ```bash
   # Get 10 free IDs starting from next available
   curl http://127.0.0.1:8000/api/v1/catalog/items/available-ids?count=10

   # Get 20 free IDs starting from 5000
   curl "http://127.0.0.1:8000/api/v1/catalog/items/available-ids?count=20&start_from=5000"
   ```

3. **Test frontend:**
   - Navigate to `http://127.0.0.1:8000/#/print/catalog/labels`
   - Verify page loads with 30 labels auto-generated
   - Verify labels show sequential IDs (e.g., 1154, 1155, 1156... if max existing is 1153)
   - Change starting ID to 2000, click "Generate IDs"
   - Verify labels now show 2000-2029
   - Change count to 60, click "Generate IDs"
   - Verify 60 labels are shown (5 Avery sheets)
   - Click Print button
   - Verify print preview shows clean Avery-compatible grid (3x4)
   - Verify controls are hidden in print preview
   - Verify barcodes render correctly

4. **Run tests:**
   ```bash
   pytest tests/integration/services/test_catalog_service.py -v
   ```

5. **Test edge cases:**
   - Try invalid starting ID (non-numeric): should show error
   - Try count = 0: should show error
   - Try count = 2000: should show error (max 1000)
   - Verify barcode symbology respects settings (CODE39 vs CODE128)

## Files Modified

**Backend (4 files):**
- `src/bcd_api/schemas/item.py` - Add AvailableIDsResponse schema
- `src/bcd_api/services/catalog_service.py` - Add get_available_item_ids() function
- `src/bcd_api/api/v1/catalog.py` - Add GET /items/available-ids endpoint
- `tests/integration/services/test_catalog_service.py` - Add tests (optional but recommended)

**Frontend (2 files):**
- `src/bcd_web_vue/js/pages/PrintItemLabels.js` - Complete redesign with controls
- `src/bcd_web_vue/css/print-labels.css` - Add control styles
