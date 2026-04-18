# Implementation Plan: Vue 3 Migration for BCD Web UI

**Branch**: `004-vue-migration` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md) | **Constitution**: v1.1.0
**Input**: Migrate BCD web UI from hybrid HTMX/Alpine.js/vanilla JS to Vue 3 (CDN-based, no build tools)

## Summary

Migrate the BCD web UI from hybrid HTMX/Alpine.js/vanilla JS architecture to **Vue 3 (CDN-based, no build tools)** to achieve:
- Single framework architecture (eliminates 3-paradigm confusion between HTMX declarative, Alpine reactive, vanilla imperative)
- Component-based development (reusable, testable, maintainable components replacing 19 template fragments)
- Proper state management (reactive Vue state replacing manual DOM manipulation)
- 52% code reduction (4,793 LOC → 2,300 LOC target)
- Preserved scanner workflow UX (<200ms feedback maintained)
- Full constitution compliance (all 10 principles validated)

**Current Architecture**: 4,793 LOC across HTMX + Alpine.js + Vanilla JS with 19 HTML template fragments
**Target Architecture**: 2,300 LOC Vue 3 (CDN) with 40+ reusable components + TypeScript JSDoc annotations
**Migration Timeline**: 8 phases over 68 hours (8.5 weeks part-time, 2 weeks full-time)
**Migration Strategy**: Parallel implementation in `src/bcd_web_vue/` with feature flag for rollback

---

## Constitution Check

### I. Code Quality & DRY ✅ PASS
- **Compliant**: Vue Single File Components (SFC-as-JS) eliminate duplication across 19 templates
- **Compliant**: Composables for shared logic (usePagination, useSearch, useApi, useNotification, useFilters)
- **Compliant**: Reusable component library (BorrowerCard, ItemScanner, Pagination, Modal, etc.)
- **Improvement**: Current hybrid has duplicate fetch patterns across 10 files → Centralized in single API client

### II. Library-First Approach ✅ PASS
- **Compliant**: Vue 3.4.21 (established framework, 33KB gzipped, actively maintained, 2M+ weekly npm downloads)
- **Compliant**: Vue Router 4.2.5 (official routing library, 10KB gzipped, proven in production)
- **Compliant**: Vue I18n 9.9.1 (official i18n library, 12KB gzipped, supports 100+ languages)
- **Justification**: Each library reduces custom code by >30%, improves maintainability, cross-platform compatible
- **No Build Tools**: All libraries loaded from CDN (unpkg.com) as global UMD modules - no npm, no webpack, no babel

### III. Comprehensive Testing Standards ⚠️ PARTIAL (Existing Gap)
- **Current State**: Web UI has no automated tests (manual testing checklist only)
- **Migration Plan**:
  - Phase 0-1: Manual testing checklist (maintain current testing approach for initial phases)
  - Phase 2-8: Add Vitest unit tests for new Vue components (NEW - improve testing coverage)
  - Post-migration: Add Playwright E2E tests (FUTURE - full automation)
- **Coverage Target**: 80% minimum for new Vue components (composables, pages, UI components)
- **Test Structure**:
  ```
  tests/web-ui/
  ├── unit/
  │   ├── components/ItemScanner.spec.js
  │   ├── components/BorrowerCard.spec.js
  │   ├── components/Pagination.spec.js
  │   └── composables/usePagination.spec.js
  └── e2e/  # Future
      ├── circulation.spec.js
      ├── catalog.spec.js
      └── borrowers.spec.js
  ```

### IV. User Experience Consistency ✅ PASS
- **Compliant**: Single design system (Bootstrap 5 preserved from current implementation)
- **Compliant**: Consistent component patterns (all modals same structure, all forms same validation, all tables same pagination)
- **Compliant**: Vue Router preserves Single-Page Application (SPA) navigation (no page reloads, instant transitions <100ms)
- **Improved**: Centralized notification system (useNotification composable replaces scattered showNotification calls)
- **Improved**: Consistent loading states via useAppState composable (global loading indicator)

### V. Click Minimization ✅ PASS
- **Maintained**: All existing workflows remain ≤2 steps (checkout: scan borrower → scan items; search: enter query → view results)
- **Improved**: Declarative routing reduces navigation complexity (router-link vs manual hash manipulation)
- **Improved**: Auto-focus managed by Vue lifecycle hooks (onMounted, nextTick) - no setTimeout hacks
- **Example**: Checkout workflow remains 2 steps: (1) scan borrower ID → (2) scan item barcodes with immediate feedback

