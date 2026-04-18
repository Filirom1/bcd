# Feature 009 — Periodicals Management

**Branch**: `009-periodiques` | **Date**: 2026-04-17 | **Status**: Planning

---

## Problem

BCD4 currently has no proper periodicals workflow. The situation in production:

- **485 periodical records** imported from BiblioPuce in broken state:
  - `medium_type = 'Livre'` on all of them (BiblioPuce exports them as "Livre")
  - `isbn = NULL` on all of them (ISSN was lost during normalization — `"1163-7706"` → strip
    hyphen → `"11637706"` → 8 digits → rejected → `None`)
  - `total_items = 0` on all of them (counter not recalculated after bulk import)
- Scanning a magazine EAN-13 barcode from a kiosk (e.g. `9771163770025` for Wakou n° 274)
  returns 404 — the system doesn't know what to do with a `977...` EAN-13
- No way to record that a new issue has been received (no "bulletinage" workflow)
- In the Views and reports, periodicals show up as books with an empty Author field

---

## Data Migration Strategy

**Drop DB and reimport from BiblioPuce** — not production data, nothing to preserve.

This is possible because we simultaneously fix `bibliopuce_to_dublin_core.py` to detect
periodicals before import, so the 485 records will arrive correctly labelled this time.
No Alembic migration file is created — the model/schema changes take effect when the DB
is recreated from scratch via `alembic upgrade head`.

**Out of scope**: consolidating the 485 records into 1 record per title (Wakou 2023 +
Wakou 2024 + … → 1 Wakou parent). That requires a title-grouping heuristic and is a
separate planning exercise.

---

## Target Model

Based on study of BCDI, PMB and Koha (see TODO.md §10), the selected model is **Model B
(PMB-style)**:

```
bibliographic_record  (one per periodical title)
  isbn        = "issn:1163-7706"   ← reuses isbn field with issn: prefix
  title       = "Wakou"            ← title without issue number
  medium_type = "Périodique"
  publisher   = "Milan Presse"

item  (one per physical issue received)
  item_id     = "P0274"            ← barcode scanned from physical copy
  call_number = "274"              ← issue number typed by librarian; UI displays "n° 274"
  status      = available/on_loan/withdrawn
```

Circulation (checkout/return/holds) is **identical to books** — the item is what gets borrowed,
not the title record.

---

## User Workflows

### 1. Cataloguing a new periodical title (once per title)

**Via EAN-13 kiosk scan** (primary):
1. Librarian scans `9771163770025` from the magazine cover in ISBNLookup
2. System detects `977` prefix → extracts ISSN `1163-770X` → queries SUDOC
3. SUDOC returns: title "Wakou", publisher "Milan Presse"
4. Librarian fills the bibliographic form (pre-populated) → saves record
5. System moves to item creation step → librarian scans the physical barcode + types issue number

**Via ISSN manual entry** (fallback):
1. Librarian types `1163-7706` in ISBNLookup → system detects ISSN format → SUDOC lookup
2. Same flow as above from step 3

### 2. Recording a new issue (bulletinage — daily workflow)

1. Librarian opens Cataloguing page → scans EAN-13 of the new magazine
2. System finds the existing parent record (Wakou) → goes directly to item creation
3. Item creation form shows an extra field: **Issue number** (call_number) — required
4. Librarian scans the physical copy's barcode + types `274` → saves (UI shows "n° 274")
5. Item is immediately available for loan

### 3. Loan / Return

Identical to books — the physical copy (item) is scanned. Multiple issues of the same title
can be borrowed simultaneously by different borrowers.

---

## Scope

### In scope

| Area | What changes |
|------|-------------|
| Backend | Fix ISSN normalization, EAN-13 detection, `isbn:`/`issn:` prefix for all identifiers, `String(22)`, `total_items` counter, `export_service._format_isbn()`, `_download_cover()`, `bibliopuce_to_dublin_core.py` |
| API | No new endpoints — existing `POST /catalog/items` handles issue creation |
| Cataloguing UI | Item creation form gains `call_number` field when `medium_type = "Périodique"` |
| Catalog views | `call_number` column in record detail, ISSN label, publisher fallback |
| Circulation feedback | Show `title · call_number` instead of just `title` |
| Reports | Publisher fallback in Author column, medium_type filter in CREW report |
| Godot Kids | Same `title · call_number` display, publisher fallback in BookCard |

### Out of scope

| Feature | Reason |
|---------|--------|
| Data migration (485 records) | Destructive one-shot — plan separately |
| Scan-first from CirculationPage | Additional scope |
| Dashboard "recently received issues" widget | Low value |
| Periodical subscriptions / ordering | No budget concept in BCD4 |
| Issue prediction / routing lists | CDI/high school feature |
| Reliure (binding of back issues) | Not relevant at primary school scale |

---

## Key Design Decisions

**Identifier storage**: ALL identifiers stored with a prefix in the `isbn` column:
- Books: `isbn:9782070612758` — 18 chars (5 prefix + 13-digit ISBN-13)
- Periodicals: `issn:1163-7706` — 14 chars (5 prefix + 9-char ISSN with hyphen)
- Column resized: `String(17)` → `String(22)` / `max_length=22`, updated directly in the model
  (no Alembic migration needed — DB is dropped and recreated from BiblioPuce reimport)
- DB filter: `WHERE isbn LIKE 'issn:%'` for periodicals; `WHERE isbn LIKE 'isbn:%'` for books
- Unambiguous: `isbn:` = book, `issn:` = periodical (same convention as Dublin Core)

**No new API endpoints**: `POST /catalog/items` + `ItemCreate` (which already has
`call_number: Optional[str]`) is sufficient. The new `call_number` field was never shown
in the UI for books — we surface it conditionally for periodicals only.

**No `item_id` auto-generation**: the librarian always scans the physical barcode.
The item creation form already requires scanning.

**EAN-13 kiosk barcodes** (`977...`): handled in `lookup_isbn()` via a new private function
`_ean13_to_issn()`. No change to the ISBNLookup.js API call — the EAN-13 is passed
through as-is; the backend converts and returns the periodical metadata.
