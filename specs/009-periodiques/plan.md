# Implementation Plan: Periodicals Management

**Branch**: `009-periodiques` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)

---

## Summary

Add proper periodicals (revues/magazines) support to BCD4. The existing model is broken: 485
records imported from BiblioPuce have `medium_type='Livre'`, `isbn=NULL`, and `total_items=0`.
We implement the target workflow (1 parent record per title + N items per issue) for all new
bulletinage going forward, without touching existing data.

**Technical approach** — zero new API endpoints, zero new Pydantic schemas:
- Resize `isbn` column to `String(22)` / `max_length=22` (direct model edit, no migration; DB dropped)
- Store ALL identifiers with prefix: `isbn:NNNN` for books, `issn:NNNN-NNNX` for periodicals
- Fix `_normalize_isbn()` to return prefixed value for both books and periodicals
- Fix `export_service._format_isbn()` to not double-prefix already-stored values
- Fix `_download_cover()` to strip `isbn:` prefix; skip for `issn:`
- Add `_ean13_to_issn()` in `catalog_service.py` to convert kiosk EAN-13 (`977...`) to ISSN
- Fix `bibliopuce_to_dublin_core.py` to detect periodicals → correct `dc.type` before reimport
- Surface `call_number` in `ItemBarcodeInput.js` conditionally (periodicals only)
- Add `call_number` to circulation API responses so both Vue.js and Godot benefit

---

## Technical Context

**Stack**: Python 3.11 / FastAPI 0.104+ / SQLAlchemy 2.0+ / Alembic (backend);
JavaScript ES2020 / Vue 3.4.21 vendored / vue-i18n (frontend); Godot 4.6 (kids client)  
**Storage**: SQLite dev, PostgreSQL-compatible prod  
**Scale**: ~3,000 items, ~500 bibliographic records, ~15 periodical titles (school scale)  
**No new DB columns, no migration file** — `item.call_number` already exists (String(50), nullable);
`isbn` column resized from String(17) to String(22) directly in the model (DB dropped + reimport).

---

## Phase 0 — Schema Change (prerequisite)

### Step 0: Resize `isbn` column to String(22)

`isbn:9782070612758` = 18 chars; `isbn:978-2-07-061275-8` = 22 chars (hyphens preserved in
some import paths). `String(17)` / `max_length=17` rejects all prefixed values.

**`src/bcd_api/models/bibliographic_record.py`**:
```python
# Before:  isbn = Column(String(17), nullable=True, index=True)
isbn = Column(String(22), nullable=True, index=True)
```

**`src/bcd_api/schemas/bibliographic_record.py`**:
```python
# Before:  isbn: Optional[str] = Field(None, max_length=17, ...)
isbn: Optional[str] = Field(None, max_length=22,
    description="Identifier with prefix: isbn:NNNN for books, issn:NNNN-NNNX for periodicals")
```

No Alembic migration created — DB dropped and recreated from scratch.

---

## Current State Analysis

### What is broken today

| Bug | Location | Root cause |
|-----|----------|-----------|
| ISSN `"1163-7706"` → `None` | `import_service._normalize_isbn()` | Strips hyphen → 8 chars → not 10 or 13 → returns `None` |
| EAN-13 `"9771163770025"` → 404 | `catalog_service.lookup_isbn()` | No 977-prefix detection — treated as invalid ISBN |
| `total_items = 0` after import | `dublin_core_import.py` | Counter incremented per-record at creation but not reconciled after bulk item insertion |
| Author column empty in UI | All views | Periodicals have no authors — no fallback to publisher |
| No call_number shown during loan | CirculationPage, Godot | Checkout/return API responses don't include `item.call_number` |
| CREW report includes old back-issues | `NeverBorrowedReport.js` | No medium_type filter — old issues get high weeding scores incorrectly |

### What already works correctly

