# Task 4: Item Labels Component

## Goal

Create `PrintItemLabels.js` - a print view that renders Avery-compatible sticker labels (3x4 grid per page) for book items, with barcodes for scanning during circulation. Labels are printed on Avery 5160/6479 sticker sheets and attached to physical books.

## Dependencies

- **Task 1** must be complete (JsBarcode CDN loaded, route registered, print CSS exists)
- **Task 2** is a reference for the component pattern

## Files to Read First

| File | Why |
|------|-----|
| `src/bcd_web_vue/js/pages/PrintBorrowerReference.js` | Component pattern to follow (created in Task 2) |
| `src/bcd_web_vue/js/pages/CatalogPage.js` | Catalog API: `apiClient.get('/catalog/bibliographic/search', params)` at line 192 returns `{ items: [...], total: N }` |
| `src/bcd_web_vue/js/api/client.js` | API client import: `import { apiClient } from '../api/client.js'` |
| `src/bcd_web_vue/css/print-labels.css` | Label CSS classes: `label-grid`, `item-label`, `label-barcode`, etc. |

## Critical: N+1 Data Fetching

There is **NO direct "list all items" API endpoint**. Items belong to bibliographic records. The fetch pattern is:

1. **Step 1**: `GET /api/v1/catalog/bibliographic/search?limit=100&offset=0` - get all bibliographic records
   - Returns: `{ items: [{ id, title, authors, ... }], total: N }`
   - Paginate if `total > 100` (fetch additional pages)

2. **Step 2**: For each record, `GET /api/v1/catalog/bibliographic/{id}/items` - get physical items
   - Returns array of items, each with: `item_id`, `barcode`, `status`, etc.
   - The `item_id` is the barcode value to encode

3. **Flatten**: Collect all items from all records into a single array

**Performance**: Use `Promise.all()` in batches of 10 for parallel fetching. For a typical school library (200-500 records), this completes in a few seconds.

## Existing Patterns (from codebase)

**Vue CDN globals**:
```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
```

**API client import** (used in CatalogPage.js line 9):
```javascript
import { apiClient } from '../api/client.js';
```

**apiClient usage** (CatalogPage.js line 192):
```javascript
const data = await apiClient.get('/catalog/bibliographic/search', { limit: 100, offset: 0 });
// Returns: { items: [...], total: N }
```

## File to Create

### `src/bcd_web_vue/js/pages/PrintItemLabels.js`

**Full component specification:**

