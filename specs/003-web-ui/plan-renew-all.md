# Implementation Plan: Renew All Feature (Web UI Enhancement)

**Branch**: `003-web-ui` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Enhancement to existing Web UI - add "Renew All" button to circulation and borrower management pages

## Summary

Add "Renew All" functionality to the Web UI to allow librarians to quickly renew all renewable items for a borrower with a single click. This feature will appear in two locations: (1) the borrower info panel on the circulation page, and (2) the borrower detail page. The feature uses the existing API endpoint (`POST /api/v1/circulation/renew`) and adds htmx dual-response support plus UI components. This enhancement aligns with Constitution Principle V (Click Minimization) by reducing the workflow from individual item renewals to a single bulk action.

## Technical Context

**Language/Version**: JavaScript ES6+ (vanilla, no build tools per existing architecture)
**Primary Dependencies**: Bootstrap 5 (already in use), htmx (already in use), Alpine.js (already in use)
**Storage**: N/A (frontend enhancement only, backend endpoint exists)
**Testing**: Manual testing in Chrome/Firefox/Safari/Edge (existing web UI testing approach)
**Target Platform**: Modern web browsers (Chrome, Firefox, Safari, Edge - latest 2 versions)
**Project Type**: Web frontend enhancement (vanilla JavaScript, no frameworks)
**Performance Goals**: API call <500ms, UI update <100ms (existing standards)
**Constraints**: No build tools, vanilla JS only, Bootstrap 5 components, i18n required (en/fr)
**Scale/Scope**: 8 files modified (3 HTML templates, 2 JS files, 2 i18n JSON files, 1 API endpoint), ~200 lines added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality & DRY ✅ PASS
- **Compliant**: Reuses existing dual-response pattern from checkout/return endpoints
- **Compliant**: Reuses existing notification system (`showNotification()`)
- **Compliant**: Reuses existing API client patterns
- **Justification**: No duplication introduced; leverages established patterns from circulation.js and borrowers.js

### II. Library-First Approach ✅ PASS
- **Compliant**: Uses existing htmx for API communication
- **Compliant**: Uses existing Bootstrap 5 for UI components
- **Compliant**: Uses existing Alpine.js for state management
- **No new dependencies**: Enhancement uses only existing libraries

### III. Comprehensive Testing Standards ⚠️ PARTIAL
- **Gap**: Web UI currently uses manual testing only (no automated E2E tests)
- **Mitigation**: Will follow existing manual testing checklist approach
- **Added**: 4 new E2E test scenarios defined in tasks.md (for future implementation)
- **Justification**: Consistent with existing 003-web-ui testing approach

### IV. User Experience Consistency ✅ PASS
- **Compliant**: Follows existing button patterns in borrower info panel and detail page
- **Compliant**: Uses consistent notification toasts for success/failure
- **Compliant**: Maintains existing color scheme and visual indicators
- **Compliant**: Shows success/failure breakdown (consistent with other bulk operations)

### V. Click Minimization ✅ PASS - PRIMARY GOAL
- **Improvement**: Reduces from N clicks (renew each item individually) to 1 click (renew all)
- **Compliant**: Primary action accessible in 1 step from borrower info display
- **Compliant**: Available in both circulation workflow and borrower management
- **Rationale**: This enhancement specifically addresses Principle V

### VI. Performance for Legacy Hardware ✅ PASS
- **Compliant**: Lightweight API call (single HTTP request)
- **Compliant**: Minimal DOM manipulation (update existing loan list)
- **Compliant**: No heavy computations (renewal logic handled by backend)
- **Target**: API response + UI update <600ms on legacy hardware

### VII. Database Schema Versioning ✅ N/A
- **Not Applicable**: Frontend-only enhancement
- **Note**: Backend endpoint and database schema already exist
- **No migrations needed**: Uses existing CirculationTransaction.renewal_count field

### VIII. Research-First Feature Design ✅ PASS
- **Compliant**: Research completed on library system renewal patterns
- **Findings**: Koha and Evergreen support bulk renewal operations
- **Adoption**: Following established patterns from library management systems
- **Reference**: Research documented in conversation (Koha/Evergreen renewal workflows)

### IX. Design-First Implementation ✅ PASS
- **Mockups**: Textual design in spec.md (scenarios 9-10, 13-14) describes full interaction flow
- **Approval**: Spec updated and approved with scenarios defining button behavior
- **Contracts**: API endpoint already exists at `POST /api/v1/circulation/renew`
- **UI Flow**: Button → API call → Display results (success/failure breakdown)