| Feature | Status |
|---------|--------|
| `lookup_isbn()` with bare ISSN `"1163-7706"` | ✅ Detects via `SUDOC_ISSN_PATTERN`, queries SUDOC |
| `sudoc_search_by_issn()` | ✅ Returns parsed Pica+ data for French periodicals |
| `item.call_number` DB column | ✅ String(50), nullable, indexed — exists in model and schema |
| `medium_type` filter in catalog search | ✅ Exposed via `AdvancedFilters.js` (datalist input) |
| `ItemCreate` schema | ✅ Has `call_number: Optional[str]` — no schema change needed |
| `POST /catalog/items` endpoint | ✅ Creates item with any call_number — no new endpoint needed |
| Holds / circulation for periodicals | ✅ Works identically to books |
| `medium_type` in search results API | ✅ Included in `PaginatedResponse` items |

### ISBNLookup.js existing flow (important)

```
scan barcode → normalizeISBN() →
  If ISSN found in DB → emit('existing-record-found') → CatalogingPage goes to item creation
  If not found in DB → POST /catalog/lookup-isbn → BNF/SUDOC → emit('lookup-success') → form
```

The "existing record found" path already routes directly to `ItemBarcodeInput`. The only gap:
`ItemBarcodeInput` doesn't know the record's `medium_type`, so it can't show the call_number field.

---

## Phase 1 — Backend Fixes

### Step 1: `import_service._normalize_isbn()` — preserve ISSN

**File**: `src/bcd_api/services/import_service.py`

**Current code** (lines ~108–125):
```python
def _normalize_isbn(isbn: str) -> Optional[str]:
    normalized = isbn.strip()
    if normalized.lower().startswith("isbn:"):
        normalized = normalized[5:]
    normalized = normalized.replace("-", "").replace(" ", "").strip()
    if len(normalized) in [10, 13]:
        return f"isbn:{normalized}"
    return None  # e.g. "11637706" (8 digits, no hyphen) → invalid
```

**Fix**: Insert ISSN detection before stripping hyphens. Add to top of file:
```python
import re
_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dX]$", re.IGNORECASE)
```

Updated function body (insert before the `startswith("isbn:")` check):
```python
def _normalize_isbn(isbn: str) -> Optional[str]:
    if not isbn or isbn.strip() == "":
        return None
    normalized = isbn.strip()

    # Handle issn: prefix explicitly
    if normalized.lower().startswith("issn:"):
        bare = normalized[5:]
        if _ISSN_RE.match(bare):
            return f"issn:{bare.upper()}"
        return None

    # Detect bare ISSN format NNNN-NNNX before stripping hyphens
    if _ISSN_RE.match(normalized):
        return f"issn:{normalized.upper()}"

    # ISBN path: strip isbn: prefix, hyphens, spaces
    if normalized.lower().startswith("isbn:"):
        normalized = normalized[5:]
    normalized = normalized.replace("-", "").replace(" ", "").strip()
    if len(normalized) in [10, 13]:
        return normalized
    return None
```

**Effect**: `"1163-7706"` → `"issn:1163-7706"`. `"978-2-07-061275-8"` → `"isbn:9782070612758"`.
`"9771163770025"` (EAN-13, 977 prefix) → `_normalize_isbn()` returns `"isbn:9771163770025"`
(treated as 13-digit ISBN at this layer; EAN-13 detection happens in `catalog_service.lookup_isbn()`).

---

### Step 2: `catalog_service` — EAN-13 detection + ISSN prefix storage

**File**: `src/bcd_api/services/catalog_service.py`

#### 2a. New private function `_ean13_to_issn()`

Insert after the `_download_cover()` function:

```python
_EAN13_PERIODICAL_RE = re.compile(r"^977(\\d{7})\\d{3}$")


def _ean13_to_issn(ean13: str) -> Optional[str]:
    """Extract and validate ISSN from a kiosk EAN-13 barcode (prefix 977).

    Kiosk EAN-13 structure for periodicals:
      977 + 7 ISSN digits (without check digit) + 2 issue digits + 1 EAN check digit

    ISSN check digit recalculation: modulo 11, with X = 10.

    Example: 9771163770025 → ISSN 1163-770X
    """
    m = _EAN13_PERIODICAL_RE.match(ean13)
    if not m:
        return None
    digits = m.group(1)  # 7 ISSN digits without check digit
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(digits, weights))
    remainder = total % 11
    check = (11 - remainder) % 11
    check_char = "X" if check == 10 else str(check)
    return f"{digits[:4]}-{digits[4:7]}{check_char}"
```

#### 2b. Update `lookup_isbn()` — targeted changes based on actual code