### VI. Performance for Legacy Hardware ✅ PASS
- **Bundle Size**: Vue 3 (33KB) + Router (10KB) + I18n (12KB) = 55KB total (vs current 50KB HTMX+Alpine) - only 5KB increase
- **Startup Time**: Target <3 seconds on legacy hardware (CDN cached, no transpilation, production build)
- **Runtime**: Vue 3 reactivity system optimized for 60fps updates even on low-end hardware
- **Memory**: Reactive system more memory-efficient than current manual DOM updates (no leaked event listeners)
- **Testing**: Validate on 5-year-old hardware baseline (2.0GHz dual-core, 4GB RAM, integrated graphics)

### VII. Database Schema Versioning ✅ N/A
- **Not Applicable**: Frontend-only migration, zero database schema changes
- **Note**: API endpoints and contracts remain unchanged

### VIII. Research-First Feature Design ✅ PASS
- **Compliant**: Comprehensive exploration of Vue 3, Alpine.js, Svelte, Lit, Web Components alternatives
- **Research Artifacts**: This plan documents findings, trade-offs, architectural rationale
- **Learnings**: Vue 3 Composition API ideal for scanner workflows (ref/reactive state), CDN-based deployment proven viable

### IX. Design-First Implementation ✅ PASS
- **Mockups**: Phase-by-phase component templates with detailed code examples (see Detailed Task Breakdown section)
- **Approval Gate**: User approves plan before Phase 0 implementation begins
- **Design Artifacts**: Component hierarchy diagram, routing structure diagram, state management flow

### X. Internationalization (i18n) ✅ PASS
- **Compliant**: Vue I18n 9 library (established standard for Vue ecosystem)
- **Languages**: English (en) + French (fr) fully supported (all user-facing text externalized)
- **Structure**: Existing `locales/en.json` and `locales/fr.json` reused (1:1 key mapping preserved)
- **Validation**: i18n keys validated via TypeScript JSDoc annotations (@typedef for translation keys)
- **Locale-Aware**: Vue I18n handles date/number formatting per locale (DD/MM/YYYY for FR, MM/DD/YYYY for EN)

**OVERALL GATE STATUS**: ✅ **PASS WITH IMPROVEMENTS** (Testing coverage to be added during migration)

---

## Technical Context

**Language/Version**: JavaScript ES6+ (modules), Vue 3.4.21+ (CDN global build)
**Primary Dependencies**:
- Vue 3.4.21 (core framework with Composition API) - https://unpkg.com/vue@3.4.21
- Vue Router 4.2.5 (hash-based Single-Page Application routing) - https://unpkg.com/vue-router@4.2.5
- Vue I18n 9.9.1 (internationalization) - https://unpkg.com/vue-i18n@9.9.1
- Bootstrap 5.3.3 (CSS framework, preserved from current) - https://cdn.jsdelivr.net/npm/bootstrap@5.3.3
- Bootstrap Icons 1.11.3 (icon font, preserved from current) - https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3

**Storage**: LocalStorage (language preference, user settings), SessionStorage (form state preservation during navigation)
**Testing**: Manual (Phase 0-1), Vitest (Phase 2-8 unit tests), Playwright (future E2E)
**Target Platform**: Chrome/Firefox/Safari/Edge (latest 2 versions each)
**Performance Goals**:
- Scanner feedback: <200ms p95 (critical path for circulation workflow)
- Page navigation: <100ms (hash routing instant transitions)
- API calls: <500ms p95 (network dependent, not in our control)

**Constraints**:
- ✅ No build tools (CDN-based Vue 3, ES modules only, no webpack/babel/vite)
- ✅ No frameworks besides Vue ecosystem (no React, Angular, Svelte, etc.)
- ✅ Preserve all existing UX patterns (scanner workflow, keyboard shortcuts, visual design)
- ✅ Maintain barcode scanner compatibility (USB HID keyboard mode input)
- ✅ Support legacy hardware (5+ year old computers with 2.0GHz dual-core, 4GB RAM)

---

## Architecture Overview

### Current Architecture (Hybrid - 4,793 LOC)

