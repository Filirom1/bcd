# Implementation Plan: Fast Cataloging Workflow

**Branch**: `015-cataloging-ui` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/015-cataloging-ui/spec.md`

## Summary

Improve the three-stage cataloging workflow for rapid book scanning: keep its step controls and primary action visible, expose contextual Enter/Escape shortcuts, represent navigation in the URL so browser history restores persisted records, and show available covers in bibliographic review, copy creation, and remote title-search candidates. Keep local search first; when a text query has no local match, return selectable BnF, Google Books, and SUDOC candidates. Reuse the existing route and catalog persistence, extend the existing source lookup contract, and do not add a database entity or persistent draft.

## Technical Context

**Language/Version**: JavaScript ES modules, Vue 3  
**Primary Dependencies**: Vue Router, Vue I18n, Bootstrap 5, existing cataloging components  
**Storage**: Existing catalog API and database records; no schema changes  
**Testing**: Vitest through `python run_tests.py js`; focused pytest provider, API, and catalog lookup tests; reuse the existing Playwright browser smoke test without adding a feature-specific E2E test
**Target Platform**: Desktop browsers on Linux and Windows, including school computers  
**Project Type**: Vue single-page web application served by the FastAPI application  
**Performance Goals**: Primary actions remain responsive within the project target of 100 ms; no additional blocking network calls during ordinary step changes  
**Constraints**: Hash-based router; no saved draft; only the active lookup value and persisted record identifier may be encoded in the URL; remote search uses configured per-source timeouts and returns at most 10 candidates per source; all user-facing text must be translated in English and French  
**Scale/Scope**: Cataloging page, search/form/copy components, existing catalog lookup service, BnF, Google Books, and SUDOC provider adapters, and focused UI/backend tests; no database, CLI, or Godot changes

## Constitution Check

| Principle | Gate | Design response |
|---|---|---|
| Code quality and library-first | PASS | Reuse the existing router, cataloging components, API client, provider adapters, focus conventions, and Bootstrap utilities; no custom navigation framework. |
| Comprehensive testing | PASS | Add focused UI, provider, API, and service tests for route, keyboard, candidate results, covers, provider errors, and reset behavior. Reuse the existing browser smoke test; do not duplicate UI permutations in E2E. |
| UX consistency and accessibility | PASS | Keep focus behavior predictable, use existing visual patterns, and expose keyboard hints through localized text. |
| Click minimization | PASS | Preserve and reposition the existing new-book action; keep the scanner ready after reset and completion. |
| Legacy hardware performance | PASS | Keep provider calls sequential and individually bounded by configured timeouts; do not add heavyweight dependencies or animations. |
| Database versioning | PASS | No database changes are needed. |
| Research-first design | PASS | Compare BCD's scanner/provider patterns, Vue Router history guidance, text-search behavior across BnF, Google Books, and SUDOC, and Koha's documented record-then-item workflow in `research.md`. Record live PoC limitations separately from deterministic mocked tests. |
| Design-first implementation | PASS | `quickstart.md` records the compact layout, state flow, focus behavior, and manual acceptance walkthrough before implementation. |
| Internationalization | PASS | Add matching English and French keys for any keyboard guidance or UI text. |
| Quality gates | PASS | Run the feature analysis before implementation and verify the feature with automated tests after implementation. |

**Pre-research gate**: PASS. The requested behavior is bounded to the existing cataloging UI and has no unresolved requirements.  
**Post-design gate**: PASS. Design reuses existing APIs and storage, preserves the no-draft constraint, and defines keyboard and route behavior.

## Project Structure

### Documentation

```text
specs/015-cataloging-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cataloging-route.md
└── tasks.md
```

### Source Code

```text
src/bcd_web_vue/js/
├── pages/CatalogingPage.js
├── components/cataloging/
│   ├── FindNotice.js
│   ├── BibliographicForm.js
│   └── ItemBarcodeInput.js
├── router.js
└── locales/
    ├── en.json
    └── fr.json

src/bcd_api/
├── services/catalog/notice_lookup.py
├── services/external/
│   ├── bnf.py
│   ├── google_books.py
│   └── sudoc.py
└── utils/catalog_input.py

tests/js/
├── pages/cataloging/CatalogingPage.test.js
└── components/cataloging/FindNotice.test.js

tests/
├── integration/services/test_catalog_notice_lookup.py
└── unit/services/
    ├── test_bnf.py
    ├── test_google_books.py
    └── test_sudoc.py
```

**Structure Decision**: Keep the feature in the existing Vue cataloging page, domain components, router, locale files, and Vitest test tree. Add no new runtime module unless implementation reveals a shared route-state helper is genuinely needed.

## UX Design

At 1280×720, show a compact horizontal stepper immediately below the page heading, followed by the current step's content. Keep the existing new-book action in the heading/action row. Each step retains its existing primary action, placed with its input or form; in copy creation, the cover and record summary sit beside the barcode input rather than pushing the input below the fold. Existing-copy lists remain secondary to the active scan form. For a remote text search, show each candidate as a compact selectable card with a cover when available, title, author, publication details, and source; require an explicit selection.

```text
Cataloging                                      [New book]
[1 Find notice] — [2 Bibliographic details] — [3 Add copy]
Keyboard: Enter = current action; Escape = new book
┌─────────────────────────────────────────────────────────┐
│ Current step's essential content and primary action     │
│ Step 3: cover + record summary | copy barcode + Add     │
└─────────────────────────────────────────────────────────┘
Remote results (after local miss):
[cover] Title · Author · Year · BnF/Google Books/SUDOC [Use]
[cover] Title · Author · Year · BnF/Google Books/SUDOC [Use]
```

Navigation transitions:

```text
lookup?query=... -> bibliographic-form?query=...
                         | save notice
                         v
              bibliographic-form?record_id=... -> item-creation?record_id=...
```

Use browser history for step transitions. The saved notice and copies are reloaded from the catalog when navigating to their persisted steps. The current ISBN, ISSN, or text search value is the only unsaved value retained; remote result details, typed bibliographic fields, and unsaved copy fields are not restored. A text query's results are loaded only after an explicit search action. Escape and the existing new-book action replace the current URL with a clean lookup state and focus the scanner.

Remote text lookup reuses `/catalog/notices/lookup` one provider at a time, in BnF, Google Books, then SUDOC order, skipping disabled providers. A returned candidate list stays in the lookup component until the librarian explicitly chooses a record; the librarian can request the next provider when the current results are empty or unsuitable. Existing ISBN and ISSN single-result behavior remains unchanged. The existing browser smoke test remains the only browser-to-server journey test; candidate and failure permutations belong in Vitest and pytest.

## Complexity Tracking

No constitution violations or additional architectural complexity.
