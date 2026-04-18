# Implementation Plan: Aide Contextuelle Intégrée

**Branch**: `001-contextual-help` | **Date**: 2026-03-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-contextual-help/spec.md`

---

## Summary

Integrate contextual help panels (Bootstrap offcanvas from the right) on all 8 main pages of the BCD Vue 3 SPA. A single reusable `HelpPanel.js` component loads page-specific markdown (FR/EN) via lazy `fetch()` and renders it with vendored `marked.js`. The simulation script is enriched with 4 targeted functions covering 7 previously missing data states. A new Playwright script generates ~21 annotated screenshots from those real states. Help markdown content (16 files) is written following a strict format contract for teacher-facing step-by-step instructions.

---

## Technical Context

**Language/Version**: Python 3.11 (scripts), JavaScript ES2020 (Vue 3 SPA — no transpilation)
**Primary Dependencies**: Vue 3.4.21 (already vendored), Bootstrap 5.3.3 offcanvas (already vendored), `marked.js` v9 (to vendor, ~50KB UMD global build)
**Storage**: Static files — `src/bcd_web_vue/help/{fr,en}/*.md` + `src/bcd_web_vue/help/images/*.png`
**Testing**: Playwright E2E for help panel (open/close/language switch/error state); pytest integration test verifying simulation scenario coverage
**Target Platform**: Linux (school server) + Windows (portable build), offline-capable
**Project Type**: Web SPA (no build tools) + Python utility scripts
**Performance Goals**: Panel opens < 2 seconds (SC-007); screenshot script completes < 5 minutes (SC-005)
**Constraints**: No CDN (offline-first); no npm/build tools; lazy content load (fetch on click only); PNG full-resolution (clarification Q2)
**Scale/Scope**: 8 pages × 2 languages = 16 markdown files; 21 screenshots; 1 reusable component; 4 new simulation functions

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|---------|
| I. DRY | ✅ PASS | Single `HelpPanel.js` for all 8 pages; `SECTION_FILES` map centralizes locale→filename mapping |
| II. Library-First | ✅ PASS | Bootstrap offcanvas (in bundle) + marked.js (standard renderer, ~50KB); no custom parsers |
| III. Testing | ✅ PASS | E2E tests: open/close/language/error; pytest fixture verifies all 7 FR-009 scenarios post-simulation |
| IV. UX Consistency | ✅ PASS | Reuses `.page-header` + `btn btn-outline-secondary btn-sm` + `bi-question-circle` icon pattern |
| V. Click Minimization | ✅ PASS | 1 click from any page to open contextual help |
| VI. Legacy Hardware | ✅ PASS | Lazy fetch (only on click); images loaded by browser natively; no preloading |
| VII. DB Migrations | N/A | No database schema changes required |
| VIII. Research-First | ✅ PASS | Modal.js pattern analyzed; vendor structure confirmed; marked.js evaluated vs. alternatives |
| IX. Design-First | ✅ PASS | Component wireframe, file contracts, and data model defined in this plan |
| X. i18n | ✅ PASS | Button + section titles in locale files; help prose in separate language files |
| XI. Quality Gate | ✅ PASS | `/speckit.analyze` before `/speckit.implement`; `/speckit.review` after |

**No violations. Complexity tracking not required.**

---

## Project Structure

### Documentation (this feature)

```text
specs/001-contextual-help/
├── plan.md                         # This file
├── research.md                     # Phase 0 ✅
├── data-model.md                   # Phase 1 ✅
├── quickstart.md                   # Phase 1 ✅
├── contracts/
│   ├── help-markdown-format.md     # Phase 1 ✅
│   └── screenshot-naming.md        # Phase 1 ✅
└── tasks.md                        # Phase 2 (/speckit.tasks)
```

### Source Code Layout

```text
src/bcd_web_vue/
├── vendor/js/
│   └── marked.min.js                    ← NEW (download from jsDelivr)
├── help/
│   ├── fr/                              ← NEW (8 FR markdown files)
│   │   ├── emprunter.md
│   │   ├── retourner.md
│   │   ├── catalogue.md
│   │   ├── catalogage.md
│   │   ├── eleves.md
│   │   ├── classes.md
│   │   ├── rapports.md
│   │   └── parametres.md
│   ├── en/                              ← NEW (8 EN markdown files)
│   │   ├── checkout.md
│   │   ├── return.md
│   │   ├── catalog.md
│   │   ├── cataloging.md
│   │   ├── borrowers.md
│   │   ├── classes.md
│   │   ├── reports.md
│   │   └── settings.md
│   └── images/                          ← NEW (21 PNGs, git-ignored in CI)
│       └── *.png
├── index.html                           ← MODIFIED (+marked.min.js script tag)
├── css/main.css                         ← MODIFIED (+.help-markdown img styles)
├── locales/fr.json                      ← MODIFIED (+help.* and navigation.help keys)
├── locales/en.json                      ← MODIFIED (+help.* and navigation.help keys)
└── js/
    ├── components/ui/
    │   └── HelpPanel.js                 ← NEW (reusable offcanvas component)
    └── pages/
        ├── CirculationPage.js           ← MODIFIED (+HelpPanel, :section dynamic)
        ├── CatalogPage.js               ← MODIFIED (+HelpPanel section="catalog")
        ├── CatalogingPage.js            ← MODIFIED (+HelpPanel section="cataloging")
        ├── BorrowersPage.js             ← MODIFIED (+HelpPanel section="borrowers")
        ├── ClassesPage.js               ← MODIFIED (+HelpPanel section="classes")
        ├── ReportsPage.js               ← MODIFIED (+HelpPanel section="reports")
        └── SettingsPage.js              ← MODIFIED (+HelpPanel section="settings")

scripts/
├── reset_and_simulate.py                ← MODIFIED (4 new enrichment functions)
└── generate_help_screenshots.py         ← NEW (Playwright screenshot automation)

tests/e2e/
└── test_help_panel.py                   ← NEW (Playwright E2E tests)
```

**Structure Decision**: Single-project layout — no backend changes whatsoever. Pure frontend additions + Python utility scripts following existing project patterns.

---

## Phase 0: Research Findings

See [research.md](./research.md) for full details. Key decisions:

| Topic | Decision |
|-------|---------|
| Markdown renderer | `marked.js` v9 (UMD global, ~50KB) vendored in `vendor/js/` |
| Panel pattern | Bootstrap 5.3 offcanvas (already in bundle), modeled after `Modal.js` |
| Content loading | Lazy `fetch('/static/help/{locale}/{file}.md')` on panel open |
| Image format | PNG full-resolution, lazy browser loading, no preload |
| Screenshot tool | Playwright (already in dev deps), new script querying SQLite for real IDs |
| Simulation | 4 new functions appended to `reset_and_simulate.py` |

---

## Phase 1: Design

### Component Design: HelpPanel.js

**File**: `src/bcd_web_vue/js/components/ui/HelpPanel.js`

**Props**: `section` (String, required) — one of 8 known section IDs

**Internal SECTION_FILES map**:
```javascript
const SECTION_FILES = {
    checkout:   { fr: 'emprunter.md',  en: 'checkout.md' },
    return:     { fr: 'retourner.md',  en: 'return.md' },
    catalog:    { fr: 'catalogue.md',  en: 'catalog.md' },
    cataloging: { fr: 'catalogage.md', en: 'cataloging.md' },
    borrowers:  { fr: 'eleves.md',     en: 'borrowers.md' },
    classes:    { fr: 'classes.md',    en: 'classes.md' },
    reports:    { fr: 'rapports.md',   en: 'reports.md' },
    settings:   { fr: 'parametres.md', en: 'settings.md' },
};
```

**Key reactive state**: `rawMd` (string), `loading` (bool), `error` (bool)

**Fetch logic** (called on `watch([section, locale], fetchHelp, { immediate: true })`):
```javascript
const fetchHelp = async () => {
    loading.value = true;
    error.value = false;
    const files = SECTION_FILES[props.section];
    const filename = files[locale.value] || files.en;
    try {
        const res = await fetch(`/static/help/${locale.value}/${filename}`);
        if (!res.ok) throw new Error(res.status);
        rawMd.value = await res.text();
    } catch {
        // Fallback to EN if locale file missing
        try {
            const res2 = await fetch(`/static/help/en/${files.en}`);
            rawMd.value = res2.ok ? await res2.text() : null;
        } catch {
            rawMd.value = null;
            error.value = true;
        }
    } finally {
        loading.value = false;
    }
};
```

**Rendering**: `renderedMarkdown = computed(() => rawMd.value ? marked.parse(rawMd.value) : '')`

**Template structure** (simplified):
```html
<div>
  <!-- Trigger button (placed in page-header by parent page) -->
  <button class="btn btn-outline-secondary btn-sm"
          data-bs-toggle="offcanvas"
          data-bs-target="#bcd-help-offcanvas"
          :title="t('help.button')">
    <i class="bi bi-question-circle me-1"></i>{{ t('help.button') }}
  </button>

  <!-- Offcanvas panel (rendered once, shown/hidden by Bootstrap) -->
  <div class="offcanvas offcanvas-end"
       id="bcd-help-offcanvas"
       tabindex="-1"
       style="width: min(480px, 100vw)">
    <div class="offcanvas-header border-bottom">
      <h5 class="offcanvas-title">
        <i class="bi bi-question-circle me-2 text-primary"></i>
        {{ t('help.sections.' + section) }}
      </h5>
      <button type="button" class="btn-close" data-bs-dismiss="offcanvas"
              :aria-label="t('common.close')"></button>
    </div>
    <div class="offcanvas-body">
      <loading-spinner v-if="loading" />
      <div v-else-if="error" class="alert alert-warning">
        {{ t('help.error') }}
      </div>
      <div v-else v-html="renderedMarkdown" class="help-markdown"></div>
    </div>
  </div>
</div>
```

**Imports needed**: `LoadingSpinner` (already in `ui/`), `useAppState` (for `locale`), `useI18n`

---

### CSS Addition (main.css)

Add after existing UI styles:
```css
/* Help panel markdown rendering */
.help-markdown img {
    max-width: 100%;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    margin: 12px 0;
    display: block;
}
.help-markdown h2 {
    font-size: 1.05rem;
    font-weight: 600;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
    color: var(--bcd-primary);
    border-bottom: 1px solid var(--bcd-border);
    padding-bottom: 0.25rem;
}
.help-markdown blockquote {
    background: #f0f7ff;
    border-left: 3px solid var(--bcd-primary);
    padding: 0.5rem 0.75rem;
    margin: 0.75rem 0;
    border-radius: 0 4px 4px 0;
}
.help-markdown table {
    width: 100%;
    font-size: 0.875rem;
    border-collapse: collapse;
    margin: 0.75rem 0;
}
.help-markdown td, .help-markdown th {
    border: 1px solid var(--bcd-border);
    padding: 0.375rem 0.5rem;
}
.help-markdown th {
    background: var(--bcd-bg-sidebar);
    font-weight: 600;
}
```

---

### Page Integration Pattern

For each page, 3 changes:

**1. Import** (top of file):
```javascript
import HelpPanel from '../components/ui/HelpPanel.js';
```

**2. Register** (in `components: {}`):
```javascript
components: { ..., HelpPanel }
```

**3. Template** (in `.page-header`, inside the `div.d-flex.gap-2` buttons container):
```html
<help-panel section="catalog" />
```

For `CirculationPage.js` (dynamic section):
```javascript
// In setup(), computed from props.mode:
const helpSection = computed(() => props.mode === 'return' ? 'return' : 'checkout');
```
```html
<help-panel :section="helpSection" />
```

---

### Simulation Enrichment Design

4 new functions appended to `scripts/reset_and_simulate.py`, called at end of `main()`:

#### `create_teachers_and_staff(session, classes)`
- Creates 1 teacher per class (role=TEACHER, class_id)
- Creates 1 directeur (role=STAFF, no class)
- Creates 3 active loans for one teacher (demonstrates higher limit)
- Creates 2 manually blocked students (active=False, blocked_reason set)
- Returns dict of created borrowers for use by subsequent functions

#### `diversify_item_statuses(session)`
- Marks 3 items → `status='in_repair'`, `loanable=False`
- Marks 2 items → `status='lost'`
- Marks 1 item → `loanable=False` (reference, status stays available)
- Selects from items not currently on loan

#### `create_demo_holds(session, today)`
- Hold A: status=`waiting`, queue_position=1, on an item that is currently on_loan
- Hold B: status=`ready`, expiration_date=today+2, on an available item
- Hold C: status=`waiting`, queue_position=2, same bibliographic record as A
- Hold D: status=`expired`, historical
- All holds linked to real borrower/bibliographic_record IDs from DB

#### `create_demo_current_loans(session, today)`
- Loan X: due_date=today-5 (overdue by 5 days) → borrower auto-flagged
- Loan Y: due_date=today (due today)
- Loan Z: due_date=today+2 (due soon)
- Loan W: renewal_count=1, due_date=today+7 (renewed once)
- Loan V: renewal_count=2, due_date=today+14 (at renewal limit)
- All use items with status='available' set to 'on_loan' after insert

---

### Screenshot Script Design

**File**: `scripts/generate_help_screenshots.py`

**Structure**:
```python
async def get_demo_data(db_path: Path) -> dict:
    """Query SQLite for real IDs needed for screenshots."""
    # Returns: active_borrower_id, overdue_borrower_id,
    #          at_limit_borrower_id, available_item_barcode,
    #          detail_record_id (has on-loan copy)

