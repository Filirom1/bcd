# Tasks: Aide Contextuelle Intégrée

**Input**: Design documents from `/specs/001-contextual-help/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks grouped by user story — each story can be implemented, tested, and demo'd independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and vendor the markdown library before any UI work can begin.

- [ ] T001 Create help content directory tree: `src/bcd_web_vue/help/fr/`, `src/bcd_web_vue/help/en/`, `src/bcd_web_vue/help/images/`
- [ ] T002 [P] Download marked.js v9 UMD build and save to `src/bcd_web_vue/vendor/js/marked.min.js` (source: `https://cdn.jsdelivr.net/npm/marked/marked.min.js` via `nix-shell -p curl`)
- [ ] T003 [P] Update `vendor.json` to add marked.js entry (read existing format first)
- [ ] T004 Update `src/bcd_web_vue/index.html` to add `<script src="/static/vendor/js/marked.min.js"></script>` after bootstrap.bundle script tag

**Checkpoint**: `marked` global is available in the browser console; directory tree exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: i18n keys, CSS, and the reusable `HelpPanel.js` component must exist before any page integration.

**⚠️ CRITICAL**: No user story page integration can begin until T008 (HelpPanel.js) is complete.

- [ ] T005 [P] Add `help.*` and `navigation.help` keys to `src/bcd_web_vue/locales/fr.json` (read current file first; add after `navigation` block): `help.button = "Aide"`, `help.loading`, `help.error`, `help.sections.{checkout,return,catalog,cataloging,borrowers,classes,reports,settings}` with French labels
- [ ] T006 [P] Add matching `help.*` and `navigation.help` keys to `src/bcd_web_vue/locales/en.json` (identical key structure, English values — 100% parity required per architecture patterns)
- [ ] T007 [P] Add `.help-markdown` CSS block to `src/bcd_web_vue/css/main.css` per plan.md Phase 1 CSS design: styles for `img`, `h2`, `blockquote`, `table`, `td/th`, `th` (read current end-of-file first to find insertion point)
- [ ] T008 Create `src/bcd_web_vue/js/components/ui/HelpPanel.js` per plan.md component design: props (`section` String required), `SECTION_FILES` map (8 sections × fr/en filenames), `fetchHelp()` with EN fallback, `renderedMarkdown` computed via `marked.parse()`, offcanvas template with `LoadingSpinner`, error alert, `v-html` body; watch `[section, locale]` with `immediate: true` (read `Modal.js` and `useAppState.js` as reference patterns before writing)

**Checkpoint**: Open browser console on any page — `marked.parse("# test")` returns HTML. Check `fr.json` and `en.json` have identical `help` key structure.

---

## Phase 3: User Story 1 — Aide sur la page Emprunter (Priority: P1) 🎯 MVP

**Goal**: A teacher on the checkout page can click "Aide" and see step-by-step French instructions with screenshots.

**Independent Test**: Open `/#/checkout`, click the "Aide" button in the page header, verify the offcanvas opens from the right with "Emprunter des livres" title and numbered steps. Close it — page state is unchanged.

- [ ] T009 [US1] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/CirculationPage.js`: import HelpPanel, add to `components`, add `helpSection = computed(() => props.mode === 'return' ? 'return' : 'checkout')` in setup(), place `<help-panel :section="helpSection" />` inside `.page-header > div.d-flex.gap-2` (read the full file before modifying)
- [ ] T010 [P] [US1] Create `src/bcd_web_vue/help/fr/emprunter.md` per help-markdown-format.md contract: H1 "Emprunter des livres", intro sentence, 3–4 numbered `## Étape N —` steps (saisir ID emprunteur, scanner code-barres, confirmer), screenshots via `/static/help/images/checkout-0N-*.png`, blockquote tips in "tu" form, `## Problèmes fréquents` table with ≥3 rows (limite atteinte, livre déjà emprunté, numéro non reconnu)
- [ ] T011 [P] [US1] Create `src/bcd_web_vue/help/en/checkout.md` per help-markdown-format.md contract: identical structure to emprunter.md in English, imperative form ("Click on…", "Scan the barcode…"), same screenshot paths (shared image set), "Common Issues" section

