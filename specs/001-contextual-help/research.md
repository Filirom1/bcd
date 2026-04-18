# Research: Aide Contextuelle Intégrée

**Feature**: 001-contextual-help
**Date**: 2026-03-27

---

## Decision 1 — Markdown Renderer Library

**Decision**: Use `marked.js` v9+ (UMD global build) vendored at `src/bcd_web_vue/vendor/js/marked.min.js`

**Rationale**:
- The project uses vendored global builds (no npm, no bundler) — marked is one of the few libraries that provides a clean UMD/IIFE build exposing a global `marked` variable
- `marked.parse(str)` is the only API needed; ~50KB minified
- Actively maintained (updated March 2026), battle-tested in millions of projects
- Alternative `markdown-it` is also strong but adds ~80KB with no benefit for this use case
- Alternative: rendering markdown server-side (Python `mistune`) would require a new API endpoint and break offline capability — rejected

**Alternatives Considered**:
| Library | Size | Verdict |
|---------|------|---------|
| marked.js | ~50KB | ✅ Chosen |
| markdown-it | ~80KB | ❌ Larger, no benefit |
| showdown.js | ~45KB | ❌ Less maintained |
| Custom parser | ~200 lines | ❌ Violates Principle II |
| Server-side (Python) | N/A | ❌ Requires API + breaks offline |

**Vendoring approach**: Copy `marked.min.js` from jsDelivr (`https://cdn.jsdelivr.net/npm/marked@9/marked.min.js`) to `vendor/js/`. No `vendor.json` exists in the project — vendoring is manual. Add `<script src="/static/vendor/js/marked.min.js"></script>` in `index.html` before `app.js`.

**marked.js safety**: Since content is developer-authored (clarification Q1), no HTML sanitization is required. The `marked` global is configured with default options (gfm: true).

---

## Decision 2 — Panel UI Pattern: Bootstrap Offcanvas

**Decision**: Use Bootstrap 5.3 offcanvas from the right side (`offcanvas-end`), initialized programmatically following the existing `Modal.js` pattern

**Rationale**:
- Bootstrap 5.3 offcanvas is already included in `bootstrap.bundle.min.js` (vendored) — zero additional JS cost
- Modal.js in the codebase demonstrates the exact pattern: `ref()` on DOM element → `new bootstrap.Offcanvas(element)` → `watch()` on reactive state
- Offcanvas does not block the underlying page content (unlike Modal) — teachers can refer to the page while reading help
- Alternative slide-in CSS animation would require ~100 lines of custom CSS + JS — violates Principle II

**Offcanvas ID strategy**: Use a fixed `id="bcd-help-offcanvas"` — since Vue renders only one page at a time, no ID collision occurs.

**Width**: Fixed at 480px on desktop; falls back to 100vw at Bootstrap's `sm` breakpoint via media query (already handled by Bootstrap).

**Alternatives Considered**:
| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Bootstrap Offcanvas | In bundle, no JS, responsive | Requires Bootstrap | ✅ Chosen |
| Custom CSS drawer | Full control | Custom CSS + JS, Principle II violation | ❌ |
| Bootstrap Modal | Already used | Blocks page, poor UX | ❌ |
| Floating panel (absolute) | No framework needed | Complex z-index, mobile issues | ❌ |

---

## Decision 3 — Content Loading: Static Fetch vs. Embedded vs. API

**Decision**: Lazy `fetch('/static/help/{locale}/{file}.md')` triggered on panel open (not at page load)

**Rationale**:
- Static files are already served under `/static/` (FastAPI `StaticFiles` mount on `src/bcd_web_vue/`)
- No new API endpoint needed — help files at `src/bcd_web_vue/help/fr/*.md` become `/static/help/fr/*.md`
- Lazy fetch (on click only, not on route change) respects Constitution VI (legacy hardware, no wasted downloads)
- FR→EN fallback handled by catching fetch errors and retrying with `en` locale
- Alternative: embed markdown in JS files — would bundle into component, not editable without redeploy, defeats the purpose