```
┌─────────────────────────────────────────────────────┐
│  index.html (885 lines)                              │
│  ├─ HTMX attributes (hx-get, hx-post, hx-target)     │
│  ├─ Alpine.js directives (x-data, x-model, @click)   │
│  └─ Vanilla JS event listeners (addEventListener)    │
└─────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ HTMX (HTML swap) │ │ Alpine.js (state)│ │ Vanilla JS (DOM) │
│ - 19 templates   │ │ - circulationPage│ │ - app.js (362)   │
│ - Dual-response  │ │ - catalogPage    │ │ - api.js (260)   │
│ - hx-* attrs     │ │ - borrowersPage  │ │ - i18n.js (197)  │
└──────────────────┘ └──────────────────┘ └──────────────────┘

Problems:
❌ 3 paradigms (HTMX declarative, Alpine reactive, vanilla imperative) cause confusion
❌ State synchronization issues (Alpine state !== DOM state in some cases)
❌ Dual-fetch pattern (same API call returns both HTML template and JSON data)
❌ Manual DOM manipulation (12 instances of innerHTML assignments, XSS risk)
❌ Fragile error parsing (regex on error strings instead of structured error codes)
```

### Target Architecture (Vue 3 - 2,300 LOC)

```
┌─────────────────────────────────────────────────────┐
│  index.html (120 lines)                              │
│  └─ <div id="app"></div>  ← Vue mounts here          │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Vue 3 App (CDN) - Single Paradigm                   │
│  ├─ Composition API (reactive state with ref/reactive)│
│  ├─ Template Syntax (declarative rendering)          │
│  └─ Component System (reusable, testable, isolated)  │
└─────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Pages (710 LOC)  │ │Components (780)  │ │ Composables(290) │
│ - CirculationPage│ │ - ItemScanner    │ │ - useApi         │
│ - CatalogPage    │ │ - BorrowerCard   │ │ - usePagination  │
│ - BorrowersPage  │ │ - SearchBar      │ │ - useNotification│
│ - ReportsPage    │ │ - Pagination     │ │ - useErrorHandler│
│ - SettingsPage   │ │ - Modal          │ │ - useFilters     │
└──────────────────┘ └──────────────────┘ └──────────────────┘

Benefits:
✅ Single paradigm (reactive components only, no mental model switching)
✅ Predictable state (Vue reactivity system, automatic dependency tracking)
✅ Single data format (JSON only, no dual HTML/JSON responses)
✅ Zero manual DOM manipulation (Vue handles all updates automatically)
✅ Structured errors (error_code + context object, no regex parsing)
```

---

## Migration Strategy: Parallel Implementation with Incremental Rollout

### Folder Structure (Separate from Existing Implementation)