The function currently: strips spaces, checks ISSN pattern (keeps hyphen), strips hyphens for ISBN,
does DB check with bare form, then routes to SUDOC/BNF/etc.

**Insert at top** (after `normalized_isbn = isbn.replace(" ", "").strip()`):

```python
# EAN-13 kiosk barcode for periodicals (977 prefix) → extract bare ISSN
if re.match(r"^\d{13}$", normalized_isbn) and normalized_isbn.startswith("977"):
    extracted = _ean13_to_issn(normalized_isbn)
    if not extracted:
        raise ValidationError(f"Barcode {isbn} does not yield a valid ISSN")
    normalized_isbn = extracted  # bare "NNNN-NNNX", falls through to ISSN check below
```

**Replace the ISSN/ISBN normalization block**:

```python
# Before:
if SUDOC_ISSN_PATTERN.match(normalized_isbn):
    normalized_isbn = normalized_isbn.upper()
else:
    normalized_isbn = normalized_isbn.replace("-", "")

# After:
if SUDOC_ISSN_PATTERN.match(normalized_isbn):
    bare_identifier = normalized_isbn.upper()           # "1163-770X"
    normalized_isbn = f"issn:{bare_identifier}"        # "issn:1163-770X"
else:
    bare_identifier = normalized_isbn.replace("-", "") # "9782070612758"
    normalized_isbn = f"isbn:{bare_identifier}"        # "isbn:9782070612758"
```

`normalized_isbn` is now always prefixed. `bare_identifier` is used for all external API calls.

**DB duplicate check** — already uses `normalized_isbn`, no change needed.

**SUDOC ISSN path**: replace `sudoc_search_by_issn(normalized_isbn)` with
`sudoc_search_by_issn(bare_identifier)`. Replace `data["isbn"] = data.pop("issn")`
with `data["isbn"] = normalized_isbn`.

**ISBN path** (BNF/Google Books/SUDOC): change all `normalized_isbn` passed to API functions
to `bare_identifier`. After any successful find, add `data["isbn"] = normalized_isbn`.

**Cover download and medium_type** — replace the final block:

```python
# Before:
cover_file = _download_cover(normalized_isbn)
if cover_file:
    data["cover_image"] = cover_file

# After:
is_issn = normalized_isbn.startswith("issn:")
if is_issn:
    data.setdefault("medium_type", MediumType.PERIODIQUE.value)
    # No cover for periodicals
else:
    cover_file = _download_cover(normalized_isbn)  # _download_cover strips isbn: prefix
    if cover_file:
        data["cover_image"] = cover_file
```

Note: `MediumType.PERIODIQUE` already defined in `src/shared/constants.py` (verify name).

#### 2c. Fix `_download_cover()` — strip prefix, skip ISSN

```python
def _download_cover(isbn: str) -> Optional[str]:
    # Skip periodicals — Open Library has no covers indexed by ISSN
    if isbn.lower().startswith("issn:"):
        return None
    # Strip isbn: prefix (new storage format)
    bare = isbn[5:] if isbn.lower().startswith("isbn:") else isbn
    normalized = bare.replace("-", "").replace(".", "").replace(" ", "")
    # ... rest unchanged: dest, filepath, url, httpx.get ...
```

Also fix the call in `create_bibliographic_record()` — it calls
`_download_cover(db_data["isbn"])` which will now receive `"isbn:9782070612758"`. The
fix in `_download_cover()` itself covers this.

---

### Step 2a (new): Fix `bibliopuce_to_dublin_core.py` — detect periodicals

**File**: `src/bcd_converters/bibliopuce_to_dublin_core.py`

BiblioPuce exports magazines with `Support = "Livre"`. Add detection by collection title:

```python
# At module level, before map_row():
KNOWN_PERIODICALS = frozenset({
    "j'aime lire", "j'aime lire max", "je bouquine",
    "wakou", "okapi", "astrapi", "phosphore", "youpi",
    "les belles histoires", "popi", "pomme d'api",
    "picoti", "toupie", "dada", "arkéo junior",
    "virgule", "vocable", "geo ado",
})

_ISSN_LIKE = re.compile(r"\d{4}-\d{3}[\dXx]$")

def is_periodical(row: dict) -> bool:
    collection = row.get("Collection", "").strip().lower()
    if collection in KNOWN_PERIODICALS:
        return True
    isbn_field = row.get("ISBN", "").strip()
    return bool(_ISSN_LIKE.match(isbn_field))
```

