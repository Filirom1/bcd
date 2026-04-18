# Task 5: UI Integration - AdminDropdown + Page Handlers

## Goal

Wire up the 3 print pages to the existing UI so users can access them from the Admin dropdown on the Borrowers and Catalog pages. After this task, users click Admin dropdown, see print options, and clicking opens the print page in a new tab.

## Dependencies

- **Tasks 1, 2, 3, 4** must ALL be complete (infrastructure + all 3 print components)

## Files to Read and Modify

| File | Action | Why |
|------|--------|-----|
| `src/bcd_web_vue/js/components/admin/AdminDropdown.js` | **MODIFY** | Add print menu items |
| `src/bcd_web_vue/js/pages/BorrowersPage.js` | **MODIFY** | Add print handlers, wire events |
| `src/bcd_web_vue/js/pages/CatalogPage.js` | **MODIFY** | Add print handler, wire event |

## Change 1: Modify `AdminDropdown.js`

**Current state** (read the full file first):
- Props: `selectedCount` (Number), `page` (String: 'borrowers' | 'catalog')
- Emits: `['import', 'export', 'bulk-edit', 'edit-selected']`
- Template: dropdown with Import, Export, divider, Edit Selected, Bulk Edit

### 1a. Add new emits

Change line 36 from:
```javascript
emits: ['import', 'export', 'bulk-edit', 'edit-selected'],
```
to:
```javascript
emits: ['import', 'export', 'bulk-edit', 'edit-selected', 'print-reference', 'print-cards', 'print-labels'],
```

### 1b. Add print menu items to template

Insert AFTER the Bulk Edit `</li>` (after line 167, before the closing `</ul>`). Add a divider and context-dependent print items:

```html
                <!-- Print Divider -->
                <li><hr class="dropdown-divider"></li>

                <!-- Print options for Borrowers page -->
                <template v-if="page === 'borrowers'">
                    <li>
                        <a
                            class="dropdown-item"
                            href="#"
                            @click.prevent="$emit('print-reference')"
                        >
                            <i class="bi bi-file-text"></i>
                            {{ t('admin.print_borrower_reference') }}
                        </a>
                    </li>
                    <li>
                        <a
                            class="dropdown-item"
                            href="#"
                            @click.prevent="$emit('print-cards')"
                        >
                            <i class="bi bi-credit-card"></i>
                            {{ t('admin.print_student_cards') }}
                        </a>
                    </li>
                </template>

                <!-- Print options for Catalog page -->
                <template v-if="page === 'catalog'">
                    <li>
                        <a
                            class="dropdown-item"
                            href="#"
                            @click.prevent="$emit('print-labels')"
                        >
                            <i class="bi bi-printer"></i>
                            {{ t('admin.print_item_labels') }}
                        </a>
                    </li>
                </template>
```

## Change 2: Modify `BorrowersPage.js`

### 2a. Add handler functions in `setup()`

Add these two functions inside `setup()`, after the existing `handleExport` function (around line 468):

```javascript
// Handle print reference sheets (from admin dropdown)
const handlePrintReference = () => {
    const params = new URLSearchParams();
    // Pass current class filter to print page if active
    if (filters.value.class_id) {
        params.set('class_ids', filters.value.class_id);
    }
    const query = params.toString();
    window.open(`#/print/borrowers/reference${query ? '?' + query : ''}`, '_blank');
};

// Handle print student cards (from admin dropdown)
const handlePrintCards = () => {
    const params = new URLSearchParams();
    if (filters.value.class_id) {
        params.set('class_ids', filters.value.class_id);
    }
    const query = params.toString();
    window.open(`#/print/borrowers/cards${query ? '?' + query : ''}`, '_blank');
};
```

### 2b. Return new handlers from setup()

Add `handlePrintReference` and `handlePrintCards` to the return object (around line 492-528):

```javascript
return {
    // ... existing returns ...
    handlePrintReference,
    handlePrintCards
};
```

### 2c. Wire events in template

Change the `<admin-dropdown>` tag in the template (lines 61-68) from:

```html
<admin-dropdown
    :selected-count="selectedCount"
    page="borrowers"
    @import="handleImportClick"
    @export="handleExport"
    @bulk-edit="handleBulkEdit"
    @edit-selected="handleEditSelected"
></admin-dropdown>
```

to:

```html
<admin-dropdown
    :selected-count="selectedCount"
    page="borrowers"
    @import="handleImportClick"
    @export="handleExport"
    @bulk-edit="handleBulkEdit"
    @edit-selected="handleEditSelected"
    @print-reference="handlePrintReference"
    @print-cards="handlePrintCards"
></admin-dropdown>
```

## Change 3: Modify `CatalogPage.js`

### 3a. Add handler function in `setup()`

Add this function inside `setup()`, after the existing `handleExportCatalog` function (around line 521):

```javascript
// Handle print item labels (from admin dropdown)
const handlePrintLabels = () => {
    window.open('#/print/catalog/labels', '_blank');
};
```

### 3b. Return new handler from setup()

Add `handlePrintLabels` to the return object (around line 523-571):

```javascript
return {
    // ... existing returns ...
    handlePrintLabels
};
```

### 3c. Wire event in template

Change the `<admin-dropdown>` tag in the template (lines 583-590) from:

```html
<admin-dropdown
    :selected-count="selectedCount"
    page="catalog"
    @import="handleImportClick"
    @export="handleExportCatalog"
    @bulk-edit="handleBulkEdit"
    @edit-selected="handleEditSelected"
></admin-dropdown>
```

to:

```html
<admin-dropdown
    :selected-count="selectedCount"
    page="catalog"
    @import="handleImportClick"
    @export="handleExportCatalog"
    @bulk-edit="handleBulkEdit"
    @edit-selected="handleEditSelected"
    @print-labels="handlePrintLabels"
></admin-dropdown>
```

## Key Technical Details

- **`window.open(url, '_blank')`**: Opens print page in new tab. Uses hash router format `#/print/...`
- **Filter forwarding**: BorrowersPage passes current `class_id` filter as `?class_ids=X` query param to print pages, so printing respects the current filter
- **CatalogPage**: No filter forwarding needed (prints ALL items)
- **AdminDropdown**: Uses `<template v-if="page === '...'">` to show page-specific print options
- **No new imports needed** in BorrowersPage or CatalogPage
- **i18n keys** (added in Task 1): `admin.print_borrower_reference`, `admin.print_student_cards`, `admin.print_item_labels`

## Verification

1. Navigate to `http://127.0.0.1:8000/#/borrowers`
2. Click the red "Admin" dropdown button
3. Verify menu shows:
   - Import Borrowers
   - Export Borrowers
   - --- divider ---
   - Edit Selected
   - Bulk Edit
   - --- divider ---
   - Print Reference Sheets (with file-text icon)
   - Print Library Cards (with credit-card icon)
4. Click "Print Reference Sheets" - new tab opens at `#/print/borrowers/reference`
5. Select a class filter, then click "Print Library Cards" - new tab URL includes `?class_ids=X`
6. Navigate to `http://127.0.0.1:8000/#/catalog`
7. Click Admin dropdown, verify it shows:
   - Import Catalog (Dublin Core)
   - Export Catalog
   - --- divider ---
   - Edit Selected
   - Bulk Edit
   - --- divider ---
   - Print Item Labels (with printer icon)
8. Click "Print Item Labels" - new tab opens at `#/print/catalog/labels`
9. `pytest tests/integration tests/unit` - no regressions
