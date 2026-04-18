# Autocomplete Feature - Task List

## Feature: Add autocomplete to checkout and return pages

**Status**: In Progress (Task 1/6)

## Tasks

### ✅ Planning Phase
- [x] Explore codebase (checkout/return pages, APIs, testing patterns)
- [x] Design autocomplete implementation
- [x] Get user confirmation on UX decisions
- [x] Create implementation plan

### 🚧 Implementation Phase

#### Task 1: Create AutocompleteInput component [IN PROGRESS]
**File**: `src/bcd_web_vue/js/components/ui/AutocompleteInput.js`

**Requirements**:
- Vue 3 Composition API
- 300ms debounce (clears on Enter)
- 2-character minimum before search
- Keyboard navigation (arrows, Enter, Escape)
- Auto-select first result when Enter pressed
- Barcode scanner detection (rapid input bypass)
- Bootstrap 5 dropdown styling
- ARIA attributes
- AbortController for race conditions
- Loading/error states

**Estimated**: 2-3 hours

---

#### Task 2: Integrate autocomplete into BorrowerScanner [PENDING]
**File**: `src/bcd_web_vue/js/components/circulation/BorrowerScanner.js`

**Changes**:
- Replace input with autocomplete-input component
- Change inputmode from "numeric" to "text"
- Remove pattern="[0-9]*"
- Update placeholder for "ID or name"
- Wire up borrower API fetch function
- Implement result formatting function
- Handle @select and @submit events
- Set minChars=2, autoSelectFirst=true

**Estimated**: 1 hour

---

#### Task 3: Integrate autocomplete into ItemScanner [PENDING]
**File**: `src/bcd_web_vue/js/components/circulation/ItemScanner.js`

**Changes**:
- Replace input with autocomplete-input component
- Wire up catalog search API fetch function
- Implement result formatting function
- Handle @select and @submit events
- Set minChars=2, autoSelectFirst=true
- Keep inputmode="text"

**Estimated**: 1 hour

---

#### Task 4: Add i18n strings [PENDING]
**Files**:
- `src/bcd_web_vue/locales/en.json`
- `src/bcd_web_vue/locales/fr.json`

**Strings to add**:
```json
{
  "autocomplete": {
    "no_results": "No results found",
    "loading": "Searching...",
    "error": "Error loading results",
    "min_chars": "Type at least {count} characters"
  },
  "circulation": {
    "borrower_id_placeholder": "Enter or scan borrower ID or name"
  }
}
```

**Estimated**: 30 minutes

---

#### Task 5: Write E2E tests [PENDING]
**Files**:
- `tests/e2e/test_autocomplete_circulation.py` (new)
- `tests/e2e/page_objects/circulation_page.py` (update)

**Test Coverage**:
- Autocomplete displays results
- Keyboard navigation (arrows, Enter, Escape)
- Mouse/touch selection
- Barcode scanner compatibility (rapid input)
- Empty results state
- Error handling
- Performance (<500ms)
- Both borrower and item autocomplete

**Estimated**: 2-3 hours

---

#### Task 6: Manual testing and verification [PENDING]

**Test Scenarios**:
- Test with physical barcode scanner (verify <200ms)
- Test on mobile devices
- Test keyboard navigation
- Test both English and French
- Verify autocomplete performance (<500ms)
- Test edge cases (empty results, errors, rapid input)
- Verify all success criteria met

**Estimated**: 1 hour

---

## Total Estimated Time
8-10 hours

## Success Criteria
- ✅ Autocomplete displays within 500ms of typing
- ✅ Shows up to 10 results from API
- ✅ Keyboard navigation works (arrows, Enter, Escape)
- ✅ Mouse/touch selection works
- ✅ Barcode scanner workflow unaffected (<200ms target maintained)
- ✅ Works in both English and French
- ✅ All E2E tests pass
- ✅ Works on mobile devices