In `map_row()` (or equivalent), replace the `dc.type` assignment:

```python
# Before:
dc["dc.type"] = row.get("Support", "Livre")

# After:
dc["dc.type"] = "Text;Periodical" if is_periodical(row) else row.get("Support", "Livre")
```

The Dublin Core importer maps `"Text;Periodical"` → `medium_type = "Périodique"`.

---

### Step 2b (new): Fix `export_service._format_isbn()` — prevent double-prefix

**File**: `src/bcd_api/services/export_service.py`

```python
def _format_isbn(self, isbn: str) -> str:
    if not isbn:
        return ""
    # Values already stored with prefix in DB — return as-is
    if isbn.lower().startswith(("isbn:", "issn:")):
        return isbn
    # Legacy bare values (safety net for any values that predate the prefix convention)
    return f"isbn:{isbn}"
```

---

### Step 3: `dublin_core_import.py` — fix `total_items` after bulk import

**File**: `src/bcd_api/services/dublin_core_import.py`

After the item insertion loop completes, add a reconciliation UPDATE.
The loop already tracks which records were touched — use that set.
If no such variable exists, collect `item.bibliographic_record_id` for each created item.

```python
# After item insertion loop, before final commit:
if created_record_ids:
    from sqlalchemy import text
    db.execute(
        text(
            "UPDATE bibliographic_record "
            "SET total_items = ("
            "  SELECT COUNT(*) FROM item "
            "  WHERE item.bibliographic_record_id = bibliographic_record.id"
            ") "
            "WHERE id IN :ids"
        ),
        {"ids": tuple(created_record_ids)},
    )
```

Read the exact variable names used in that file before implementing — the set of touched
record IDs may already exist under a different name.

---

### Step 4: `circulation_service.py` — add `call_number` to three responses

**File**: `src/bcd_api/services/circulation_service.py`

This single change makes both Vue.js and Godot display the issue number without extra API calls.

**`checkout_items()`** — in the `transactions` list comprehension:
```python
# Current:
{
    "transaction_id": t.id,
    "item_id": t.item.item_id,
    "title": t.bibliographic_record.title,
    "due_date": t.due_date,
    "cover_image": t.bibliographic_record.cover_image,
}
# Add:
    "call_number": t.item.call_number,   # None for books, "274" for periodicals (UI adds "n°")
```

**`return_items()`** — in the returned items list, same addition:
```python
    "call_number": item_obj.call_number,  # use actual variable name in that file
```

**`get_borrower_current_loans()`** — in the loan dict:
```python
    "call_number": t.item.call_number,
```

`t.item` is already loaded via the existing ORM relationship — no extra query needed.

---

## Phase 2 — Frontend: Vue.js

### Step 5: i18n keys — `fr.json` and `en.json`

**Files**: `src/bcd_web_vue/locales/fr.json` and `src/bcd_web_vue/locales/en.json`

Add to both files simultaneously:

```json
// fr.json additions:
"periodical": {
  "issue_number": "Numérotation",
  "issue_number_placeholder": "ex : n° 274, Avril 2026",
  "new_issue_success": "Numéro ajouté avec succès"
},
"catalog": {
  "issn": "ISSN",
  "author_publisher": "Auteur / Éditeur"
}

// en.json additions:
"periodical": {
  "issue_number": "Issue number",
  "issue_number_placeholder": "e.g.: Issue 274, April 2026",
  "new_issue_success": "Issue added successfully"
},
"catalog": {
  "issn": "ISSN",
  "author_publisher": "Author / Publisher"
}
```

Note: merge into existing `catalog` object, do not create a duplicate top-level key.

---

### Step 6: `CatalogingPage.js` — pass `medium_type` to `ItemBarcodeInput`

**File**: `src/bcd_web_vue/js/pages/CatalogingPage.js`

`createdRecord` is set in `handleRecordCreated(record)` — it is the full `BiblographicRecordResponse`
which already contains `medium_type`. The component just doesn't forward it.

