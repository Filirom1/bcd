# Task 2: Borrower Reference Sheet Component

## Goal

Create `PrintBorrowerReference.js` - a full-page print view that shows ALL students grouped by class, each with a barcode image. This is a reference guide for the librarian to quickly find the right barcode for the right student.

## Dependencies

- **Task 1** must be complete (JsBarcode CDN loaded, route registered, print CSS exists, sidebar hidden on print routes)

## Files to Read First

| File | Why |
|------|-----|
| `src/bcd_web_vue/js/pages/BorrowersPage.js` | Borrower API endpoint and response shape |
| `src/bcd_web_vue/js/composables/useReport.js` | `printReport()` pattern (`window.print()`) |
| `src/bcd_web_vue/js/api/client.js` | API client usage (but this component can use `fetch` directly like BorrowersPage does) |
| `src/bcd_web_vue/css/print-labels.css` | CSS classes to use in template |
| `src/bcd_web_vue/locales/en.json` | Confirm i18n keys: `admin.print_borrower_reference` |

## Existing Patterns to Follow

From reading the codebase, these are the exact patterns used by all page components:

**Vue globals (CDN pattern - NO ES6 imports for Vue)**:
```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
```

**Component export pattern**:
```javascript
export default defineComponent({
    name: 'ComponentName',
    setup() { ... },
    template: `...`
});
```

**API call pattern** (from BorrowersPage.js line 195-207):
```javascript
const params = new URLSearchParams({ page: 1, page_size: 500 });
const response = await fetch(`/api/v1/borrowers?${params}`);
const data = await response.json();
// Response: { items: [...], total: N }
// Each borrower has: id, borrower_id, barcode, first_name, last_name, class_name, role
```

## File to Create

### `src/bcd_web_vue/js/pages/PrintBorrowerReference.js`

**Full component specification:**

```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;

export default defineComponent({
    name: 'PrintBorrowerReference',

    setup() {
        const { t } = useI18n();
        const route = useRoute();
        const borrowers = ref([]);
        const loading = ref(true);
        const error = ref(null);

        // Group borrowers by class_name, sorted alphabetically
        const borrowersByClass = computed(() => {
            const grouped = {};
            borrowers.value.forEach(b => {
                const className = b.class_name || 'Sans classe';
                if (!grouped[className]) grouped[className] = [];
                grouped[className].push(b);
            });

            // Sort students within each class by last_name, then first_name
            for (const className in grouped) {
                grouped[className].sort((a, b) =>
                    (a.last_name || '').localeCompare(b.last_name || '') ||
                    (a.first_name || '').localeCompare(b.first_name || '')
                );
            }

            // Return sorted by class name
            return Object.fromEntries(
                Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b))
            );
        });

        const totalCount = computed(() => borrowers.value.length);

        onMounted(async () => {
            try {
                // Build query - support optional class filter via URL query param
                const params = new URLSearchParams({
                    page: 1,
                    page_size: 500
                });

                // ?class_ids=3 filters to a specific class
                const classIds = route.query.class_ids;
                if (classIds) {
                    params.set('class_id', classIds);
                }

                const response = await fetch(`/api/v1/borrowers?${params}`);
                if (!response.ok) throw new Error('Failed to load borrowers');

                const data = await response.json();
                borrowers.value = data.items || data.borrowers || [];
                loading.value = false;

                // Render barcodes after DOM updates
                await nextTick();
                renderBarcodes();
            } catch (err) {
                error.value = err.message;
                loading.value = false;
            }
        });

        const renderBarcodes = () => {
            document.querySelectorAll('.barcode').forEach((svg) => {
                if (svg.dataset.code) {
                    JsBarcode(svg, svg.dataset.code, {
                        format: 'CODE39',
                        width: 2,
                        height: 50,
                        displayValue: false
                    });
                }
            });
        };

        const printPage = () => window.print();

        return { t, borrowersByClass, loading, error, totalCount, printPage };
    },

    template: `
        <div class="print-page">
            <!-- Toolbar (hidden when printing) -->
            <div class="print-toolbar no-print">
                <h2>{{ t('admin.print_borrower_reference') }}</h2>
                <div>
                    <span class="text-muted me-3">{{ totalCount }} borrowers</span>
                    <button class="btn btn-primary" @click="printPage">
                        <i class="bi bi-printer me-1"></i>
                        {{ t('reports.print') }}
                    </button>
                </div>
            </div>

            <!-- Loading state -->
            <div v-if="loading" class="text-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted">{{ t('common.loading') }}</p>
            </div>

            <!-- Error state -->
            <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

            <!-- Content: students grouped by class -->
            <div v-else>
                <div
                    v-for="(students, className) in borrowersByClass"
                    :key="className"
                    class="class-section"
                >
                    <h1 class="class-header">{{ className }}</h1>

                    <div
                        v-for="student in students"
                        :key="student.id"
                        class="borrower-row"
                    >
                        <div class="borrower-id">{{ student.borrower_id }}</div>
                        <div class="borrower-barcode">
                            <svg class="barcode" :data-code="student.barcode"></svg>
                            <div class="barcode-text">{{ student.barcode }}</div>
                        </div>
                        <div class="borrower-name">
                            {{ student.last_name }} {{ student.first_name }}
                        </div>
                        <div class="borrower-status">
                            {{ student.role === 'student' ? 'Eleve' : student.role }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});
```

## Key Technical Details

- **API endpoint**: `GET /api/v1/borrowers?page=1&page_size=500` - returns `{ items: [...], total: N }`
- **Borrower fields**: `id`, `borrower_id`, `barcode`, `first_name`, `last_name`, `class_name`, `role`
- **Barcode rendering**: `JsBarcode` is a global (loaded via CDN in index.html). Call it on `<svg>` elements after DOM renders via `nextTick()`
- **Barcode format**: CODE39 (default). The plan mentions reading from settings but CODE39 is the safe default.
- **Class filter**: URL query `?class_ids=3` gets passed as `class_id` param to API
- **CSS classes**: All defined in `print-labels.css` (Task 1): `print-page`, `print-toolbar`, `no-print`, `class-section`, `class-header`, `borrower-row`, `borrower-id`, `borrower-barcode`, `barcode`, `barcode-text`, `borrower-name`, `borrower-status`
- **Print**: Uses `window.print()` pattern from `useReport.js`

## Verification

1. Start server: `python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000`
2. Ensure data exists: `python reset_and_simulate.py` if database is empty
3. Navigate to `http://127.0.0.1:8000/#/print/borrowers/reference`
4. Verify:
   - No sidebar visible
   - Students grouped by class with class name headers
   - Each student shows: ID, barcode image, name, role
   - Barcodes render as visible barcode images (not empty SVGs)
   - Print toolbar visible at top with Print button
5. Click Print or Ctrl+P:
   - Print preview shows clean layout
   - Toolbar is hidden
   - Each class starts on a new page
6. `pytest tests/integration tests/unit` - no regressions
