# Autocomplete for Checkout and Return Pages

## Context

The BCD library system currently uses simple text input fields for:
- **Borrower identification** (checkout only): Users manually enter borrower ID
- **Item scanning** (checkout and return): Users manually enter item barcode

These inputs are optimized for physical barcode scanners (targeting <200ms feedback) but provide no assistance for manual entry. When librarians type manually, they must know the exact ID/barcode or look it up separately.

This plan adds **autocomplete functionality** to assist with manual entry while preserving the fast barcode scanner workflow.

## Requirements

**What**: Add autocomplete for:
- **Borrowers**: Search by barcode ID and name
- **Items**: Search by barcode ID, ISBN, title, author, publisher, subtitle

**Where**:
- Checkout page: BorrowerScanner and ItemScanner components
- Return page: ItemScanner component

**How**:
- 300ms debounce (matches existing SearchBar pattern)
- If Enter pressed: immediate search/submit (bypass autocomplete)
- Show up to 10 results in dropdown
- Standard autocomplete UX (keyboard navigation, click to select)

**Verify**: Automated E2E tests with Playwright

## Implementation Approach

### 1. Create Reusable AutocompleteInput Component

**File**: `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/ui/AutocompleteInput.js`

**Why reusable component?**
- DRY principle: Used by BorrowerScanner and ItemScanner
- Separation of concerns: Autocomplete logic isolated
- Testable in isolation
- Matches existing Vue 3 Composition API patterns

**Component Interface**:
```javascript
Props:
  - modelValue: String (v-model binding)
  - placeholder: String
  - fetchResults: Function (async, returns array of results)
  - formatResult: Function (renders each result as HTML string)
  - debounceMs: Number (default 300)
  - minChars: Number (default 2, user confirmed)
  - disabled: Boolean
  - inputmode: String (e.g., "numeric", "text")
  - otherInputAttrs: Object (pattern, autocomplete, etc.)
  - autoSelectFirst: Boolean (default true, user confirmed - auto-select first result when Enter pressed)

Emits:
  - update:modelValue (v-model)
  - select (item selected from dropdown)
  - submit (Enter pressed or button clicked)
```

**Features**:
- 300ms debounce timer (clears on Enter keydown)
- Keyboard navigation (ArrowDown, ArrowUp, Enter, Escape)
- **Minimum 2 characters** before search triggers (user confirmed)
- **Auto-select first result** when Enter pressed without highlighted item (user confirmed)
- Barcode scanner detection: Rapid input (< 100ms between keystrokes) + immediate Enter = bypass autocomplete
- Loading state and error handling
- Bootstrap 5 dropdown styling
- ARIA attributes for accessibility
- AbortController for canceling previous requests

**Scanner Compatibility**:
- Detect rapid input patterns (characters entered < 100ms apart)
- If Enter pressed within 200ms of last keystroke: Submit immediately, skip autocomplete
- Preserves <200ms scanner feedback target

### 2. Leverage Existing Search APIs

**No new API endpoints needed**. Use existing pagination-ready endpoints:

**For Borrowers** (`/api/v1/borrowers`):
```javascript
async function fetchBorrowers(query) {
  const response = await apiClient.get('/api/v1/borrowers', {
    q: query,
    limit: 10
  });
  return response.items; // Array of borrower objects
}
```
- Searches: `borrower_id`, `first_name`, `last_name`, `full_name` (case-insensitive)
- Returns: Enriched borrower data with current_loans_count, class info, etc.

**For Items** (`/api/v1/catalog/bibliographic/search`):
```javascript
async function fetchItems(query) {
  const response = await apiClient.get('/api/v1/catalog/bibliographic/search', {
    q: query,
    limit: 10
  });
  return response.items; // Array of bibliographic records
}
```
- Searches: `title`, `authors`, `isbn`, `item_id`, `catalog_id` (case-insensitive)
- Returns: Bibliographic records with availability info

### 3. Autocomplete Result Display Format

**Borrower Results** (for BorrowerScanner):
```html
<div class="autocomplete-item">
  <div class="fw-bold">{borrower_id} - {first_name} {last_name}</div>
  <small class="text-muted">{class_name} • {current_loans_count}/{loan_limit} loans</small>
  <span v-if="blocked" class="badge bg-danger ms-2">Blocked</span>
  <span v-if="has_overdue" class="badge bg-warning ms-2">Overdue</span>
</div>
```

**Item Results** (for ItemScanner):
```html
<div class="autocomplete-item">
  <div class="fw-bold">{item_id} - {title}</div>
  <small class="text-muted">{author} • {medium_type}</small>
  <span class="badge bg-success ms-2" v-if="available">Available</span>
  <span class="badge bg-secondary ms-2" v-else>On loan</span>
</div>
```