### X. Internationalization (i18n) ✅ PASS
- **Compliant**: All strings externalized to en.json and fr.json
- **Languages**: English (en) and French (fr) translations required
- **Keys**: ~12 new translation keys for renew all feature
- **Validation**: Manual verification required (no automated i18n checks in current CI)

**OVERALL GATE STATUS**: ✅ **PASS** (with documented limitations matching existing project state)

## Project Structure

### Documentation (this feature)

```text
specs/003-web-ui/
├── spec.md                  # Updated with renew all scenarios (9-10, 13-14) and FR-020-RENEW through FR-024-RENEW
├── plan.md                  # Original plan (block/unblock feature)
├── plan-renew-all.md        # This file - focused plan for renew all feature
├── research.md              # Existing research (library system patterns already documented)
├── data-model.md            # Existing (no updates needed - schema unchanged)
├── quickstart.md            # Existing (may update with renew all examples)
├── contracts/               # Existing API contracts (POST /circulation/renew already documented)
└── tasks.md                 # Updated with T027a-T080b (11 new tasks for renew all)
```

### Source Code (repository root)

```text
src/bcd_web/
├── templates/fragments/
│   ├── borrower_info.html               # MODIFY: Add "Renew All" button
│   ├── borrower_detail.html             # MODIFY: Add "Renew All" button
│   └── renew_confirmation.html          # ADD: New template for renewal results
├── js/pages/
│   ├── circulation.js                   # MODIFY: Add renewAll() function
│   └── borrowers.js                     # MODIFY: Add renewAllItems() function
└── locales/
    ├── en.json                          # ADD: ~12 new translation keys for renew all
    └── fr.json                          # ADD: ~12 new French translations

Backend (modification needed):
src/bcd_api/api/v1/circulation.py        # MODIFY: Add htmx dual-response support to POST /renew endpoint

Tests (new):
tests/e2e/
├── test_circulation.py                  # ADD: 2 new renew all tests (T041a, T041b)
└── test_borrowers.py                    # ADD: 2 new renew all tests (T080a, T080b)
```

**Structure Decision**: This is an enhancement to the existing Web UI (003-web-ui). The structure follows the established vanilla JS pattern with no build tools. Both frontend and minimal backend modifications (htmx support only).

## Complexity Tracking

> **No violations to justify** - This enhancement complies with all constitution principles and improves Click Minimization compliance.

## Phase 0: Research

Since this is an enhancement to an existing feature with a well-established API endpoint, research needs are minimal:

### Research Status: ✅ COMPLETE (Leveraging Prior Work + New Research)

**Existing Research Artifacts**:
- `ui-research.md` - Comprehensive UX research including industry best practices
- `research.md` - Technology choices and patterns documented
- Earlier in conversation: Koha and Evergreen renewal workflow research

**Additional Research Completed** (during spec update):
- Library management system renewal patterns (Koha, Evergreen)
- Bulk operation UX patterns in admin interfaces
- Success/failure feedback for batch operations
- Auto-blocking behavior in circulation systems (decided NOT to implement)

**Key Findings Applied**:
1. **Bulk Renewal Pattern**: Industry standard for efficiency in library circulation
2. **Success/Failure Breakdown**: Show which items renewed and which failed with reasons
3. **Dual Location**: Available in both circulation workflow and borrower management
4. **No Auto-Unblocking**: Keep it simple - renewal only extends due dates, no privilege changes
5. **Graceful Degradation**: Renew what's renewable, report what failed

**No Additional Research Required**: Patterns already established, API endpoint exists, UI patterns consistent with existing implementation.

## Phase 1: Design & Contracts

### 1.1 Data Model

**No new data models** - Uses existing entities:

- **CirculationTransaction** (existing): Already has `renewal_count` field
- **SystemSettings** (existing): Already has `renewal_limit` configuration
- **Borrower** (existing): No changes needed

**Key relationships** (already exist):
- CirculationTransaction → Borrower (many-to-one)
- CirculationTransaction → Item (many-to-one)
- CirculationTransaction → BiblographicRecord (many-to-one)

### 1.2 API Contracts

**Existing Endpoint** (no changes to contract, only add htmx support):

```
POST /api/v1/circulation/renew
```

**Request** (already defined):
```json
{
  "borrower_id": "string",
  "item_ids": ["string"] | null  // null or empty = renew all eligible items
}
```

**Response** (already defined):
```json
{
  "borrower_id": "string",
  "renewed_count": integer,
  "failed_count": integer,
  "renewed": [
    {
      "item_id": "string",
      "title": "string",
      "old_due_date": "date",
      "new_due_date": "date",
      "renewals_used": integer,
      "renewals_remaining": integer
    }
  ],
  "failed": [
    {
      "item_id": "string",
      "reason": "string"  // e.g., "Renewal limit reached (2)"
    }
  ]
}
```