**Checkpoint**: US1 fully functional — checkout help panel opens, displays structured content, closes cleanly. Passes all 4 acceptance scenarios from spec.md US1.

---

## Phase 4: User Story 2 — Aide sur toutes les pages principales (Priority: P1)

**Goal**: All 8 main pages have a contextual "Aide" button showing page-specific step-by-step content.

**Independent Test**: Navigate to each of the 8 pages and verify: (1) "Aide" button appears in the page header, (2) the panel content is different and relevant to each page, (3) the panel closes automatically on navigation.

### Page Integrations (all parallelizable — different files)

- [ ] T012 [P] [US2] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/CatalogPage.js` with `section="catalog"` (read full file before modifying; same 3-step pattern as T009 without dynamic section)
- [ ] T013 [P] [US2] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/CatalogingPage.js` with `section="cataloging"`
- [ ] T014 [P] [US2] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/BorrowersPage.js` with `section="borrowers"`
- [ ] T015 [P] [US2] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/ClassesPage.js` with `section="classes"`
- [ ] T016 [P] [US2] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/ReportsPage.js` with `section="reports"`
- [ ] T017 [P] [US2] Integrate `HelpPanel` in `src/bcd_web_vue/js/pages/SettingsPage.js` with `section="settings"`

### Return page help content

- [ ] T018 [P] [US2] Create `src/bcd_web_vue/help/fr/retourner.md`: saisir ID emprunteur, liste prêts affichée, cliquer pour retourner chaque livre, retard affiché — screenshots `return-0N-*.png`, `## Problèmes fréquents` table
- [ ] T019 [P] [US2] Create `src/bcd_web_vue/help/en/return.md`: English equivalent of retourner.md

### Catalog page help content

- [ ] T020 [P] [US2] Create `src/bcd_web_vue/help/fr/catalogue.md`: recherche par titre/auteur/ISBN, lire disponibilité, fiche détail, historique des prêts — screenshots `catalog-0N-*.png`
- [ ] T021 [P] [US2] Create `src/bcd_web_vue/help/en/catalog.md`: English equivalent of catalogue.md

### Cataloging page help content

- [ ] T022 [P] [US2] Create `src/bcd_web_vue/help/fr/catalogage.md`: saisir ISBN, résultat BNF automatique, créer manuellement si sans ISBN, scanner code-barres du livre — screenshots `cataloging-0N-*.png`
- [ ] T023 [P] [US2] Create `src/bcd_web_vue/help/en/cataloging.md`: English equivalent of catalogage.md

### Borrowers page help content

- [ ] T024 [P] [US2] Create `src/bcd_web_vue/help/fr/eleves.md`: liste des élèves, filtrer par classe, fiche élève, prêts en cours, bloquer/débloquer, importer CSV — screenshots `borrowers-0N-*.png`
- [ ] T025 [P] [US2] Create `src/bcd_web_vue/help/en/borrowers.md`: English equivalent of eleves.md

### Classes page help content

- [ ] T026 [P] [US2] Create `src/bcd_web_vue/help/fr/classes.md`: liste des classes, voir les élèves par classe, imprimer les cartes — screenshot `classes-01-list.png`
- [ ] T027 [P] [US2] Create `src/bcd_web_vue/help/en/classes.md`: English equivalent of classes.md

### Reports page help content

- [ ] T028 [P] [US2] Create `src/bcd_web_vue/help/fr/rapports.md`: rapport retards (groupé par classe), livres les plus empruntés, jamais empruntés, imprimer/exporter — screenshots `reports-0N-*.png`
- [ ] T029 [P] [US2] Create `src/bcd_web_vue/help/en/reports.md`: English equivalent of rapports.md

### Settings page help content

- [ ] T030 [P] [US2] Create `src/bcd_web_vue/help/fr/parametres.md`: durée de prêt, limite par emprunteur, format ID, renouvellements maximum, paramètres réseau — screenshot `settings-01-main.png`
- [ ] T031 [P] [US2] Create `src/bcd_web_vue/help/en/settings.md`: English equivalent of parametres.md

**Checkpoint**: Navigate to all 8 pages — each shows "Aide" button. Open help on Catalogue then on Élèves — content is different. Navigate away from an open panel — panel closes automatically.