This format:
- Shows searchable IDs prominently (critical for barcode workflow)
- Provides visual context to confirm selection
- Uses Bootstrap badges for status indicators
- Compact enough for 10 results

### 4. Integrate into Existing Components

**BorrowerScanner.js** (`src/bcd_web_vue/js/components/circulation/BorrowerScanner.js`):
- Replace `<input>` with `<autocomplete-input>`
- **Change inputmode from "numeric" to "text"** (user confirmed - supports both ID and name search)
- Remove `pattern="[0-9]*"` (no longer numeric-only)
- Update placeholder to indicate both ID and name search supported
- Provide `fetchResults` function that calls borrower API
- Provide `formatResult` function for borrower display
- Handle `@select` event: emit `borrower-loaded` with selected borrower_id
- Handle `@submit` event: emit `borrower-loaded` with raw input (fallback)
- Set `minChars="2"` (user confirmed)
- Set `autoSelectFirst="true"` (user confirmed - pressing Enter selects first result)

**ItemScanner.js** (`src/bcd_web_vue/js/components/circulation/ItemScanner.js`):
- Replace `<input>` with `<autocomplete-input>`
- Keep `inputmode="text"` (already accepts text barcodes)
- Provide `fetchResults` function that calls catalog search API
- Provide `formatResult` function for item display
- Handle `@select` event: emit `item-scanned` with selected item_id
- Handle `@submit` event: emit `item-scanned` with raw input (fallback)
- Set `minChars="2"` (user confirmed)
- Set `autoSelectFirst="true"` (user confirmed - pressing Enter selects first result)

### 5. Add i18n Strings

**Files**: `src/bcd_web_vue/locales/en.json` and `locales/fr.json`

```json
{
  "autocomplete": {
    "no_results": "No results found",
    "loading": "Searching...",
    "error": "Error loading results",
    "min_chars": "Type at least {count} characters",
    "press_enter": "Press Enter to search"
  }
}
```

### 6. Testing Strategy

**E2E Tests with Playwright** (`tests/e2e/test_autocomplete_circulation.py`):

Following existing Page Object Model pattern:

```python
# Test autocomplete displays results
def test_borrower_autocomplete_displays_results(circulation_page, borrower_factory):
    """Typing shows autocomplete dropdown with matching borrowers"""
    # Arrange: Create test borrowers
    borrower = borrower_factory.create(
        borrower_id="101",
        first_name="Amira",
        last_name="BENALI"
    )

    # Act: Type partial name
    circulation_page.goto_checkout()
    circulation_page.type_borrower_search("Ami")
    circulation_page.wait_for_autocomplete_dropdown()

    # Assert: Results shown with correct data
    results = circulation_page.get_autocomplete_results()
    assert len(results) >= 1
    assert "Amira BENALI" in results[0].text

# Test keyboard navigation
def test_autocomplete_keyboard_navigation(circulation_page, borrower_factory):
    """Arrow keys navigate, Enter selects"""
    # Arrange: Create multiple borrowers
    # Act: Type, press ArrowDown twice, press Enter
    # Assert: Second result selected

# Test barcode scanner compatibility
def test_barcode_scanner_bypasses_autocomplete(circulation_page, item_factory):
    """Rapid typing + immediate Enter submits without autocomplete"""
    # Arrange: Create item
    # Act: Type barcode quickly (simulate scanner) + immediate Enter
    # Assert: Item scanned successfully, autocomplete not shown

# Test autocomplete selection
def test_click_autocomplete_result(circulation_page, borrower_factory):
    """Clicking result selects it"""
    # Arrange: Create borrower
    # Act: Type, click first result
    # Assert: Borrower loaded

# Test performance
def test_autocomplete_performance(circulation_page, performance_monitor):
    """Autocomplete appears within 500ms"""
    # Measure time from typing to dropdown visible
    # Assert: < 500ms (300ms debounce + 200ms API)
```

**Page Object Methods** (add to `tests/e2e/page_objects/circulation_page.py`):
```python
def type_borrower_search(self, text: str):
    """Type into borrower input without submitting"""
    self.page.fill(self.BORROWER_INPUT, text)

def wait_for_autocomplete_dropdown(self, timeout: int = 1000):
    """Wait for autocomplete dropdown to appear"""
    self.page.wait_for_selector('.autocomplete-dropdown', timeout=timeout)

def get_autocomplete_results(self) -> list:
    """Get autocomplete result elements"""
    return self.page.locator('.autocomplete-item').all()

def click_autocomplete_result(self, index: int = 0):
    """Click autocomplete result by index"""
    self.page.locator('.autocomplete-item').nth(index).click()
```