```
src/bcd_web_vue/                 # NEW - Parallel Vue 3 implementation
├── index.html                   # NEW (120 lines) - Vue 3 entry point
├── js/
│   ├── app.js                   # NEW (150 lines) - Vue app initialization
│   ├── router.js                # NEW (150 lines) - Vue Router configuration
│   ├── api/
│   │   └── client.js            # NEW (200 lines) - Centralized API client
│   ├── composables/
│   │   ├── useApi.js            # NEW (40 lines) - API wrapper composable
│   │   ├── useAppState.js       # NEW (100 lines) - Global state (locale, loading)
│   │   ├── useNotification.js   # NEW (120 lines) - Toast notification system
│   │   ├── useErrorHandler.js   # NEW (70 lines) - Centralized error handling
│   │   ├── usePagination.js     # NEW (90 lines) - Pagination logic
│   │   └── useFilters.js        # NEW (150 lines) - URL-synced filtering
│   ├── models/
│   │   ├── borrower.js          # NEW (50 lines) - TypeScript JSDoc typedefs
│   │   ├── item.js              # NEW (60 lines) - TypeScript JSDoc typedefs
│   │   ├── pagination.js        # NEW (30 lines) - TypeScript JSDoc typedefs
│   │   └── error.js             # NEW (80 lines) - ApiError class + ERROR_CODES enum
│   ├── components/
│   │   ├── layout/
│   │   │   ├── SidebarNav.js    # NEW (100 lines) - Main sidebar container
│   │   │   ├── NavigationMenu.js # NEW (80 lines) - Nav menu with submenu support
│   │   │   ├── NavLink.js       # NEW (60 lines) - Single nav link with active state
│   │   │   └── LanguageSwitcher.js # NEW (50 lines) - FR/EN toggle buttons
│   │   ├── ui/
│   │   │   ├── NotificationContainer.js # NEW (80 lines) - Toast container
│   │   │   ├── Toast.js         # NEW (60 lines) - Individual toast notification
│   │   │   ├── Pagination.js    # NEW (100 lines) - Reusable pagination component
│   │   │   ├── LoadingSpinner.js # NEW (30 lines) - Loading indicator
│   │   │   ├── FilterSelect.js  # NEW (60 lines) - Dropdown filter component
│   │   │   └── Modal.js         # NEW (100 lines) - Bootstrap modal wrapper
│   │   ├── settings/
│   │   │   └── SettingsForm.js  # NEW (200 lines) - Phase 1 (easiest page)
│   │   ├── circulation/
│   │   │   ├── BorrowerScanner.js # NEW (120 lines) - Borrower ID input
│   │   │   ├── ItemScanner.js    # NEW (180 lines) - Item barcode scanner
│   │   │   ├── BorrowerCard.js   # NEW (150 lines) - Borrower info display
│   │   │   └── ScannedItemsList.js # NEW (80 lines) - Checked-out items list
│   │   ├── catalog/
│   │   │   ├── SearchBar.js      # NEW (120 lines) - Search input + filters
│   │   │   ├── SearchResults.js  # NEW (150 lines) - Results grid
│   │   │   ├── RecordDetail.js   # NEW (200 lines) - Bibliographic detail modal
│   │   │   └── AdvancedFilters.js # NEW (100 lines) - Category/availability filters
│   │   ├── borrowers/
│   │   │   ├── BorrowerFilters.js # NEW (100 lines) - Class/role/status filters
│   │   │   ├── BorrowerList.js    # NEW (150 lines) - Borrower table
│   │   │   ├── BorrowerDetail.js  # NEW (250 lines) - Detail modal with actions
│   │   │   └── BorrowerActions.js # NEW (120 lines) - Block/unblock/renew buttons
│   │   ├── reports/
│   │   │   ├── ReportTabs.js      # NEW (80 lines) - Tab navigation
│   │   │   ├── OverdueReport.js   # NEW (180 lines) - Overdue items by class
│   │   │   ├── MostBorrowedReport.js # NEW (120 lines) - Top borrowed items
│   │   │   └── NeverBorrowedReport.js # NEW (120 lines) - Never borrowed items
│   │   └── cataloging/
│   │       ├── ISBNLookup.js      # NEW (120 lines) - BNF API ISBN lookup
│   │       ├── BibliographicForm.js # NEW (200 lines) - Record creation form
│   │       └── ItemBarcodeInput.js # NEW (80 lines) - Item barcode entry
│   └── pages/
│       ├── SettingsPage.js      # NEW (150 lines) - Phase 1 (easiest to test)
│       ├── CirculationPage.js   # NEW (200 lines) - Phase 3 (most critical)
│       ├── CatalogPage.js       # NEW (180 lines) - Phase 4
│       ├── BorrowersPage.js     # NEW (180 lines) - Phase 5
│       ├── ReportsPage.js       # NEW (180 lines) - Phase 6
│       └── CatalogingPage.js    # NEW (180 lines) - Phase 7
├── locales/
│   ├── en.json                  # COPY from src/bcd_web/locales/en.json
│   └── fr.json                  # COPY from src/bcd_web/locales/fr.json
└── css/
    └── main.css                 # SYMLINK to src/bcd_web/css/main.css

src/bcd_web/                     # EXISTING - Preserved during migration
├── index.html                   # PRESERVED (885 lines HTMX/Alpine)
├── templates/                   # PRESERVED (19 template fragments)
├── js/                          # PRESERVED (app.js, api.js, i18n.js, pages/*.js)
└── ...                          # PRESERVED (all existing files remain untouched)

Total New Code: ~6,500 lines across 8 phases
```

### Server Configuration (Implemented)

The system now serves Vue 3 web UI by default from `src/bcd_web_vue/`.

**Implementation** (see `src/bcd_api/main.py:36-43`):
- Uses `is_portable()` function to detect bundled vs development mode
- Portable mode: Looks for `bcd_web_vue` in bundled resources
- Development mode: Uses `src/bcd_web_vue` directory
- Legacy HTMX implementation archived at `src/bcd_web_legacy/` (not actively maintained)

**Rollback Plan**:
- Git tag before migration: Can revert entire repository state if needed
- Legacy code preserved at `src/bcd_web_legacy/` for reference
- No database changes (frontend-only migration)

---

## Detailed Task Breakdown by Phase

### Phase 0: Foundation Setup (4 hours)

Create core infrastructure that all pages will depend on.

**Task 0.1: Create project structure** (1 hour)
- Create `src/bcd_web_vue/` directory with all subdirectories
- Copy locale files (`locales/en.json`, `locales/fr.json`) from `src/bcd_web/`
- Symlink `css/main.css` to reuse existing styles
- Create blank `index.html` skeleton with Vue 3 CDN scripts