---

## Phase 5: User Story 3 — Aide bilingue FR/EN (Priority: P2)

**Goal**: When the interface is in English, help content is in English; locale switch updates the panel in real time without closing it.

**Independent Test**: Set interface to English (toggle in UI), open help on any page — content is in English. Switch back to French while panel is open — content switches to French without closing.

> **Note**: The HelpPanel locale-watch behavior is already implemented in T008. All EN markdown files were created in T010–T011 and T019–T031. This phase validates the end-to-end bilingual behavior and adds the resilience E2E test.

- [ ] T032 [US3] Create `tests/e2e/test_help_panel.py` with these 7 Playwright test cases (read `tests/e2e/` existing tests for fixture patterns): `test_help_panel_opens_on_checkout_page`, `test_help_panel_content_is_checkout_specific`, `test_help_panel_closes_on_dismiss`, `test_help_panel_updates_on_language_switch` (verifies panel content changes when locale toggled while open), `test_help_panel_shows_error_when_content_missing` (mock missing file → verify error alert, not crash), `test_all_8_pages_have_help_button`, `test_help_panel_closes_on_navigation`

**Checkpoint**: `pytest tests/e2e/test_help_panel.py -v` passes all 7 tests. Manual: toggle FR↔EN while panel is open — content switches.

---

## Phase 6: User Story 4 — Captures avec données réalistes (Priority: P2)

**Goal**: Screenshots embedded in help content show real named students, real book titles, real loan dates — not empty pages.

**Independent Test**: Run `python scripts/reset_and_simulate.py` and verify via SQLite queries that all 7 FR-009 scenarios are present. Run `python scripts/generate_help_screenshots.py` and verify 21 PNG files appear in `src/bcd_web_vue/help/images/` showing recognizable data.

- [ ] T033 [US4] Add `create_teachers_and_staff(session, classes)` function to `scripts/reset_and_simulate.py` (read full file first; append after existing functions, call from `main()`): creates 1 teacher per class (role=TEACHER, class_id assigned), 1 directeur (role=STAFF), 2 manually blocked borrowers (active=False, blocked_reason set), 3 active loans for one teacher; prints `✓ Created teachers and staff (N borrowers)`
- [ ] T034 [US4] Add `diversify_item_statuses(session)` function to `scripts/reset_and_simulate.py`: marks 3 items → `status='in_repair', loanable=False`; marks 2 items → `status='lost'`; marks 1 item → `loanable=False` (reference); selects only from items not currently on loan; prints `✓ Diversified item statuses (N lost, N in_repair)`
- [ ] T035 [US4] Add `create_demo_holds(session, today)` function to `scripts/reset_and_simulate.py`: Hold A (`waiting`, queue_position=1, on an on-loan item), Hold B (`ready`, expiration_date=today+2, on available item), Hold C (`waiting`, queue_position=2, same bibliographic_record as A), Hold D (`expired`); all use real borrower/item IDs from DB; prints `✓ Created demo holds (waiting: N, ready: N)`
- [ ] T036 [US4] Add `create_demo_current_loans(session, today)` function to `scripts/reset_and_simulate.py`: Loan X (due_date=today-5, overdue), Loan Y (due_date=today), Loan Z (due_date=today+2), Loan W (renewal_count=1, due_date=today+7), Loan V (renewal_count=2, due_date=today+14); update item status to `on_loan` after insert; prints `✓ Created demo current loans (overdue: N, renewed: N, at-limit: N)`
- [ ] T037 [US4] Create `scripts/generate_help_screenshots.py` per plan.md screenshot script design and screenshot-naming.md contract: `async get_demo_data(db_path)` queries SQLite for active_borrower_id, overdue_borrower_id, at_limit_borrower_id, available_item_barcode, detail_record_id; `async capture_screenshots(base_url, demo, output_dir)` captures all 21 PNGs from screenshot-naming.md inventory (1280×800px, Chromium headless, fr-FR locale, networkidle wait); verifies server available at startup; continues on individual capture failure; prints final summary with counts

