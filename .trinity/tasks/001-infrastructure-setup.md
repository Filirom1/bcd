# Task 1: Infrastructure Setup

## Goal

Set up all shared infrastructure for the barcode printing feature: JsBarcode CDN library, print CSS file, Vue routes, sidebar-hiding layout logic, and i18n keys. After this task, the 3 print routes exist and render with no sidebar, but the page components themselves don't exist yet.

## Dependencies

None - this task runs first.

## Files to Read First

Read these files to understand the existing patterns before making changes:

| File | Why |
|------|-----|
| `src/bcd_web_vue/index.html` | CDN script locations, CSS link locations |
| `src/bcd_web_vue/js/router.js` | Route definition pattern, imports |
| `src/bcd_web_vue/js/components/App.js` | Layout structure, sidebar rendering |
| `src/bcd_web_vue/css/main.css` | CSS variable naming conventions |
| `src/bcd_web_vue/locales/en.json` | i18n key structure (admin section) |
| `src/bcd_web_vue/locales/fr.json` | Same |

## Changes

### 1. Modify `src/bcd_web_vue/index.html`

**Add JsBarcode CDN** - Insert before the app.js script tag (before line 121):

```html
<!-- JsBarcode for client-side barcode generation -->
<script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
```

**Add print CSS link** - Insert in `<head>` after the loading.css link (after line 17):

```html
<link rel="stylesheet" href="/static/css/print-labels.css">
```

### 2. Create `src/bcd_web_vue/css/print-labels.css`

Create this new file with ALL print CSS for the 3 print page types. This includes:

```css
/* =================================================================
   Print Labels CSS - Barcode printing layouts
   Covers: Borrower Reference Sheets, Student Library Cards, Item Labels
   ================================================================= */

/* --- Base Print Rules --- */
@media print {
    /* Hide all UI chrome when printing */
    .sidebar,
    .navbar,
    .breadcrumb,
    .no-print,
    .print-toolbar {
        display: none !important;
    }

    body {
        margin: 0;
        padding: 0;
    }

    .main-content {
        margin-left: 0 !important;
        padding: 0 !important;
    }
}

/* Print page container (visible on screen) */
.print-page {
    padding: 20px;
    max-width: 210mm; /* A4 width */
    margin: 0 auto;
}

.print-toolbar {
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* --- Borrower Reference Sheets --- */

.class-section {
    margin-bottom: 20px;
}

@media print {
    .class-section {
        page-break-before: always;
    }
    .class-section:first-child {
        page-break-before: avoid;
    }
}

.class-header {
    font-size: 1.5em;
    font-weight: bold;
    border-bottom: 2px solid #333;
    padding-bottom: 8px;
    margin-bottom: 12px;
}

.borrower-row {
    display: flex;
    align-items: center;
    border-bottom: 1px solid #ddd;
    padding: 10px 0;
}

.borrower-id {
    width: 80px;
    font-weight: bold;
}

.borrower-barcode {
    width: 200px;
    text-align: center;
}

.borrower-barcode svg {
    height: 50px;
}

.barcode-text {
    font-size: 0.8em;
    margin-top: 2px;
}

.borrower-name {
    flex: 1;
    font-size: 1em;
}

.borrower-status {
    width: 80px;
    font-size: 0.9em;
    color: #666;
}

/* --- Student Library Cards --- */

.card-grid {
    display: grid;
    grid-template-columns: repeat(2, 85mm);
    grid-template-rows: repeat(5, 54mm);
    gap: 5mm;
    justify-content: center;
}

.library-card {
    width: 85mm;
    height: 54mm;
    border: 2px solid #000;
    border-radius: 3mm;
    padding: 3mm;
    box-sizing: border-box;
    page-break-inside: avoid;
    overflow: hidden;
}

.card-header {
    text-align: center;
    font-weight: bold;
    font-size: 10pt;
    border-bottom: 1px solid #ccc;
    padding-bottom: 2mm;
    margin-bottom: 2mm;
}

.card-body {
    display: flex;
    gap: 3mm;
}

.card-photo {
    width: 25mm;
    height: 30mm;
    border: 1px solid #ddd;
    background: #f5f5f5;
    flex-shrink: 0;
}

.card-info {
    flex: 1;
}

.card-name {
    font-weight: bold;
    font-size: 9pt;
}

.card-id,
.card-role {
    font-size: 8pt;
    color: #666;
}

.card-barcode {
    text-align: center;
    margin-top: 2mm;
}

.card-barcode svg {
    height: 40px;
}

.card-barcode .barcode-text {
    font-size: 7pt;
}

/* --- Item Labels (Avery 5160/6479 compatible) --- */

@page {
    margin: 10mm;
}

.label-grid {
    display: grid;
    grid-template-columns: repeat(3, 66mm);
    grid-template-rows: repeat(4, 25mm);
    gap: 2.5mm 0;
    justify-content: center;
}

.item-label {
    width: 66mm;
    height: 25mm;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    page-break-inside: avoid;
    border: 1px dashed #ddd; /* Alignment guide, hidden when printing */
}

@media print {
    .item-label {
        border: none;
    }
}

.label-barcode svg {
    height: 15mm;
}

.label-id {
    font-size: 8pt;
    margin-top: 1mm;
}

.label-library {
    font-size: 6pt;
    color: #666;
    margin-top: 1mm;
}
```