**Task 0.2: Implement core composables** (3 hours)
- `api/client.js` (200 LOC) - Centralized API client with loading state, error handling, i18n headers
- `models/error.js` (80 LOC) - ERROR_CODES enum + ApiError class with getTranslatedMessage() method
- `composables/useAppState.js` (100 LOC) - Global state (locale, loading, settings) with localStorage persistence
- `composables/useNotification.js` (120 LOC) - Toast notification system (success, error, warning, info) with auto-dismiss
- `composables/useErrorHandler.js` (70 LOC) - Centralized error handling with special cases (LOAN_LIMIT_EXCEEDED, BORROWER_BLOCKED, etc.)
- `composables/useApi.js` (40 LOC) - Wrapper composable for API client

**Deliverable**: Foundation infrastructure ready for page-by-page migration

---

### Phase 1: Settings Page (Easiest - 6 hours)

Start with settings page because it's the simplest (form with no complex interactions, no scanner workflow).

**Task 1.1: Settings page setup** (1 hour)
- Create `pages/SettingsPage.js` with route `/settings`
- Create `components/settings/SettingsForm.js` component
- Add route to `router.js`: `{ path: '/settings', component: SettingsPage }`

**Task 1.2: Migrate settings form** (3 hours)
**Current implementation**: `templates/fragments/settings_form.html` (Jinja2 with HTMX `hx-put`)
**Vue 3 implementation**: See complete code example in plan.md (settings form with all 14 fields)

**Task 1.3: Settings page layout** (1 hour)
- Create `pages/SettingsPage.js` wrapper
- Add page title + breadcrumbs
- Integrate SettingsForm component
- Add loading spinner for initial data fetch

**Task 1.4: Test settings migration** (1 hour)
- [ ] Load settings from API successfully
- [ ] All 14 form fields render with correct values
- [ ] Save updates successfully with success notification
- [ ] Form validation errors display inline
- [ ] Reset button restores original values
- [ ] i18n works (switch EN ↔ FR, all labels translate)
- [ ] Browser back/forward navigation works

**Deliverable**: Settings page fully migrated and validated against acceptance criteria

---

### Phase 2: Layout Components (8 hours)

Build the shell that all pages will render inside (sidebar, nav, notifications).

**Task 2.1: Minimal app.js and router** (2 hours)
- Create `js/app.js` with Vue app initialization, i18n setup, router setup
- Create `js/router.js` with initial route to Settings only
- Load Vue 3, Vue Router, Vue I18n from CDN
- Mount app to `#app` div

**Task 2.2: Sidebar navigation** (2 hours)
- Create `components/layout/SidebarNav.js` with BCD logo, nav menu, language switcher
- Create `components/layout/NavigationMenu.js` with all navigation items + reports submenu
- Create `components/layout/NavLink.js` with active state highlighting
- Implement `isActive()` logic for parent items with submenus

**Task 2.3: Language switcher** (1 hour)
- Create `components/layout/LanguageSwitcher.js` with FR/EN buttons
- Use useI18n() to get/set locale
- Persist locale to localStorage via useAppState()
- Update `document.documentElement.lang` attribute

**Task 2.4: Main App component** (1 hour)
- Create `components/App.js` with sidebar + router-view layout
- Add `<notification-container />` for toasts
- Add transition for page changes

**Task 2.5: Notification system** (2 hours)
- Create `components/ui/NotificationContainer.js` with transition-group
- Create `components/ui/Toast.js` with auto-dismiss timer
- Add CSS animations for toast enter/leave
- Test all notification types: success, error, warning, info

**Deliverable**: Complete layout with working navigation, language switching, and notifications

---

### Phase 3: Circulation Page (12 hours)

Most critical workflow for daily library operations.

**Task 3.1: Analyze current circulation** (1 hour)
- Read `js/pages/circulation.js` (Alpine.js with checkout/return modes)
- Read `templates/fragments/borrower_info.html` (borrower info panel)
- Read `templates/fragments/checkout_confirmation.html` (item checkout confirmation)
- Document workflow: scan borrower → scan items → immediate checkout (no confirm)

**Task 3.2: Borrower scanner component** (2 hours)
- Create `components/circulation/BorrowerScanner.js`
- Input with ref for auto-focus
- Enter key triggers `loadBorrower()` API call
- Emit 'borrower-loaded' event to parent
- Display error if borrower blocked (checkout mode only)

