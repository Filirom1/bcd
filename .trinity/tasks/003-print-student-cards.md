# Task 3: Student Library Cards Component

## Goal

Create `PrintStudentCards.js` - a print view that renders individual credit-card-sized library cards for students in a 2x5 grid per A4 page. Cards are printed on card stock and given to students for checkout.

## Dependencies

- **Task 1** must be complete (JsBarcode CDN loaded, route registered, print CSS exists)
- **Task 2** is a reference for the component pattern (read `PrintBorrowerReference.js` for exact conventions)

## Files to Read First

| File | Why |
|------|-----|
| `src/bcd_web_vue/js/pages/PrintBorrowerReference.js` | Exact same component pattern to follow (created in Task 2) |
| `src/bcd_web_vue/js/pages/BorrowersPage.js` | Borrower API endpoint: `GET /api/v1/borrowers?page=1&page_size=500` returns `{ items: [...] }` |
| `src/bcd_web_vue/css/print-labels.css` | Card CSS classes: `card-grid`, `library-card`, `card-header`, etc. |

## Existing Patterns (from codebase)

**Vue CDN globals** (NO ES6 imports for Vue/VueRouter/VueI18n):
```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
```

**Settings API** (for library name):
```javascript
const response = await fetch('/api/v1/admin/settings');
const settings = await response.json();
// settings.library_name = "BCD" (or custom name)
// settings.barcode_type = "code39" or "code128"
```

## File to Create

### `src/bcd_web_vue/js/pages/PrintStudentCards.js`

**Full component specification:**

```javascript
const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;

export default defineComponent({
    name: 'PrintStudentCards',

    setup() {
        const { t } = useI18n();
        const route = useRoute();
        const borrowers = ref([]);
        const settings = ref(null);
        const loading = ref(true);
        const error = ref(null);

        const totalCount = computed(() => borrowers.value.length);

        onMounted(async () => {
            try {
                // Fetch borrowers and settings in parallel
                const params = new URLSearchParams({
                    page: 1,
                    page_size: 500
                });

                // Support class filter from URL
                const classIds = route.query.class_ids;
                if (classIds) {
                    params.set('class_id', classIds);
                }

                const [borrowerRes, settingsRes] = await Promise.all([
                    fetch(`/api/v1/borrowers?${params}`),
                    fetch('/api/v1/admin/settings')
                ]);

                if (!borrowerRes.ok) throw new Error('Failed to load borrowers');

                const borrowerData = await borrowerRes.json();
                borrowers.value = borrowerData.items || borrowerData.borrowers || [];

                if (settingsRes.ok) {
                    settings.value = await settingsRes.json();
                }

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
                        height: 40,
                        displayValue: false
                    });
                }
            });
        };

        const libraryName = computed(() =>
            settings.value?.library_name || 'BCD'
        );

        const printPage = () => window.print();

        return { t, borrowers, loading, error, totalCount, libraryName, printPage };
    },

    template: `
        <div class="print-page">
            <!-- Toolbar (hidden when printing) -->
            <div class="print-toolbar no-print">
                <h2>{{ t('admin.print_student_cards') }}</h2>
                <div>
                    <span class="text-muted me-3">{{ totalCount }} cards</span>
                    <button class="btn btn-primary" @click="printPage">
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
            <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

            <!-- Card Grid: 2 columns x 5 rows = 10 cards per A4 page -->
            <div v-else class="card-grid">
                <div
                    v-for="student in borrowers"
                    :key="student.id"
                    class="library-card"
                >
                    <div class="card-header">
                        {{ libraryName }}
                        <span v-if="student.class_name"> - {{ student.class_name }}</span>
                    </div>

                    <div class="card-body">
                        <div class="card-photo">
                            <!-- Photo placeholder -->
                        </div>

                        <div class="card-info">
                            <div class="card-name">
                                {{ student.last_name }} {{ student.first_name }}
                            </div>
                            <div class="card-id">{{ student.borrower_id }}</div>
                            <div class="card-role">
                                {{ student.role === 'student' ? 'Eleve' : student.role }}
                            </div>
                        </div>
                    </div>

                    <div class="card-barcode">
                        <svg class="barcode" :data-code="student.barcode"></svg>
                        <div class="barcode-text">{{ student.barcode }}</div>
                    </div>
                </div>
            </div>
        </div>
    `
});
```

## Key Technical Details

- **Card dimensions**: 85mm x 54mm (ISO/IEC 7810 ID-1 standard, credit card size)
- **Grid**: 2 columns x 5 rows = 10 cards per A4 page
- **API endpoints**: Same borrower API as Task 2, plus `GET /api/v1/admin/settings` for library name
- **Barcode format**: Read from `settings.barcode_type` (code39 or code128), default to CODE39
- **Photo placeholder**: Empty div with border - future feature to add actual photos
- **Parallel fetch**: Use `Promise.all` to fetch borrowers and settings simultaneously
- **CSS classes** (from `print-labels.css`): `print-page`, `print-toolbar`, `card-grid`, `library-card`, `card-header`, `card-body`, `card-photo`, `card-info`, `card-name`, `card-id`, `card-role`, `card-barcode`

## Verification

1. Navigate to `http://127.0.0.1:8000/#/print/borrowers/cards`
2. Verify:
   - No sidebar visible
   - Cards arranged in 2-column grid
   - Each card shows: library name, class, photo placeholder, student name, ID, barcode
   - Barcodes render as visible barcode images
3. Ctrl+P:
   - 10 cards fit per A4 page
   - Card borders visible for cutting guides
   - Toolbar hidden
4. `pytest tests/integration tests/unit` - no regressions
