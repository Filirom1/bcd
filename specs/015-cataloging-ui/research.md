# Research: Fast Cataloging Workflow

## Existing BCD behavior

- `CatalogingPage.js` already coordinates lookup, bibliographic entry, and copy creation; the feature can refine the existing flow without introducing a second workflow.
- `FindNotice.js` already submits scanner input on Enter and focuses the lookup field when mounted. Preserve this pattern and pass the retained ISBN back into that field when returning to lookup.
- BCD uses Vue Router hash history. The URL fragment is therefore the right place for non-sensitive workflow identifiers and does not require server-side URL routing changes.
- The bibliographic notice and each copy are saved through existing catalog operations. The browser history must only navigate; it must never delete or undo those records.
- `BibliographicForm.js` already has cover preview behavior. The copy step currently does not receive the cover, so pass the persisted record's cover into that existing workflow rather than adding a second cover lookup.
- The local notice search already accepts free text and enriches local matches for selection. It intentionally returns before calling a remote source when local matches exist.
- The existing `/catalog/notices/lookup` endpoint checks the local catalog again, honors each source's enabled/timeout settings, and returns a single match for ISBN/ISSN lookups. Extend this contract for text candidates rather than adding a new endpoint.
- Google Books parsing already returns `cover_url` and has title-search machinery. BnF's SRU query supports `bib.title all "..."`; a live query for "Le Petit Prince" returned a bounded set when `maximumRecords` was supplied.

## Comparable workflow: Koha

Koha's official cataloging manual describes a bibliographic record as the main record, with item records attached after bibliographic information is saved. Its documented flow separates record creation/import from item attachment and keeps cataloging actions at the top of the module.

- Source: [Koha 23.11 manual - Cataloging](https://koha-community.org/manual/23.11/en/html/cataloging.html)
- Adopt: keep the bibliographic notice and physical copy as distinct, ordered steps; allow an existing notice to go directly to copy creation.
- Improve for BCD: prioritize a fast scanner-ready flow, a visible compact stepper, keyboard operation, and browser history for returning to saved data.

## Navigation and URL behavior

Vue Router documents that `router.push` adds a history entry, `router.replace` replaces the current entry, and query values can be passed as a location descriptor. Its hash mode stores the client-side route after `#`, which fits BCD's current deployment without requiring server fallback configuration.

- Sources: [Vue Router - Programmatic Navigation](https://router.vuejs.org/guide/essentials/navigation.html), [Vue Router - History Modes](https://router.vuejs.org/guide/essentials/history-mode.html)
- Decision: push when moving between meaningful workflow steps; replace when canonicalizing a step after saving or clearing the workflow.
- Rationale: this makes Back/Forward meaningful while avoiding an extra unsaved form entry after its notice has been committed.
- Alternative rejected: local-only step state, because it cannot be restored by browser Back/Forward or linked in the URL.
- Alternative rejected: serializing form fields, because the user explicitly chose not to keep a draft and persisted records must remain the source of truth.

## Remote text search

The local database remains first. When a free-text query has no local match, the enabled sources are searched sequentially in BnF, Google Books, then SUDOC order. Provider calls use the existing per-source timeouts. The UI shows candidates as soon as one source returns them, and a librarian can explicitly start the next source if those candidates are not suitable. This avoids waiting for every provider before the user can act.

- BnF evidence: the project's BnF SRU endpoint accepted `bib.title all "Le Petit Prince"` and returned matching MARC records; the first result was a diagnostic record and must be discarded. A capped `maximumRecords` keeps result parsing bounded.
- Google Books evidence: `external/google_books.py` already maps titles, authors, publisher/year, ISBN, and thumbnail into BCD's bibliographic format; the existing text query implementation can be extended to return ranked candidates instead of only one best match.
- SUDOC evidence: `external/sudoc.py` already supports title/author SRU queries and parses Pica+ records, but its current helper returns only one best candidate and does not provide covers.
- Live PoC status: Google Books returned HTTP 429 and SUDOC reset the connection during the previous probe, so those probes were inconclusive rather than evidence that text search is unsupported. Automated tests must use mocked provider responses and must not depend on these external services being reachable.
- Decision: text searches return at most 10 title candidates per provider, never auto-select a candidate, and display available `cover_url` or local cover references.
- Rationale: explicit selection prevents a fuzzy title match from silently creating the wrong edition; showing available covers improves disambiguation.
- Alternatives considered: automatically pick the highest-scoring candidate (rejected because similar titles/editions are common); wait for both providers before rendering (rejected because it adds avoidable sequential latency); query SUDOC for book titles (rejected because SUDOC is retained for its existing ISSN/periodical route).

## Keyboard and focus behavior

BCD's documented barcode pattern handles Enter at form submission, clears the scanner input, and returns focus to the scanner. Keep Enter contextual to the active step's existing submit action. Handle Escape only within the cataloging page so it does not collide with global shortcuts or other screens. Focus the lookup field after Escape, the existing new-book action, or successful completion of the copy step.

- Source: `.specify/architecture-patterns.md`, Vue 3 Web UI Patterns, Barcode Scanner Support.
- Decision: no global Enter/Escape shortcut registration; use component/page-scoped behavior and existing input submission.

## Decisions

1. Keep the existing Vue components and catalog persistence; extend the existing source lookup response, but add no endpoint or migration.
2. Encode only `step`, the active ISBN/ISSN/text query, and `record_id` once a notice is persisted.
3. Reload persisted notice/copy data from the catalog on route restoration; never represent unsaved fields as persisted state.
4. Reposition existing controls, show covers from available record/provider data, and present remote candidates for explicit selection.
5. Add any new UI strings to both English and French locale files.
6. Keep provider tests deterministic with mocked HTTP responses; the previous Google Books and SUDOC live PoCs were inconclusive and must not gate ordinary test runs.