**Current** (line ~193):
```javascript
<ItemBarcodeInput
    v-if="state === 'item-creation' && createdRecord"
    :record-id="createdRecord.id"
    :record-title="createdRecord.title"
    @item-created="(item) => {}"
    @done="handleItemsDone"
/>
```

**Change** — add one prop:
```javascript
<ItemBarcodeInput
    v-if="state === 'item-creation' && createdRecord"
    :record-id="createdRecord.id"
    :record-title="createdRecord.title"
    :record-medium-type="createdRecord.medium_type"
    @item-created="(item) => {}"
    @done="handleItemsDone"
/>
```

---

### Step 7: `ItemBarcodeInput.js` — call_number field for periodicals

**File**: `src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js`

**Existing props** (from code audit):
```javascript
props: {
    recordId: { type: Number, required: true },
    recordTitle: { type: String, required: true }
}
```

**Changes**:

1. Add prop:
```javascript
recordMediumType: { type: String, default: '' }
```

2. Add state in `setup()`:
```javascript
const callNumber = ref('');
const isPeriodical = computed(() => props.recordMediumType === 'Périodique');
```

3. Modify `createItem()`:
```javascript
const createItem = async () => {
    const barcodeValue = barcode.value.trim();
    if (!barcodeValue) return;

    // Require call_number for periodicals
    if (isPeriodical.value && !callNumber.value.trim()) {
        showError(t('periodical.issue_number') + ' ' + t('common.required'));
        return;
    }

    const itemData = {
        item_id: barcodeValue,
        bibliographic_record_id: props.recordId,
    };
    if (isPeriodical.value) {
        itemData.call_number = callNumber.value.trim();
    }

    const item = await apiClient.post('/catalog/items', itemData);
    createdItems.value.push(item);
    emit('item-created', item);
    callNumber.value = '';   // clear both fields
    barcode.value = '';
    // Refocus: periodical → call_number field; book → barcode field
    if (isPeriodical.value) callNumberInput.value?.focus();
    else barcodeInput.value?.focus();
};
```

4. Add `ref` for call_number input: `const callNumberInput = ref(null)`.

5. Template addition — insert above the existing barcode input row:
```javascript
<div v-if="isPeriodical" class="row g-3 mb-3">
    <div class="col-12">
        <label class="form-label">
            {{ t('periodical.issue_number') }}
            <span class="text-danger">*</span>
        </label>
        <input
            ref="callNumberInput"
            v-model="callNumber"
            type="text"
            class="form-control"
            :placeholder="t('periodical.issue_number_placeholder')"
            :disabled="loading"
            @keypress.enter.prevent="$refs.barcodeInput?.focus()"
        />
    </div>
</div>
```

Enter on call_number field moves focus to barcode — natural scanner workflow.

---

### Step 8: `ISBNLookup.js` — detect EAN-13 kiosk barcode (prefix 977)

**File**: `src/bcd_web_vue/js/components/cataloging/ISBNLookup.js`

**Existing `normalizeISBN()`** already handles ISSN detection and ISBN stripping.

Add at the very start of `normalizeISBN()`, before ISSN check:
```javascript
const normalizeISBN = (value) => {
    const trimmed = value.trim();

    // EAN-13 kiosk barcode for periodicals (prefix 977) — pass through as-is
    // Backend _ean13_to_issn() will extract and validate the ISSN
    if (/^\d{13}$/.test(trimmed) && trimmed.startsWith('977')) {
        return trimmed;
    }

    // ... existing ISSN and ISBN logic unchanged ...
};
```

The rest of the flow is unchanged: `POST /catalog/lookup-isbn?isbn=9771163770025` → backend
extracts ISSN → SUDOC lookup → returns `{title: "Wakou", medium_type: "Périodique", isbn: "issn:1163-770X"}`.

If record already exists (ISSN `issn:1163-770X` in DB): `emit('existing-record-found', record)` →
`CatalogingPage` goes to `state = 'item-creation'` → `ItemBarcodeInput` with `medium_type = "Périodique"`.

---

### Step 9: `RecordDetail.js` — call_number column + ISSN label

**File**: `src/bcd_web_vue/js/components/catalog/RecordDetail.js`

#### 9a. `isPeriodical` computed