**Task 3.3: Borrower card component** (2 hours)
- Create `components/circulation/BorrowerCard.js`
- Display name, class, role with icons
- Show current loans count + overdue count with badges
- Render current loans table with due dates
- Quick action buttons: Return All, Renew All

**Task 3.4: Item scanner component** (3 hours)
- Create `components/circulation/ItemScanner.js`
- Input with auto-focus that returns after each scan
- Checkout mode: immediate `POST /circulation/checkout` on Enter
- Return mode: immediate `POST /circulation/return` on Enter
- Display scanned items list with success/error feedback
- Auto-clear input after each successful scan

**Task 3.5: Circulation page integration** (2 hours)
- Create `pages/CirculationPage.js` with mode prop ('checkout' or 'return')
- Integrate BorrowerScanner + BorrowerCard + ItemScanner
- Add routes: `/checkout` and `/return` with mode props
- Manage currentBorrower ref state

**Task 3.6: Test circulation workflow** (2 hours)
- [ ] Checkout: scan borrower → scan 5 items rapidly (<10 seconds total)
- [ ] Return: scan 5 items rapidly without borrower (<5 seconds total)
- [ ] Scanner feedback <200ms per item (critical performance metric)
- [ ] Auto-focus returns to input after each scan
- [ ] Overdue warnings display with red badges
- [ ] Loan limit enforcement blocks additional checkouts
- [ ] Blocked borrower displays error and prevents checkout
- [ ] i18n works for all error messages

**Deliverable**: Full circulation page with checkout + return modes validated

---

### Phase 4: Catalog Page (10 hours)

Search and browse bibliographic records.

**Task 4.1: Analyze catalog** (1 hour)
- Read `js/pages/catalog.js` (search, filters, pagination state)
- Read `templates/fragments/search_results.html` (results grid)
- Read `templates/fragments/record_detail.html` (modal with items table)

**Task 4.2: Search bar component** (2 hours)
- Create `components/catalog/SearchBar.js` with debounced input (300ms)
- Advanced filters dropdown (availability, category, language)
- URL sync using useFilters() composable
- Clear button to reset all filters

**Task 4.3: Search results component** (2 hours)
- Create `components/catalog/SearchResults.js`
- Display cards with title, author, publication year
- Color-coded availability badges (green/orange/red)
- Click card to open RecordDetail modal
- Empty state when no results
- Loading skeleton during API call

**Task 4.4: Pagination component** (2 hours)
- Create `components/ui/Pagination.js` (reusable for all pages)
- Page numbers with ellipsis (...) for large page counts
- Page size selector (50/100 items)
- "Showing X-Y of Z items" text
- Prev/Next buttons with disabled state

**Task 4.5: Record detail modal** (2 hours)
- Create `components/catalog/RecordDetail.js`
- Display all bibliographic fields
- Items table showing all copies with status badges
- Circulation history table
- Cross-navigation links to borrower detail
- Quick "Return this item" button if item on loan

**Task 4.6: Test catalog** (1 hour)
- [ ] Search by title, author, ISBN
- [ ] Filters work (availability, category)
- [ ] Pagination works (prev/next, page numbers, page size)
- [ ] Detail modal opens/closes
- [ ] Quick return from modal works
- [ ] Cross-navigation to borrower works
- [ ] URL updates with search params (refresh preserves state)

**Deliverable**: Complete catalog search and browse functionality

---

### Phase 5: Borrowers Page (10 hours)

Borrower management with list, detail, block/unblock actions.

**Task 5.1: Borrower filters** (2 hours)
- Create `components/borrowers/BorrowerFilters.js`
- Search input with debounce (300ms)
- Class dropdown (CP-A, CP-B, CE1-A, etc.)
- Role dropdown (student, teacher, staff)
- Status filter (active, blocked)
- URL sync using useFilters()

**Task 5.2: Borrower list** (2 hours)
- Create `components/borrowers/BorrowerList.js`
- Table with columns: ID, Name, Class, Current Loans, Status
- Status badge (green=active, red=blocked)
- Warning icon for overdue items
- Click row to open BorrowerDetail modal
- Reuse Pagination component

**Task 5.3: Borrower detail modal** (3 hours)
- Create `components/borrowers/BorrowerDetail.js`
- Reuse BorrowerCard from circulation page
- Reuse CurrentLoansTable component
- Add circulation history section
- Footer with actions: Block, Unblock, Renew All, Edit

**Task 5.4: Borrower actions** (2 hours)
- Create `components/borrowers/BorrowerActions.js`
- Block modal with reason dropdown (Lost Book, Damaged Materials, etc.)
- Unblock confirmation dialog
- Renew all with summary (success count + failures)
- Edit borrower (future: link to edit form)