**Enhancement Needed**: Add htmx dual-response support

When `HX-Request` header is present, return HTML fragment instead of JSON:

```html
<!-- src/bcd_web/templates/fragments/renew_confirmation.html -->
<div class="alert alert-success">
  <h5>✓ Renewed {{ renewed_count }} item(s)</h5>
  <ul>
    {% for item in renewed %}
    <li>{{ item.title }} - New due date: {{ item.new_due_date }}</li>
    {% endfor %}
  </ul>
  {% if failed_count > 0 %}
  <h6 class="text-warning">Failed to renew {{ failed_count }} item(s):</h6>
  <ul>
    {% for item in failed %}
    <li>{{ item.item_id }} - {{ item.reason }}</li>
    {% endfor %}
  </ul>
  {% endif %}
</div>
```

### 1.3 UI Contracts

**Location 1: Circulation Page - Borrower Info Panel**

```html
<!-- Added to src/bcd_web/templates/fragments/borrower_info.html -->
<div class="borrower-actions">
  {% if current_loans_count > 0 %}
  <button
    class="btn btn-sm btn-primary"
    onclick="renewAll('{{ borrower_id }}')"
    data-i18n="circulation.renew_all">
    Renew All
  </button>
  {% endif %}
</div>
```

**Location 2: Borrower Detail Page**

```html
<!-- Added to src/bcd_web/templates/fragments/borrower_detail.html -->
<div class="modal-footer">
  {% if current_loans_count > 0 %}
  <button
    class="btn btn-primary"
    onclick="renewAllItems('{{ borrower_id }}')"
    data-i18n="borrowers.renew_all">
    Renew All Items
  </button>
  {% endif %}
  <!-- existing buttons: Close, Edit, Block/Unblock -->
</div>
```

### 1.4 JavaScript API

**circulation.js** (new function):
```javascript
async function renewAll(borrowerId) {
  try {
    showNotification('info', i18n.t('circulation.renewing'));

    const response = await fetch(`/api/v1/circulation/renew`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'HX-Request': 'true'
      },
      body: JSON.stringify({
        borrower_id: borrowerId,
        item_ids: null  // null = renew all
      })
    });

    if (response.ok) {
      const html = await response.text();
      document.getElementById('renewal-results').innerHTML = html;
      // Refresh borrower info to show updated due dates
      await loadBorrowerInfo(borrowerId);
    } else {
      showNotification('error', i18n.t('circulation.renewal_failed'));
    }
  } catch (error) {
    showNotification('error', i18n.t('common.network_error'));
  }
}
```

**borrowers.js** (new function):
```javascript
async function renewAllItems(borrowerId) {
  // Similar to renewAll() but updates borrower detail modal
  // Implementation matches circulation.js pattern
}
```

### 1.5 Translations

**New keys needed** (~12 keys):

```json
// en.json
{
  "circulation": {
    "renew_all": "Renew All",
    "renewing": "Renewing items...",
    "renewed_successfully": "Renewed {count} item(s) successfully",
    "renewal_failed": "Failed to renew items",
    "renewal_limit_reached": "Renewal limit reached",
    "items_renewed": "Items renewed",
    "items_not_renewed": "Items not renewed"
  },
  "borrowers": {
    "renew_all": "Renew All Items",
    "renew_all_confirm": "Renew all items for this borrower?",
    "renewal_summary": "Renewal Summary"
  }
}

// fr.json (French translations)
{
  "circulation": {
    "renew_all": "Tout renouveler",
    "renewing": "Renouvellement en cours...",
    "renewed_successfully": "{count} document(s) renouvelé(s)",
    "renewal_failed": "Échec du renouvellement",
    "renewal_limit_reached": "Limite de renouvellement atteinte",
    "items_renewed": "Documents renouvelés",
    "items_not_renewed": "Documents non renouvelés"
  },
  "borrowers": {
    "renew_all": "Tout renouveler",
    "renew_all_confirm": "Renouveler tous les documents de cet emprunteur ?",
    "renewal_summary": "Résumé du renouvellement"
  }
}
```

### 1.6 Testing Contracts

**Manual Test Scenarios** (immediate):
1. Circulation page: Load borrower → Click "Renew All" → Verify success
2. Circulation page: Borrower with items at limit → Verify partial renewal
3. Borrower detail page: Click "Renew All Items" → Verify success
4. Verify French translations display correctly

**E2E Test Scenarios** (tasks.md, future):
- T041a: Renew all from circulation page
- T041b: Partial renewal with items at limit
- T080a: Renew all from borrower detail page
- T080b: Verify success/failure breakdown display