**Caching**: Browser caches fetched markdown after first load per session (standard HTTP cache). No additional caching needed.

**Alternatives Considered**:
| Approach | Verdict |
|----------|---------|
| Lazy fetch from `/static/` | ✅ Chosen |
| Embedded in locale JSON | ❌ JSON becomes huge, hard to edit |
| Embedded in JS component | ❌ No editability, no separation |
| Dedicated FastAPI `/help/*` endpoint | ❌ Unnecessary complexity |

---

## Decision 4 — Screenshot Generation: Playwright Interaction Pattern

**Decision**: New script `scripts/generate_help_screenshots.py` — reuses Playwright (already in dev dependencies), queries SQLite directly for real IDs, takes ~21 targeted screenshots including interaction-based ones

**Rationale**:
- Playwright already used in `tests/e2e/` and `scripts/take_screenshots.py` — reuse, don't duplicate
- Direct SQLite query at script start gives real borrower/item IDs without API calls
- The existing `take_screenshots.py` only captures empty page states — help screenshots need populated states (borrower loaded, items scanned)
- Screenshots saved to `src/bcd_web_vue/help/images/` (served at `/static/help/images/`) — no new server config

**Interaction pattern for state-based screenshots**:
1. Navigate to page
2. Fill input fields with real IDs (type via `page.fill()`)
3. Wait for API response (network idle or specific selector)
4. Screenshot

**Naming convention**: `{section}-{nn}-{state}.png` (e.g., `checkout-02-borrower-loaded.png`)

---

## Decision 5 — Simulation Enrichment Strategy

**Decision**: Add 4 new focused functions to `reset_and_simulate.py`, called sequentially after the existing `simulate_activity()`:
- `create_teachers_and_staff()` — roles, higher limits
- `diversify_item_statuses()` — lost, in_repair, non-loanable
- `create_demo_holds()` — waiting, ready, expired holds
- `create_demo_current_loans()` — overdue, due-today, renewed, at-limit states

**Rationale**:
- Non-destructive additions: existing simulation logic unchanged, new functions inject specific edge-case states
- Each function is independently testable
- Functions use existing SQLAlchemy session pattern (no new dependencies)
- Ensure screenshot script always finds valid data by setting specific, predictable states

**FR-009 scenario coverage**:
| Scenario | Function |
|----------|----------|
| Prêts actifs en retard | `create_demo_current_loans()` |
| Élèves bloqués manuellement | `create_teachers_and_staff()` + student modifications |
| Réservations en attente (waiting) | `create_demo_holds()` |
| Réservations prêtes à retirer (ready) | `create_demo_holds()` |
| Articles en réparation | `diversify_item_statuses()` |
| Prêts renouvelés | `create_demo_current_loans()` |
| Enseignants avec plusieurs livres | `create_teachers_and_staff()` |

---

## Decision 6 — i18n Keys Placement

**Decision**: Add `help.*` keys to existing `fr.json` and `en.json` locale files, under a new top-level `"help"` key

**Rationale**: Follows existing pattern (all UI strings in these files). The help panel button label and section titles need translation. The actual help content (the markdown prose) is in separate files, not in locale JSON.

**New keys (fr.json)**:
```json
"navigation": { ..., "help": "Aide" },
"help": {
    "button": "Aide",
    "loading": "Chargement de l'aide…",
    "error": "Aide non disponible pour cette page.",
    "sections": {
        "checkout":   "Emprunter des livres",
        "return":     "Retourner des livres",
        "catalog":    "Rechercher dans le catalogue",
        "cataloging": "Ajouter des livres",
        "borrowers":  "Gérer les élèves",
        "classes":    "Gérer les classes",
        "reports":    "Rapports et statistiques",
        "settings":   "Paramètres"
    }
}
```