**Task 5.5: Test borrowers page** (1 hour)
- [ ] Filter by class works
- [ ] Search by name works
- [ ] Detail modal opens with all data
- [ ] Block/unblock actions work
- [ ] Renew all displays summary correctly
- [ ] Pagination works
- [ ] Cross-navigation to catalog works

**Deliverable**: Complete borrower management functionality

---

### Phase 6: Reports Page (8 hours)

Three report types with filters and print support.

**Task 6.1: Report tabs** (1 hour)
- Create `components/reports/ReportTabs.js`
- Three tabs: Overdue, Most Borrowed, Never Borrowed
- Tab click updates route (`/reports/overdue`, etc.)

**Task 6.2: Overdue report** (2 hours)
- Create `components/reports/OverdueReport.js`
- Group by class (collapsible sections using Bootstrap collapse)
- Each row: borrower name (link), item title (link), days overdue (badge)
- Print button with `@media print` CSS
- Filter by class dropdown

**Task 6.3: Most borrowed report** (2 hours)
- Create `components/reports/MostBorrowedReport.js`
- Ranked list with checkout counts
- Visual bar chart using CSS width percentages
- Top N selector (10, 25, 50)

**Task 6.4: Never borrowed report** (2 hours)
- Create `components/reports/NeverBorrowedReport.js`
- Table of records with zero checkouts
- Filter by category
- Reuse Pagination component

**Task 6.5: Test reports** (1 hour)
- [ ] All three reports load
- [ ] Overdue grouped by class correctly
- [ ] Print formatting works (print preview looks good)
- [ ] Filters work
- [ ] Cross-navigation works

**Deliverable**: All three report types functional

---

### Phase 7: Cataloging Page (6 hours)

ISBN lookup and bibliographic record creation.

**Task 7.1: ISBN lookup** (2 hours)
- Create `components/cataloging/ISBNLookup.js`
- ISBN input (scanner compatible)
- Lookup button triggers BNF API call
- Display results in editable form
- Error handling for ISBN not found

**Task 7.2: Bibliographic form** (2 hours)
- Create `components/cataloging/BibliographicForm.js`
- Auto-fill from BNF data or manual entry
- All fields: title, author, publisher, year, category, etc.
- Form validation (required fields, ISBN format)
- Submit creates bibliographic record via `POST /catalog/records`

**Task 7.3: Item barcode input** (1 hour)
- Create `components/cataloging/ItemBarcodeInput.js`
- After bibliographic record created, scan barcode to create item
- Display created item with success message
- "Add another copy" button to create multiple items

**Task 7.4: Test cataloging** (1 hour)
- [ ] ISBN lookup works with valid ISBN
- [ ] Manual entry works without ISBN
- [ ] Barcode scanning creates items
- [ ] Validation displays errors
- [ ] Success notifications appear

**Deliverable**: Complete cataloging workflow

---

### Phase 8: Cleanup and Launch (4 hours)

Final polish and production deployment.

**Task 8.1: Remove feature flag** (1 hour)
- Update `server.py` to default `VUE_MODE=true`
- Move old implementation to `src/bcd_web_legacy/` for rollback safety
- Update deployment docs

**Task 8.2: Documentation** (2 hours)
- Update README with Vue 3 architecture
- Document component structure + hierarchy
- Document composables usage patterns
- Create migration notes for future developers

**Task 8.3: Final testing** (1 hour)
- [ ] All pages work end-to-end
- [ ] All workflows validated (checkout, return, search, etc.)
- [ ] Performance validated (<200ms scanner, <100ms navigation)
- [ ] Cross-browser tested (Chrome, Firefox, Safari, Edge)
- [ ] i18n complete (all strings in EN + FR)
- [ ] Legacy hardware tested (5-year-old computer)

**Deliverable**: Production-ready Vue 3 web UI

---

## Total Timeline

| Phase | Focus | Hours | Weeks (8h/week) |
|-------|-------|-------|-----------------|
| 0 | Foundation | 4 | 0.5 |
| 1 | Settings Page | 6 | 0.75 |
| 2 | Layout Components | 8 | 1 |
| 3 | Circulation Page | 12 | 1.5 |
| 4 | Catalog Page | 10 | 1.25 |
| 5 | Borrowers Page | 10 | 1.25 |
| 6 | Reports Page | 8 | 1 |
| 7 | Cataloging Page | 6 | 0.75 |
| 8 | Cleanup & Launch | 4 | 0.5 |
| **Total** | **All Pages** | **68** | **8.5** |