**Test Coverage**:
- Autocomplete displays with correct results
- Keyboard navigation (arrows, Enter, Escape)
- Mouse/touch selection
- Barcode scanner compatibility (rapid input + Enter)
- Empty results state
- Error handling
- Performance (<500ms display time)
- Both borrower and item autocomplete

## Implementation Steps

1. **Create AutocompleteInput component** (~2-3 hours)
   - Vue 3 Composition API with debounce, keyboard nav, scanner detection
   - Bootstrap 5 dropdown styling
   - ARIA attributes

2. **Integrate into BorrowerScanner** (~1 hour)
   - Replace input with autocomplete-input
   - Wire up borrower API and formatting
   - Handle select/submit events

3. **Integrate into ItemScanner** (~1 hour)
   - Replace input with autocomplete-input
   - Wire up catalog API and formatting
   - Handle select/submit events

4. **Add i18n strings** (~30 minutes)
   - Update en.json and fr.json
   - Test both languages

5. **Write E2E tests** (~2-3 hours)
   - Create test file with ~8-10 test cases
   - Add page object methods
   - Verify all scenarios pass

6. **Manual testing** (~1 hour)
   - Test with physical barcode scanner
   - Test on mobile devices
   - Test keyboard navigation
   - Verify performance

**Total Estimated Time**: 8-10 hours

## Critical Files

**New Files**:
- `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/ui/AutocompleteInput.js` - Core autocomplete component

**Modified Files**:
- `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/circulation/BorrowerScanner.js` - Borrower autocomplete integration
- `/home/nixos/src/local/bcd4/src/bcd_web_vue/js/components/circulation/ItemScanner.js` - Item autocomplete integration
- `/home/nixos/src/local/bcd4/src/bcd_web_vue/locales/en.json` - English i18n strings
- `/home/nixos/src/local/bcd4/src/bcd_web_vue/locales/fr.json` - French i18n strings
- `/home/nixos/src/local/bcd4/tests/e2e/page_objects/circulation_page.py` - Page object methods
- `/home/nixos/src/local/bcd4/tests/e2e/test_autocomplete_circulation.py` - E2E tests (new)

## Edge Cases Handled

1. **Race Conditions**: Use AbortController to cancel previous API requests
2. **Empty Results**: Show "No results found" message, allow raw input submission
3. **API Errors**: Show error message, allow raw input submission
4. **Minimum Query Length**: Require 2 characters before searching (user confirmed)
5. **Dropdown Positioning**: Use Bootstrap dropdown classes for smart positioning
6. **Focus Management**: Maintain focus in input after selection (continuous scanning)
7. **Duplicate Prevention**: Parent components handle duplicate checking
8. **Scanner Detection**: Detect rapid input patterns, bypass autocomplete

## Architecture Alignment

Follows BCD project patterns:
- **Vue 3 Composition API**: Matches SearchBar.js, BorrowerFilters.js
- **Service Layer Pattern**: API calls via apiClient (no business logic in component)
- **Reusable Components**: Component structure matches `/components/ui/` pattern
- **i18n**: All user-facing text externalized (en/fr required)
- **Testing**: E2E with Playwright, Page Object Model, AAA pattern
- **Bootstrap 5**: Dropdown classes, badges, utilities
- **Performance**: Maintains <200ms scanner target, adds <500ms autocomplete

## Verification

**Manual Testing**:
1. Start app: `python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000`
2. Navigate to checkout page: `http://127.0.0.1:8000/#/checkout`
3. Type partial borrower name: Verify autocomplete appears within 500ms
4. Use arrow keys to navigate: Verify highlighting works
5. Press Enter: Verify selection works
6. Test with barcode scanner: Verify scanner workflow unaffected (<200ms)
7. Navigate to return page: Test item autocomplete
8. Switch to French (fr-FR): Verify i18n strings

**Automated Testing**:
```bash
# Run E2E tests
pytest tests/e2e/test_autocomplete_circulation.py -v

# Run all circulation tests
pytest tests/e2e/test_us1_circulation.py -v

# Verify performance
pytest tests/e2e/test_autocomplete_circulation.py::test_autocomplete_performance -v
```

**Success Criteria**:
- ✅ Autocomplete displays within 500ms of typing
- ✅ Shows up to 10 results from API
- ✅ Keyboard navigation works (arrows, Enter, Escape)
- ✅ Mouse/touch selection works
- ✅ Barcode scanner workflow unaffected (<200ms target maintained)
- ✅ Works in both English and French
- ✅ All E2E tests pass
- ✅ Works on mobile devices