**Checkpoint**: Run `python scripts/reset_and_simulate.py` → output includes all 4 `✓` lines. Run quickstart.md verification SQLite script → all 7 scenario counts are `> 0`. Run screenshot script with server → 21 PNGs in `help/images/`.

---

## Phase 7: User Story 5 — Régénération sans intervention (Priority: P3)

**Goal**: An admin can re-run the screenshot script at any time after updating the DB; the script handles failures gracefully and reports clearly.

**Independent Test**: Run `python scripts/generate_help_screenshots.py` — when one page fails, the script logs the failure and continues; final exit code is 1 if any failure, 0 if all succeed; output lists successes and failures counts.

- [ ] T038 [US5] Verify `scripts/generate_help_screenshots.py` fully satisfies all 7 script behavior contract points from `specs/001-contextual-help/contracts/screenshot-naming.md`: (1) server health check with clear error on failure, (2) DB query for real IDs, (3) continue-on-failure per capture, (4) final summary report, (5) fixed output directory `src/bcd_web_vue/help/images/`, (6) overwrite without confirmation, (7) exit code 0/1 based on success count — add any missing behavior from T037
- [ ] T039 [US5] Add `--help` / `--db-path` / `--base-url` CLI arguments to `scripts/generate_help_screenshots.py` using `argparse` so the script self-documents its usage (`python scripts/generate_help_screenshots.py --help` prints usage)

**Checkpoint**: `python scripts/generate_help_screenshots.py --help` prints usage. Deliberately point at a non-existent server URL — script exits with a clear "Server not reachable" message, not a Python traceback.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration check, help images referenced in markdown files, quickstart validation.

- [ ] T040 Verify all markdown files in `src/bcd_web_vue/help/fr/` and `src/bcd_web_vue/help/en/` reference only image paths that exist in `src/bcd_web_vue/help/images/` (run `python scripts/generate_help_screenshots.py` first if images missing); fix any broken image references
- [ ] T041 Run the full quickstart.md validation sequence end-to-end: `python scripts/reset_and_simulate.py` → start server → `python scripts/generate_help_screenshots.py` → open each of the 8 help pages → verify panel opens with content and screenshots → toggle FR↔EN → `pytest tests/e2e/test_help_panel.py -v`
- [ ] T042 [P] Update `specs/001-contextual-help/plan.md` Phase 2 section to record tasks.md creation as complete; add any implementation notes that deviated from the plan

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation: T005–T008) — BLOCKS all page integrations
    ↓
Phase 3 (US1 MVP) — validates core help panel concept
    ↓
Phase 4 (US2) — extends to all pages (T012–T017 parallelizable; T018–T031 parallelizable)
    ↓
Phase 5 (US3) — bilingual E2E test (content already created in US1/US2)
    ↓ ← Phase 6 can start in parallel with Phase 5 (no shared files)
Phase 6 (US4) — simulation enrichment and screenshot generation
    ↓
Phase 7 (US5) — script resilience polish
    ↓