### 1.7 Quickstart Examples

Add to `quickstart.md`:

```markdown
## Renew All Items Workflow

### From Circulation Page

1. Start web server: `python -m src.bcd_web.server`
2. Navigate to http://127.0.0.1:8888/#circulation
3. Enter borrower ID: `101`
4. Click "Renew All" button
5. Verify renewal summary shows:
   - Items renewed with new due dates
   - Items that failed with reasons (if any)

### From Borrower Management

1. Navigate to http://127.0.0.1:8888/#borrowers/101
2. View current loans list
3. Click "Renew All Items" button
4. Verify borrower detail refreshes with updated due dates

### Expected Behavior

- All renewable items: Due dates extended by loan_duration_days (default: 14)
- Items at renewal limit: Listed in "Failed" section with reason
- Blocked borrowers: Cannot renew (API returns error)
- Empty loans: Button not displayed
```

## Phase 2: Implementation Strategy

### 2.1 Task Execution Order

**Sequential Dependencies**:
1. T027a: Add htmx support to API endpoint (backend first)
2. T027b: Create renew_confirmation.html template
3. T034a: Add button to borrower_info.html
4. T034b: Implement renewAll() function in circulation.js
5. T034c: Add result display logic
6. T036a-b: Add translations
7. T073a-c: Repeat for borrower detail page
8. T041a-b, T080a-b: E2E tests (optional, manual testing sufficient)

**Parallel Opportunities**:
- T027a and T027b can be done in parallel (different files)
- T036a and T036b can be done in parallel (different files)
- T034a, T034b, T034c are sequential (same feature area)
- T073a, T073b, T073c are sequential (same feature area)

### 2.2 Rollout Plan

1. **Phase 1**: Implement circulation page (T027a-T036b)
   - ~4 tasks, all related to circulation workflow
   - Enables testing of core renewal logic

2. **Phase 2**: Implement borrower detail page (T073a-T073c)
   - ~3 tasks, reuses patterns from Phase 1
   - Completes dual-location requirement

3. **Phase 3**: E2E tests (optional, T041a-b, T080a-b)
   - ~4 tasks, manual testing may be sufficient
   - Can be deferred for later implementation

### 2.3 Testing Strategy

**Manual Testing** (immediate):
- Load borrower with 3 items, all renewable → Verify all 3 renewed
- Load borrower with items at renewal limit → Verify partial renewal + error messages
- Test in both locations (circulation page, borrower detail)
- Test with different borrower states (active, blocked)
- Verify French translations

**Automated Testing** (future):
- E2E tests using Playwright (defined in tasks.md)
- Can be implemented when E2E test infrastructure is set up
- Not blocking for feature deployment

## Phase 3: Deployment Checklist

- [ ] API endpoint returns HTML for htmx requests
- [ ] "Renew All" button appears in borrower info panel (circulation page)
- [ ] "Renew All" button appears in borrower detail modal
- [ ] Renewal summary shows success/failure breakdown
- [ ] Items at renewal limit show correct error message
- [ ] Translations work in both French and English
- [ ] Manual testing completed on all browsers (Chrome, Firefox, Safari, Edge)
- [ ] No console errors in browser DevTools
- [ ] Performance acceptable (<600ms for API + UI update)

## Known Limitations

1. **No E2E Tests**: Web UI currently uses manual testing only
   - Mitigation: Manual test checklist defined
   - Future: E2E tests defined in tasks.md for later implementation

2. **No Auto-Unblocking**: Renewal does not change borrower blocked status
   - Rationale: Simpler, more predictable behavior
   - Librarian must explicitly unblock if needed

3. **No Confirmation Dialog**: Renew All executes immediately
   - Rationale: Non-destructive operation, consistent with checkout/return
   - Can be added later if user feedback indicates need

## Success Metrics

- [ ] Librarians can renew all items in 1 click (vs. N clicks for N items)
- [ ] Success/failure breakdown clearly displayed
- [ ] No increase in support tickets related to renewals
- [ ] Performance meets existing standards (<600ms)
- [ ] Feature works identically in both locations (circulation, borrower detail)

## Completion Criteria

✅ All 11 tasks (T027a-T080b) completed
✅ Manual testing passed in all 4 browsers
✅ French and English translations verified
✅ No console errors or warnings
✅ Performance within acceptable limits
✅ Documentation updated (quickstart.md)

---

**Next Command**: `/speckit.tasks` to generate detailed implementation tasks (already completed - see tasks.md)
**Next Command**: `/speckit.implement` to execute tasks automatically
