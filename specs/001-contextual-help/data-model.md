# Data Model: Aide Contextuelle Intégrée

**Feature**: 001-contextual-help
**Date**: 2026-03-27

> Note: This feature introduces no database schema changes. Entities below are logical file-system constructs.

---

## Entities

### HelpSection (file-based)

Represents one section of the contextual help, in one language.

| Attribute | Type | Description |
|-----------|------|-------------|
| `section_id` | string | Page identifier — one of: `checkout`, `return`, `catalog`, `cataloging`, `borrowers`, `classes`, `reports`, `settings` |
| `locale` | string | `fr` or `en` |
| `filename` | string | Markdown filename (locale-specific, e.g., `emprunter.md` for FR checkout) |
| `file_path` | path | `src/bcd_web_vue/help/{locale}/{filename}` |
| `http_url` | string | `/static/help/{locale}/{filename}` |
| `title` | string | Human title (from i18n key `help.sections.{section_id}`) |
| `screenshots` | HelpScreenshot[] | Associated captures referenced in the markdown |

**Identity**: `(section_id, locale)` — unique

**Validation rules**:
- `section_id` MUST be one of the 8 known values (enforced by `SECTION_FILES` map in `HelpPanel.js`)
- Markdown file MUST exist for FR; EN is fallback if FR missing
- File encoding: UTF-8

**Section → file mapping**:

| section_id | FR filename | EN filename |
|------------|-------------|-------------|
| checkout | emprunter.md | checkout.md |
| return | retourner.md | return.md |
| catalog | catalogue.md | catalog.md |
| cataloging | catalogage.md | cataloging.md |
| borrowers | eleves.md | borrowers.md |
| classes | classes.md | classes.md |
| reports | rapports.md | reports.md |
| settings | parametres.md | settings.md |

---

### HelpScreenshot (file-based)

A PNG capture illustrating one step in a help section.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | string | Descriptive filename without extension |
| `section_id` | string | Parent section |
| `step_number` | integer | Step within the section (01–99) |
| `state_slug` | string | Short description of state captured (e.g., `borrower-loaded`, `overdue-warning`) |
| `file_path` | path | `src/bcd_web_vue/help/images/{name}.png` |
| `http_url` | string | `/static/help/images/{name}.png` |
| `resolution` | string | 1280×800px (fixed, set in Playwright browser context) |
| `format` | string | PNG (full resolution, no compression — per clarification Q2) |

**Naming convention**: `{section_id}-{step_number:02d}-{state_slug}.png`
- Example: `checkout-02-borrower-loaded.png`
- Example: `reports-01-overdue-by-class.png`

**Full screenshot inventory**:

| Filename | Section | Description |
|----------|---------|-------------|
| `checkout-01-empty.png` | checkout | Empty checkout page |
| `checkout-02-borrower-loaded.png` | checkout | Borrower card loaded after ID entry |
| `checkout-03-item-scanned.png` | checkout | 1 item added to checkout list |
| `checkout-04-loan-limit.png` | checkout | Loan limit warning |
| `return-01-empty.png` | return | Empty return page |
| `return-02-borrower-loans.png` | return | Borrower with active loans displayed |
| `return-03-overdue-warning.png` | return | Overdue warning on return page |
| `catalog-01-search.png` | catalog | Catalog search empty |
| `catalog-02-results.png` | catalog | Search results with availability |
| `catalog-03-detail.png` | catalog | Book detail with on-loan copies |
| `cataloging-01-isbn.png` | cataloging | ISBN lookup form |
| `cataloging-02-filled.png` | cataloging | Form filled after BNF lookup |
| `borrowers-01-list.png` | borrowers | Borrower list with classes |
| `borrowers-02-detail.png` | borrowers | Borrower detail with active loans |
| `borrowers-03-blocked.png` | borrowers | Blocked borrower detail |
| `classes-01-list.png` | classes | Class list |
| `reports-01-overdue.png` | reports | Overdue report grouped by class |
| `reports-02-most-borrowed.png` | reports | Most borrowed chart |
| `reports-03-never-borrowed.png` | reports | Never borrowed list |
| `settings-01-main.png` | settings | Settings form |
| `printing-01-cards.png` | printing | Print student cards (for help reference only) |

---

### SimulationScenario (database states)

Specific database states created by enriched `reset_and_simulate.py` to ensure screenshot realism.

| Scenario ID | Description | Created by |
|-------------|-------------|------------|
| `overdue-loan` | At least 1 active loan with `due_date < today` | `create_demo_current_loans()` |
| `blocked-borrower` | At least 1 borrower with `active=False`, `blocked_reason` set | `import_students()` or `create_demo_current_loans()` |
| `hold-waiting` | At least 1 Hold with `status='waiting'`, `queue_position=1` | `create_demo_holds()` |
| `hold-ready` | At least 1 Hold with `status='ready'`, `expiration_date=today+2` | `create_demo_holds()` |
| `item-in-repair` | At least 2 Items with `status='in_repair'`, `loanable=False` | `diversify_item_statuses()` |
| `renewed-loan` | At least 1 active loan with `renewal_count >= 1` | `create_demo_current_loans()` |
| `teacher-with-loans` | At least 1 teacher borrower with 3 active loans | `create_teachers_and_staff()` |
| `loan-due-today` | At least 1 active loan with `due_date = today` | `create_demo_current_loans()` |
| `loan-due-soon` | At least 1 active loan with `due_date = today + 2` | `create_demo_current_loans()` |

---

## State Transitions

### HelpPanel visibility

```
[CLOSED] --(user clicks "Aide" button)--> [LOADING] --(fetch success)--> [OPEN]
                                                      --(fetch error)---> [OPEN with error msg]
[OPEN] --(user clicks close / backdrop / ESC)--> [CLOSED]
[OPEN] --(user navigates to another page)--> [CLOSED]
[OPEN] --(locale changes)--> [LOADING] --(fetch success)--> [OPEN with new language]
```

### Screenshot generation

```
[START] --> [DB query for real IDs] --> [For each screenshot:]
    --> [Navigate to page] --> [Apply interactions if needed]
    --> [Wait for selector/networkidle] --> [Capture PNG]
    --> [Log success or failure]
[END] --> [Report: N captured, M failed]
```
