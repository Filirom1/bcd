# Data Model: Circulation History — Pagination and Performance

**Feature**: 007-circulation-history
**Date**: 2026-03-26

---

## Existing Models (no schema changes)

### CirculationTransaction (existing)

No new columns are added. One missing index is added via migration.

| Column | Type | Indexed | Notes |
|--------|------|---------|-------|
| `id` | Integer PK | ✅ | Auto-increment |
| `borrower_id` | Integer FK | ✅ | References `borrower.id` |
| `item_id` | Integer FK | ✅ | References `item.id` |
| `bibliographic_record_id` | Integer FK | — | References `bibliographic_record.id` |
| `checkout_date` | DateTime | ✅ | Used for sort order and date range filter |
| `due_date` | Date | — | Displayed in history rows |
| `return_date` | DateTime nullable | **🆕 Add index** | NULL = active loan; NOT NULL = completed |
| `status` | String(20) | — | ACTIVE / RETURNED / RENEWED |
| `renewal_count` | Integer | — | Number of renewals |
| `checked_out_by` | String(100) nullable | — | Librarian name at checkout |
| `returned_by` | String(100) nullable | — | Librarian name at return |
| `notes` | Text nullable | — | Optional notes |
| `created_at` | DateTime | — | Audit timestamp |
| `updated_at` | DateTime | — | Audit timestamp |

**Migration required**: Add `index=True` to `return_date` column.
Migration file: `migrations/versions/XXX_add_return_date_index.py`

---

## New API Response Schemas

### PaginationMeta (new Pydantic schema)

Embedded in all paginated history responses.

| Field | Type | Description |
|-------|------|-------------|
| `page` | int | Current page number (1-indexed) |
| `page_size` | int | Records per page |
| `total_items` | int | Total matching records (respects active date filter) |
| `total_pages` | int | Computed: `ceil(total_items / page_size)` |

### BorrowerHistoryItem (new Pydantic schema)

One entry in the borrower history table. Shows completed loans only.

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | str | Item barcode |
| `bibliographic_record_id` | int | For deep linking to catalog |
| `title` | str | Book title (denormalized at query time) |
| `checkout_date` | datetime | When the loan started |
| `due_date` | date | When the loan was due |
| `return_date` | datetime | When the loan ended (always set — completed only) |
| `was_overdue` | bool | True if returned after due_date |

### BorrowerHistoryResponse (modified — adds pagination)

Replaces the existing unstructured dict returned by `get_borrower_circulation_history()`.

| Field | Type | Description |
|-------|------|-------------|
| `borrower_id` | str | Borrower identifier |
| `borrower_name` | str | Full name |
| `history` | list[BorrowerHistoryItem] | Current page of completed transactions |
| `pagination` | PaginationMeta | Page metadata |

### ItemHistoryItem (new Pydantic schema)

One entry in the item history table. Includes active loans (the current borrower).

| Field | Type | Description |
|-------|------|-------------|
| `borrower_name` | str | Full name of borrower |
| `checkout_date` | datetime | When the loan started |
| `due_date` | date | When the loan is/was due |
| `return_date` | datetime nullable | NULL if currently on loan |
| `was_overdue` | bool | True if returned after due_date |
| `status` | str | on_loan / returned_on_time / returned_late / overdue |

### ItemHistoryResponse (modified — adds pagination)

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | str | Item barcode |
| `title` | str | Book title |
| `current_loan` | ItemHistoryItem nullable | Active loan if any (not paginated) |
| `history` | list[ItemHistoryItem] | Current page of completed transactions |
| `pagination` | PaginationMeta | Page metadata for completed transactions |

---

## New i18n Keys

Added to both `src/bcd_web_vue/locales/en.json` and `src/bcd_web_vue/locales/fr.json` under the `circulation` section:

| Key | English | French |
|-----|---------|--------|
| `circulation.date_from` | "From" | "Du" |
| `circulation.date_to` | "To" | "Au" |
| `circulation.apply_date_filter` | "Apply" | "Appliquer" |
| `circulation.clear_date_filter` | "Clear" | "Effacer" |
| `circulation.no_history_for_period` | "No history found for this period." | "Aucun historique trouvé pour cette période." |
| `circulation.currently_on_loan_to` | "Currently on loan to {name}" | "Actuellement emprunté par {name}" |
| `circulation.history_returned_on_time` | "On time" | "À temps" |
| `circulation.history_returned_late` | "Late" | "En retard" |

---

## Query Patterns

### Borrower history page query

```
SELECT transactions WHERE
  borrower_id = :borrower_id        -- uses borrower_id index
  AND return_date IS NOT NULL        -- uses return_date index (new)
  [AND checkout_date >= :date_from]  -- uses checkout_date index
  [AND checkout_date <= :date_to]    -- uses checkout_date index
ORDER BY checkout_date DESC
LIMIT :page_size OFFSET :offset
```

### Item history page query (completed transactions only)

```
SELECT transactions WHERE
  item_id = :item_id                 -- uses item_id index
  AND return_date IS NOT NULL        -- uses return_date index (new)
  [AND checkout_date >= :date_from]
  [AND checkout_date <= :date_to]
ORDER BY checkout_date DESC
LIMIT :page_size OFFSET :offset
```

### Item current loan query (separate, not paginated)

```
SELECT transaction WHERE
  item_id = :item_id
  AND return_date IS NULL
LIMIT 1
```