```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../api/client.js';

export default defineComponent({
    name: 'PrintItemLabels',

    setup() {
        const { t } = useI18n();
        const items = ref([]);
        const settings = ref(null);
        const loading = ref(true);
        const error = ref(null);
        const loadingProgress = ref('');

        const totalCount = computed(() => items.value.length);

        /**
         * Fetch all items via N+1 pattern:
         * 1. Get all bibliographic records (paginated)
         * 2. For each record, get its physical items
         * 3. Flatten into single items array
         */
        const fetchAllItems = async () => {
            const allItems = [];
            let offset = 0;
            const pageSize = 100;
            let total = 0;

            // Step 1: Fetch all bibliographic records (paginated)
            do {
                loadingProgress.value = `Loading records (${offset}/${total || '?'})...`;
                const data = await apiClient.get('/catalog/bibliographic/search', {
                    limit: pageSize,
                    offset: offset
                });

                const records = data.items || [];
                total = data.total || 0;

                // Step 2: Fetch items for each record in batches of 10
                for (let i = 0; i < records.length; i += 10) {
                    const batch = records.slice(i, i + 10);
                    loadingProgress.value = `Loading items (${offset + i + 1}/${total} records)...`;

                    const batchResults = await Promise.all(
                        batch.map(record =>
                            apiClient.get(`/catalog/bibliographic/${record.id}/items`)
                                .catch(() => []) // Skip records that fail
                        )
                    );

                    // Flatten: each result is an array of items
                    batchResults.forEach((recordItems, idx) => {
                        const record = batch[idx];
                        const itemList = Array.isArray(recordItems) ? recordItems : (recordItems.items || []);
                        itemList.forEach(item => {
                            allItems.push({
                                ...item,
                                record_title: record.title // Keep reference to parent
                            });
                        });
                    });
                }

                offset += pageSize;
            } while (offset < total);

            return allItems;
        };

        onMounted(async () => {
            try {
                // Fetch items and settings in parallel
                const [allItems, settingsRes] = await Promise.all([
                    fetchAllItems(),
                    fetch('/api/v1/admin/settings').then(r => r.ok ? r.json() : null)
                ]);

                items.value = allItems;
                settings.value = settingsRes;
                loading.value = false;

                // Render barcodes after DOM update
                await nextTick();
                renderBarcodes();
            } catch (err) {
                error.value = err.message;
                loading.value = false;
            }
        });

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

        const libraryName = computed(() =>
            settings.value?.library_name || 'BCD'
        );

        const printPage = () => window.print();

        return {
            t, items, loading, error, loadingProgress,
            totalCount, libraryName, printPage
        };
    },

    template: `
        <div class="print-page">
            <!-- Toolbar (hidden when printing) -->
            <div class="print-toolbar no-print">
                <h2>{{ t('admin.print_item_labels') }}</h2>
                <div>
                    <span class="text-muted me-3">{{ totalCount }} labels</span>
                    <button class="btn btn-primary" @click="printPage" :disabled="loading">
                        <i class="bi bi-printer me-1"></i>
                        {{ t('reports.print') }}
                    </button>
                </div>
            </div>

            <!-- Loading with progress -->
            <div v-if="loading" class="text-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted">{{ loadingProgress || t('common.loading') }}</p>
            </div>

            <!-- Error -->
            <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

            <!-- Label Grid: 3 columns x 4 rows = 12 labels per page -->
            <div v-else class="label-grid">
                <div
                    v-for="item in items"
                    :key="item.id"
                    class="item-label"
                >
                    <div class="label-barcode">
                        <svg class="barcode" :data-code="item.item_id"></svg>
                    </div>
                    <div class="label-id">{{ item.item_id }}</div>
                    <div class="label-library">{{ libraryName }}</div>
                </div>
            </div>
        </div>
    `
});
```

## Key Technical Details

- **Label dimensions**: 66mm x 25mm (Avery 5160/6479 compatible)
- **Grid**: 3 columns x 4 rows = 12 labels per page
- **Barcode value**: `item.item_id` is the barcode to encode (this is the physical copy identifier)
- **N+1 fetch**: Unavoidable with current API. Batched with `Promise.all` in groups of 10.
- **Progress indicator**: Shows "Loading items (45/120 records)..." during fetch
- **apiClient**: Import from `'../api/client.js'` (used by CatalogPage, not raw `fetch`)
- **Dashed borders**: Visible on screen as alignment guides, hidden when printing (CSS handles this)
- **CSS classes** (from `print-labels.css`): `print-page`, `print-toolbar`, `label-grid`, `item-label`, `label-barcode`, `label-id`, `label-library`

## Edge Cases

- **Empty catalog**: Show "0 labels" with no grid
- **Records with no items**: Skip gracefully (items array will be empty)
- **API errors for individual records**: Caught and skipped via `.catch(() => [])`, does not break the whole page
- **Large catalogs (500+ records)**: Pagination in fetchAllItems handles this, progress indicator keeps user informed

## Verification

1. Navigate to `http://127.0.0.1:8000/#/print/catalog/labels`
2. Verify:
   - No sidebar visible
   - Progress indicator shows while loading
   - Labels arranged in 3-column grid with dashed borders
   - Each label shows: barcode image, item ID, library name
   - Barcodes render as visible barcode images
3. Ctrl+P:
   - Dashed borders disappear
   - 12 labels per page
   - Clean print preview suitable for Avery sticker sheets
4. `pytest tests/integration tests/unit` - no regressions