### 3. Modify `src/bcd_web_vue/js/router.js`

**Add imports** - After the existing page imports (after line 15):

```javascript
import PrintBorrowerReference from './pages/PrintBorrowerReference.js';
import PrintStudentCards from './pages/PrintStudentCards.js';
import PrintItemLabels from './pages/PrintItemLabels.js';
```

**Add routes** - Insert before the closing `]` of the routes array (before line 84). Follow the exact same object pattern as existing routes:

```javascript
    {
        path: '/print/borrowers/reference',
        name: 'print-borrower-reference',
        component: PrintBorrowerReference,
        meta: { title: 'Impression - Fiches de reference', layout: 'print' }
    },
    {
        path: '/print/borrowers/cards',
        name: 'print-student-cards',
        component: PrintStudentCards,
        meta: { title: 'Impression - Cartes bibliotheque', layout: 'print' }
    },
    {
        path: '/print/catalog/labels',
        name: 'print-item-labels',
        component: PrintItemLabels,
        meta: { title: 'Impression - Etiquettes articles', layout: 'print' }
    }
```

**IMPORTANT**: The components won't exist yet. The routes will cause import errors until Tasks 2-4 are complete. To avoid blocking, you may create minimal placeholder files:

```javascript
// Minimal placeholder for each: e.g. src/bcd_web_vue/js/pages/PrintBorrowerReference.js
const { defineComponent } = Vue;
export default defineComponent({
    name: 'PrintBorrowerReference',
    template: '<div class="print-page"><p>Loading...</p></div>'
});
```

### 4. Modify `src/bcd_web_vue/js/components/App.js`

The sidebar (`<sidebar-nav />`) is currently rendered unconditionally at line 53. Add a computed property to hide it on print routes.

**In setup()** - After `const route = useRoute();` (line 23), add:

```javascript
const isPrintLayout = Vue.computed(() => route.meta?.layout === 'print');
```

**In the return object** (line 30-34), add `isPrintLayout`:

```javascript
return {
    isLoading,
    appReady,
    route,
    isPrintLayout
};
```

**In the template** - Change line 53 from:

```html
<sidebar-nav />
```

to:

```html
<sidebar-nav v-if="!isPrintLayout" />
```

### 5. Modify `src/bcd_web_vue/locales/en.json`

Add 3 keys inside the `"admin"` object (after `"edit_selected": "Edit Selected"` on line 662 is fine, or at the end of the admin section before the closing `}`):

```json
"print_borrower_reference": "Print Reference Sheets",
"print_student_cards": "Print Library Cards",
"print_item_labels": "Print Item Labels"
```

### 6. Modify `src/bcd_web_vue/locales/fr.json`

Add 3 keys inside the `"admin"` object (same location as en.json):

```json
"print_borrower_reference": "Imprimer fiches de reference",
"print_student_cards": "Imprimer cartes de bibliotheque",
"print_item_labels": "Imprimer etiquettes articles"
```

## Key Technical Details

- **JsBarcode version**: 3.11.6 (CDN, no npm)
- **Route naming**: kebab-case (`print-borrower-reference`) matching existing pattern
- **Layout meta**: `meta: { layout: 'print' }` is a NEW convention - only print routes use it
- **Vue globals**: Use `Vue.computed()` (not destructured import - this is CDN Vue)
- **Static file serving**: Files in `src/bcd_web_vue/` are served as `/static/` by the FastAPI server
- **`useRoute()` is already imported** in App.js at line 7 and used at line 23

## Verification

1. `pytest tests/integration tests/unit` - all pass (no regressions)
2. Start server: `python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000`
3. Open browser console on any page: `typeof JsBarcode` should return `"function"`
4. Navigate to `http://127.0.0.1:8000/#/print/borrowers/reference` - page loads with no sidebar visible
5. Navigate to `http://127.0.0.1:8000/#/checkout` - sidebar is visible (normal pages unaffected)