Phase 8 (Polish) — final integration check
```

### Key Within-Phase Dependencies

- T004 depends on T002 (marked.min.js must exist before index.html update)
- T008 depends on T005, T006 (i18n keys must exist for `t('help.*')` calls)
- T009–T017 all depend on T008 (HelpPanel.js must exist)
- T033–T036 are independent of each other (append to different function slots)
- T037 depends on T033–T036 (screenshot script needs all simulation scenarios)
- T038–T039 depend on T037 (polishing the script created in T037)
- T040 depends on T037 (images must exist to verify references)

### User Story Dependencies

| Story | Phase | Depends on | Can parallelize with |
|-------|-------|------------|---------------------|
| US1 (P1) | Phase 3 | Phase 1 + Phase 2 | — |
| US2 (P1) | Phase 4 | US1 complete | — |
| US3 (P2) | Phase 5 | US1 + US2 content | US4 Phase 6 |
| US4 (P2) | Phase 6 | Phase 1 only (script) | US3 Phase 5 |
| US5 (P3) | Phase 7 | US4 complete | — |

---

## Parallel Execution Examples

### Phase 4 — All page integrations in parallel (T012–T017)

```
Task: "Integrate HelpPanel in CatalogPage.js"        → T012
Task: "Integrate HelpPanel in CatalogingPage.js"     → T013
Task: "Integrate HelpPanel in BorrowersPage.js"      → T014
Task: "Integrate HelpPanel in ClassesPage.js"         → T015
Task: "Integrate HelpPanel in ReportsPage.js"         → T016
Task: "Integrate HelpPanel in SettingsPage.js"        → T017
```

### Phase 4 — All markdown files in parallel (T018–T031)

```
Task: "Create retourner.md + return.md"               → T018 + T019
Task: "Create catalogue.md + catalog.md"              → T020 + T021
Task: "Create catalogage.md + cataloging.md"          → T022 + T023
Task: "Create eleves.md + borrowers.md"               → T024 + T025
Task: "Create classes.md (FR+EN)"                     → T026 + T027
Task: "Create rapports.md + reports.md"               → T028 + T029
Task: "Create parametres.md + settings.md"            → T030 + T031
```

### Phase 6 — Simulation functions in parallel (T033–T036)

```
Task: "Add create_teachers_and_staff()"               → T033
Task: "Add diversify_item_statuses()"                 → T034
Task: "Add create_demo_holds()"                       → T035
Task: "Add create_demo_current_loans()"               → T036
```

---

## Implementation Strategy

### MVP First (US1 only — Phases 1–3)

1. Complete Phase 1 (Setup): create directories, vendor marked.js
2. Complete Phase 2 (Foundation): i18n keys, CSS, HelpPanel.js
3. Complete Phase 3 (US1): CirculationPage + emprunter.md + checkout.md
4. **STOP AND VALIDATE**: Teacher can open help on `/checkout`, read step-by-step FR instructions
5. Demo to stakeholders — core concept is proven

### Incremental Delivery

1. Setup + Foundation → HelpPanel component ready
2. Add US1 → Checkout help functional (MVP demo)
3. Add US2 → All 8 pages have contextual help (full feature demo)
4. Add US3 → Bilingual E2E tests confirm locale switching
5. Add US4 → Screenshots show real data (visual quality upgrade)
6. Add US5 → Admin can regenerate screenshots autonomously
7. Polish → All integration verified end-to-end

### Key Files to Read Before Each Phase

| Phase | Files to Read First |
|-------|-------------------|
| T008 (HelpPanel.js) | `src/bcd_web_vue/js/components/ui/Modal.js`, `src/bcd_web_vue/js/composables/useAppState.js` |
| T009–T017 (page integrations) | Each target page file in full |
| T033–T036 (simulation) | Full `scripts/reset_and_simulate.py` |
| T037 (screenshot script) | `scripts/take_screenshots.py` (existing pattern), `specs/001-contextual-help/contracts/screenshot-naming.md` |
| T032 (E2E tests) | `tests/e2e/` existing test files for fixture patterns |

---

## Task Summary

| Phase | Story | Count | Parallelizable |
|-------|-------|-------|---------------|
| Phase 1: Setup | — | 4 | 2 of 4 |
| Phase 2: Foundation | — | 4 | 3 of 4 |
| Phase 3: US1 (P1) | checkout help | 3 | 2 of 3 |
| Phase 4: US2 (P1) | all 8 pages | 20 | 18 of 20 |
| Phase 5: US3 (P2) | bilingual E2E | 1 | 0 of 1 |
| Phase 6: US4 (P2) | screenshots | 5 | 4 of 5 |
| Phase 7: US5 (P3) | script resilience | 2 | 0 of 2 |
| Phase 8: Polish | — | 3 | 1 of 3 |
| **Total** | | **42** | **30 of 42** |

---

## Notes

- `[P]` tasks touch different files — safe to run in parallel
- Each user story phase is independently completable and demonstrable
- Help content (markdown files) follows `specs/001-contextual-help/contracts/help-markdown-format.md` strictly — read the contract before writing any `.md` file
- Screenshot paths in markdown must use `/static/help/images/` prefix (not relative paths)
- FR and EN locale files must have 100% identical key structure (architecture pattern §8)
- Screenshots can reference placeholder paths (`/static/help/images/checkout-01-empty.png`) before images exist — browser handles missing images gracefully per FR-011
- Commit after each phase checkpoint, not after every individual task