In `setup()`, add:
```javascript
const isPeriodical = computed(() =>
    record.value?.medium_type === 'Périodique'
);
```

#### 9b. Items tab — add call_number column

In the items table header (conditionally after `item_id` column):
```javascript
<th>{{ t('catalog.item_id') }}</th>
<th v-if="isPeriodical">{{ t('periodical.issue_number') }}</th>
<th>{{ t('catalog.shelf_location') }}</th>
```

In each table row:
```javascript
<td class="font-monospace">{{ item.item_id }}</td>
<td v-if="isPeriodical" class="text-muted">{{ item.call_number || '—' }}</td>
<td class="text-muted">{{ item.shelf_location || '—' }}</td>
```

`item.call_number` is already returned by `GET /catalog/bibliographic/{id}/items`
via `ItemWithCurrentLoan` schema — no API change needed.

#### 9c. ISBN/ISSN label in details tab

Locate the row that shows `record.isbn` (currently labeled `t('catalog.isbn')`):
```javascript
<tr v-if="record.isbn">
    <th>
        {{ record.isbn.startsWith('issn:') ? t('catalog.issn') : t('catalog.isbn') }}
    </th>
    <td class="font-monospace">
        {{ record.isbn.startsWith('issn:') ? record.isbn.slice(5) : record.isbn }}
    </td>
</tr>
```

---

### Step 10: `CirculationPage.js` — display `title · call_number`

**File**: `src/bcd_web_vue/js/pages/CirculationPage.js`

After checkout, items are pushed into a `scannedItems` reactive array. Locate where `title` is
set from the transaction and apply:

```javascript
// Helper (add once in setup()):
const formatItemTitle = (transaction) => {
    return transaction.call_number
        ? `${transaction.title} · ${transaction.call_number}`
        : (transaction.title || '');
};

// Replace direct title assignment with:
title: formatItemTitle(transaction),
```

Apply the same `formatItemTitle()` helper in the return feedback path.

---

### Step 11: `SearchResults.js` — publisher fallback

**File**: `src/bcd_web_vue/js/components/catalog/SearchResults.js`

Locate `getAuthors(record)`. At the end, before the final `return ''`:
```javascript
const getAuthors = (record) => {
    // ... existing deserialization logic ...
    // All existing paths that return non-empty stay unchanged.
    // Final fallback:
    return record.publisher || '';
};
```

This affects both card view (author `<p>` element) and table view (author column).
The `<p v-if="record.authors">` guard in card view needs updating too:
```javascript
<p v-if="getAuthors(record)" class="card-text text-muted small mb-2">
```
(Change from `v-if="record.authors"` to `v-if="getAuthors(record)"` so publisher shows.)

---

### Step 12: `MostBorrowedReport.js` — publisher fallback + column label

**File**: `src/bcd_web_vue/js/components/reports/MostBorrowedReport.js`

1. Column header: change `t('reports.mostBorrowed.author')` → `t('catalog.author_publisher')`

2. Row value — check exact field name returned by the reports endpoint (likely `item.author`
   singular, not `item.authors`):
```javascript
<td>{{ item.author || item.publisher || '—' }}</td>
```

---

### Step 13: `NeverBorrowedReport.js` — medium_type filter

**File**: `src/bcd_web_vue/js/components/reports/NeverBorrowedReport.js`

Add a filter dropdown in the report toolbar. The report calls the inventory search endpoint
which already supports a `medium_type` query parameter.

```javascript
// In setup():
const mediumTypeFilter = ref('books_only');  // default: exclude periodicals

const mediumTypesForFilter = computed(() => {
    const types = parseCsv(props.settings?.catalog_medium_types || '');
    return [
        { value: '', label: t('common.all') },
        ...types.map(t => ({ value: t, label: t })),
    ];
});

// When building query params for the inventory API call:
if (mediumTypeFilter.value === 'books_only') {
    // Exclude periodicals: pass all medium types except "Périodique"
    // OR: use a dedicated exclude_medium_type param if available
    // Fallback: filter client-side after fetch
    params.exclude_medium_type = 'Périodique';
}
```