**Assumptions**: Part-time = 8 hours/week; Full-time = 40 hours/week
**Full-time equivalent**: ~2 weeks (1.7 weeks at 40 hours/week)

---

## Migration Metrics

| Metric | Before (HTMX/Alpine) | After (Vue 3) | Change |
|--------|---------------------|---------------|--------|
| Total Lines of Code | 4,793 | 2,300 | **-52%** |
| HTML | 885 | 120 | **-86%** |
| JavaScript | 3,908 | 2,180 | **-44%** |
| Template Files | 19 files | 0 files | **-100%** |
| Frameworks | 3 (HTMX+Alpine+Vanilla) | 1 (Vue) | **-67%** |
| Manual DOM manipulation | 12 instances | 0 instances | **-100%** |
| Dual API responses | HTML + JSON | JSON only | Simplified |
| Error handling | Regex parsing | Structured codes | Improved |
| Component reusability | Low (templates) | High (40+ components) | Improved |

---

## Rollback Plan

### Emergency Rollback (Phase 1-7)
- Keep original HTMX implementation in `src/bcd_web/` untouched during migration
- Feature flag allows instant switch: set `VUE_MODE=false` and restart server
- Rollback time: <1 minute (no database changes, frontend-only migration)

### Post-Launch Rollback (Phase 8+)
- Git tag before merge: `v1.0-pre-vue-migration`
- Move old implementation to `src/bcd_web_legacy/` (not deleted)
- Database unchanged (frontend-only migration)
- Rollback procedure: `git checkout v1.0-pre-vue-migration` or point VUE_MODE to legacy folder

---

## Verification Checklist

### Functional Testing (All Acceptance Scenarios)
- [ ] **Circulation**: Checkout 100 items in <30s
- [ ] **Circulation**: Return 50 items in <15s
- [ ] **Catalog**: Search results appear <2s
- [ ] **Borrowers**: Filter by class <1s
- [ ] **Reports**: Generate overdue report <3s
- [ ] **Settings**: Update settings <1s
- [ ] **i18n**: All strings translated (EN + FR, zero hard-coded strings)
- [ ] **Navigation**: All routes accessible, browser back/forward works
- [ ] **Pagination**: Works on all list pages (catalog, borrowers, reports)
- [ ] **Filtering**: Works on all filterable pages (catalog, borrowers, reports)

### Performance Testing (Constitution Principle VI)
- [ ] **Scanner feedback**: <200ms p95 (most critical metric)
- [ ] **Page load**: <3s cold start on legacy hardware
- [ ] **Page navigation**: <100ms (hash routing)
- [ ] **API calls**: <500ms p95 (network dependent)
- [ ] **Memory**: <500MB after 1 hour continuous use
- [ ] **No memory leaks**: Heap size stable over time

### Cross-Browser Testing (FR-007)
- [ ] **Chrome**: Latest 2 versions (works without issues)
- [ ] **Firefox**: Latest 2 versions (works without issues)
- [ ] **Safari**: Latest 2 versions (works without issues, including iOS Safari)
- [ ] **Edge**: Latest 2 versions (works without issues)

### Legacy Hardware Testing (Constitution Principle VI)
- [ ] **5-year-old hardware**: 2.0GHz dual-core, 4GB RAM, integrated graphics
- [ ] **Scanner workflow**: Maintains <200ms feedback on legacy hardware
- [ ] **No UI freezing**: All operations remain responsive
- [ ] **Animations**: 60fps smooth transitions (or gracefully degraded)

---

## Next Steps

1. **User approval**: Review and approve this detailed implementation plan
2. **Create branch**: `git checkout -b 004-vue-migration`
3. **Phase 0 kickoff**: Set up `src/bcd_web_vue/` folder structure and core composables
4. **Phase 1 validation**: Migrate Settings page and validate against acceptance criteria (go/no-go gate)
5. **Phase 2-8 execution**: Continue incremental migration with testing at each phase
6. **Final validation**: Complete verification checklist before production deployment

---

**Questions for User (if any)**:
- Approve CDN-based Vue 3 approach with no build tools? (npm-free, webpack-free)
- Approve 8.5-week part-time timeline (68 hours total, ~2 weeks full-time)?
- Approve parallel implementation strategy with feature flag rollback?
- Need working prototype before Phase 1 approval? (can demo Settings page first)
- Manual testing acceptable for Phase 0-1, automated testing Phase 2+?