async def capture_screenshots(base_url: str, demo: dict, output_dir: Path):
    """Capture all 21 screenshots."""
    # Each capture = navigate + optional interactions + wait + screenshot

async def main():
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "bcd.db"
    output_dir = project_root / "src/bcd_web_vue/help/images"
    output_dir.mkdir(parents=True, exist_ok=True)
    demo = await get_demo_data(db_path)
    await capture_screenshots("http://127.0.0.1:8000", demo, output_dir)
```

---

### E2E Test Design

**File**: `tests/e2e/test_help_panel.py`

Key test cases:
```python
def test_help_panel_opens_on_checkout_page(page, live_server)
def test_help_panel_content_is_checkout_specific(page, live_server)
def test_help_panel_closes_on_dismiss(page, live_server)
def test_help_panel_updates_on_language_switch(page, live_server)
def test_help_panel_shows_error_when_content_missing(page, live_server)
def test_all_8_pages_have_help_button(page, live_server)
def test_help_panel_closes_on_navigation(page, live_server)
```

---

## Verification Checklist

| Check | Method |
|-------|--------|
| SC-002: 8 pages have Aide button | E2E: `test_all_8_pages_have_help_button` |
| SC-003: FR + EN content | E2E: `test_help_panel_updates_on_language_switch` |
| SC-004: Screenshots show real data | Manual: inspect generated PNGs |
| SC-005: Script < 5 minutes | Manual: time the script |
| SC-006: 7 FR-009 scenarios present | pytest fixture: `test_simulation_scenarios` |
| SC-007: Panel opens < 2 seconds | E2E: measure time from click to panel visible |
| FR-011: Graceful degradation | E2E: `test_help_panel_shows_error_when_content_missing` |

---

## Phase 2: Implementation Status

**tasks.md created**: 2026-03-27 — 42 tasks across 8 phases.
**Implementation completed**: 2026-03-28

### Completed tasks

- T001–T039: all infrastructure, UI, markdown content, E2E tests, simulation functions, and screenshot script
- T040: script image names aligned with markdown references (23 images, up from 21 planned)

### Deviations from plan

| Area | Planned | Actual |
|------|---------|--------|
| Screenshot count | 21 | 23 (added `checkout-04-confirmed`, `cataloging-03-manual`, `cataloging-04-barcode`, `borrowers-04-import`; removed `printing-01-cards`) |
| Screenshot names | Contract names (`return-02-borrower-loans`, etc.) | Markdown-referenced names (`return-02-item-returned`, `return-03-borrower-loaded`, etc.) — markdown was authored before alignment check |
| Help content tone | Not specified | Full teacher-only tone pass: "Utilisez" → "tu" form; CSV sections rewritten with Excel step-by-step instructions |
| `generate_help_screenshots.py` signature | `async def main()` | `def main()` calling `asyncio.run(capture_screenshots(...))` with `argparse` CLI args |
| Playwright timeout | Default (30s) | Set to 5 seconds per operation to avoid hangs on missing selectors |

### Pending (requires running server)

- T041: full end-to-end quickstart validation
- Task checkbox updates in tasks.md (post-image verification)