Check if the inventory endpoint supports `exclude_medium_type`. If not, apply client-side:
```javascript
const filteredItems = computed(() =>
    mediumTypeFilter.value === 'books_only'
        ? items.value.filter(i => i.medium_type !== 'Périodique')
        : items.value
);
```

Client-side filtering is acceptable at school scale (~3,000 items).

---

## Phase 3 — Godot Kids

### Step 14: `SCheckout.gd` — display `title · call_number`

**File**: `bcd_kids/src/screens/SCheckout.gd`

API response `transactions[0]` now includes `call_number` (from Step 4).

In `_do_checkout()`, after fetching `title`:
```gdscript
var title: String = transactions[0].get("title", "")
var call_number: String = transactions[0].get("call_number", "")
if not call_number.is_empty():
    title = title + " · " + call_number
```

In `_refresh_list()`, same pattern for each loan label:
```gdscript
var title: String = l.get("title", "")
var call_number: String = l.get("call_number", "")
if not call_number.is_empty():
    title = title + " · " + call_number
lbl.text = "✅ %s - %s" % [title, l.get("due_date", "")]
```

---

### Step 15: `SReturnScan.gd` — display `title · call_number`

**File**: `bcd_kids/src/screens/SReturnScan.gd`

API response `items[0]` now includes `call_number` (from Step 4).

In `_do_return()`:
```gdscript
var title: String = item.get("title", "")
var call_number: String = item.get("call_number", "")
if not call_number.is_empty():
    title = title + " · " + call_number
var msg := "✅ %s - %s - %s" % [title, borrower_name, status_text]
```

---

### Step 16: `BookCard.gd` — publisher fallback

**File**: `bcd_kids/src/components/BookCard.gd`

```gdscript
func setup(data: Dictionary, action_label: String, action_color: Color) -> void:
    book_data = data
    # ... existing status/title logic ...

    var authors = data.get("authors", [])
    var authors_text := ", ".join(authors) if authors is Array and not authors.is_empty() else ""
    # NEW: fallback to publisher for periodicals
    if authors_text.is_empty():
        authors_text = data.get("publisher", "")
    _authors_lbl.text = authors_text
    _authors_lbl.visible = not authors_text.is_empty()
```

---

## Phase 4 — Tests

### Step 17: Unit tests — `test_import_service.py`

**File**: `tests/unit/test_import_service.py`

```python
from src.bcd_api.services.import_service import _normalize_isbn


class TestNormalizeIsbn:

    def test_bare_issn_gets_prefix(self):
        assert _normalize_isbn("1163-7706") == "issn:1163-7706"

    def test_bare_issn_uppercase_check_digit(self):
        assert _normalize_isbn("0336-743X") == "issn:0336-743X"

    def test_bare_issn_lowercase_normalized(self):
        assert _normalize_isbn("0336-743x") == "issn:0336-743X"

    def test_prefixed_issn_preserved(self):
        assert _normalize_isbn("issn:1163-7706") == "issn:1163-7706"

    def test_regular_isbn13_returns_with_prefix(self):
        assert _normalize_isbn("978-2-07-061275-8") == "isbn:9782070612758"

    def test_regular_isbn10_returns_with_prefix(self):
        assert _normalize_isbn("2-07-061275-6") == "isbn:2070612756"

    def test_prefixed_isbn_idempotent(self):
        assert _normalize_isbn("isbn:9782070612758") == "isbn:9782070612758"

    def test_8_digit_string_without_hyphen_is_invalid(self):
        # "11637706" is not a valid ISSN (no hyphen) and not ISBN (8 digits)
        assert _normalize_isbn("11637706") is None

    def test_empty_returns_none(self):
        assert _normalize_isbn("") is None
```

---

### Step 18: Integration tests — `test_catalog_service.py`

**File**: `tests/integration/services/test_catalog_service.py`

```python
from src.bcd_api.services.catalog_service import _ean13_to_issn, lookup_isbn, create_item
from src.bcd_api.schemas.item import ItemCreate
from src.bcd_api.schemas.bibliographic_record import BiblographicRecordCreate


class TestEan13ToIssn:

    def test_wakou_ean13_returns_correct_issn(self):
        result = _ean13_to_issn("9771163770025")
        assert result is not None
        assert result.startswith("1163-")

    def test_book_ean13_returns_none(self):
        # 978 prefix = book, not periodical
        assert _ean13_to_issn("9780306406157") is None

    def test_non_digits_returns_none(self):
        assert _ean13_to_issn("NOT_A_BARCODE") is None

    def test_12_digit_returns_none(self):
        assert _ean13_to_issn("977116377002") is None


class TestLookupIssnStorage:

    def test_issn_stored_with_prefix(self, db_session):
        with patch("src.bcd_api.services.catalog_service.sudoc_search_by_issn") as mock:
            mock.return_value = {
                "title": "Wakou",
                "publisher": "Milan Presse",
                "medium_type": "Périodique",
            }
            result = lookup_isbn(db_session, "1163-7706")
        assert result is not None
        assert result["isbn"] == "issn:1163-7706"
        assert result["medium_type"] == "Périodique"


class TestCreateItemWithCallNumber:

    def test_item_created_with_call_number(self, db_session):
        from src.bcd_api.services.catalog_service import create_bibliographic_record
        record = create_bibliographic_record(
            db_session,
            BiblographicRecordCreate(
                title="Wakou",
                medium_type="Périodique",
                isbn="issn:1163-7706",
            ),
            isbn_lookup=False,
        )
        item = create_item(
            db_session,
            ItemCreate(
                item_id="P0274",
                bibliographic_record_id=record.id,
                call_number="274",
            ),
        )
        assert item.call_number == "274"
        db_session.refresh(record)
        assert record.total_items == 1
```

---

## File Change Summary

| File | Type of change | Steps |
|------|---------------|-------|
| `src/bcd_api/services/import_service.py` | Fix: ISSN preservation | 1 |
| `src/bcd_api/services/catalog_service.py` | Add: `_ean13_to_issn()`, update `lookup_isbn()` | 2 |
| `src/bcd_api/services/dublin_core_import.py` | Fix: `total_items` reconciliation | 3 |
| `src/bcd_api/services/circulation_service.py` | Add: `call_number` to 3 responses | 4 |
| `src/bcd_web_vue/locales/fr.json` | Add: 5 i18n keys | 5 |
| `src/bcd_web_vue/locales/en.json` | Add: 5 i18n keys | 5 |
| `src/bcd_web_vue/js/pages/CatalogingPage.js` | Add: 1 prop on `<ItemBarcodeInput>` | 6 |
| `src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js` | Add: call_number field (periodicals only) | 7 |
| `src/bcd_web_vue/js/components/cataloging/ISBNLookup.js` | Add: EAN-13 passthrough | 8 |
| `src/bcd_web_vue/js/components/catalog/RecordDetail.js` | Add: call_number col + ISSN label | 9 |
| `src/bcd_web_vue/js/pages/CirculationPage.js` | Add: `title · call_number` display | 10 |
| `src/bcd_web_vue/js/components/catalog/SearchResults.js` | Fix: publisher fallback | 11 |
| `src/bcd_web_vue/js/components/reports/MostBorrowedReport.js` | Fix: publisher fallback + header | 12 |
| `src/bcd_web_vue/js/components/reports/NeverBorrowedReport.js` | Add: medium_type filter | 13 |
| `bcd_kids/src/screens/SCheckout.gd` | Add: call_number in display | 14 |
| `bcd_kids/src/screens/SReturnScan.gd` | Add: call_number in display | 15 |
| `bcd_kids/src/components/BookCard.gd` | Fix: publisher fallback | 16 |
| `tests/unit/test_import_service.py` | Add: 8 ISSN normalize tests | 17 |
| `tests/integration/services/test_catalog_service.py` | Add: 6 periodical tests | 18 |

**Total**: 19 files, 0 new API endpoints, 0 new DB migrations, 0 new Pydantic schemas.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Data migration (485 broken records) | Destructive one-shot — plan separately after validating new workflow |
| Scan-first from `CirculationPage.js` | Out of scope for this MVP |
| Dashboard "recently received issues" widget | Low value, cosmetic |
| Grouping items by `call_number` in `RecordDetail` | Complexity vs benefit |
| Periodical subscriptions, ordering, budget | No budget concept in BCD4 |
| Issue prediction / routing lists | CDI / high school feature |
| Reliure (binding back issues) | Irrelevant at primary school scale (max ~15 titles) |
