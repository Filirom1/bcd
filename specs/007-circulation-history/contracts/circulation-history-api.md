# API Contracts: Circulation History Pagination

**Feature**: 007-circulation-history
**Date**: 2026-03-26
**Base URL**: `/api/v1`

Both endpoints are **extensions** of existing routes. Existing query parameters (`limit`) are removed and replaced by the paginated parameters below.

---

## GET /circulation/borrower/{borrower_id}/history

Returns paginated completed circulation history for a single borrower. Active loans are excluded (they appear in the Current Loans tab).

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `borrower_id` | string | ✅ | Borrower barcode (e.g., "101") |

### Query Parameters

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `page` | integer | 1 | ≥ 1 | Page number (1-indexed) |
| `page_size` | integer | 20 | 1–50 | Records per page |
| `date_from` | date (ISO 8601) | null | — | Filter: checkout_date ≥ date_from |
| `date_to` | date (ISO 8601) | null | — | Filter: checkout_date ≤ date_to |

### Response 200 OK

```json
{
  "borrower_id": "101",
  "borrower_name": "Martin DUPONT",
  "history": [
    {
      "item_id": "BK-00142",
      "bibliographic_record_id": 57,
      "title": "Les Misérables",
      "checkout_date": "2025-01-12T09:15:00Z",
      "due_date": "2025-01-26",
      "return_date": "2025-01-24T14:30:00Z",
      "was_overdue": false
    },
    {
      "item_id": "BK-00089",
      "bibliographic_record_id": 34,
      "title": "Harry Potter à l'école des sorciers",
      "checkout_date": "2024-11-05T09:00:00Z",
      "due_date": "2024-11-19",
      "return_date": "2024-11-22T10:00:00Z",
      "was_overdue": true
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 42,
    "total_pages": 3
  }
}
```

### Response — Empty history

```json
{
  "borrower_id": "101",
  "borrower_name": "Martin DUPONT",
  "history": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 0,
    "total_pages": 0
  }
}
```

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Borrower not found |
| 422 | Invalid query parameter (page < 1, page_size out of range, invalid date format) |

---

## GET /circulation/item/{item_id}/history

Returns the current active loan (if any) plus paginated completed loan history for a single item.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_id` | string | ✅ | Item barcode (e.g., "BK-00142") |

### Query Parameters

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `page` | integer | 1 | ≥ 1 | Page number for completed history |
| `page_size` | integer | 20 | 1–50 | Records per page |
| `date_from` | date (ISO 8601) | null | — | Filter: checkout_date ≥ date_from |
| `date_to` | date (ISO 8601) | null | — | Filter: checkout_date ≤ date_to |

### Response 200 OK

```json
{
  "item_id": "BK-00142",
  "title": "Les Misérables",
  "current_loan": {
    "borrower_name": "Léa MARTIN",
    "checkout_date": "2026-03-15T09:00:00Z",
    "due_date": "2026-03-29",
    "return_date": null,
    "was_overdue": false,
    "status": "on_loan"
  },
  "history": [
    {
      "borrower_name": "Martin DUPONT",
      "checkout_date": "2025-01-12T09:15:00Z",
      "due_date": "2025-01-26",
      "return_date": "2025-01-24T14:30:00Z",
      "was_overdue": false,
      "status": "returned_on_time"
    },
    {
      "borrower_name": "Amira BENALI",
      "checkout_date": "2024-11-05T09:00:00Z",
      "due_date": "2024-11-19",
      "return_date": "2024-11-22T10:00:00Z",
      "was_overdue": true,
      "status": "returned_late"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 28,
    "total_pages": 2
  }
}
```

### Response — No active loan, no history

```json
{
  "item_id": "BK-00999",
  "title": "Le Petit Prince",
  "current_loan": null,
  "history": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 0,
    "total_pages": 0
  }
}
```

### Status Values (item history)

| Value | Meaning |
|-------|---------|
| `on_loan` | Currently checked out (only in `current_loan`) |
| `returned_on_time` | Returned on or before due_date |
| `returned_late` | Returned after due_date |
| `overdue` | Not yet returned and past due_date |

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Item not found |
| 422 | Invalid query parameter |

---

## UI Wireframes

### Borrower History Tab

```
┌─────────────────────────────────────────────────────────┐
│ MARTIN DUPONT — CP (3A)                                 │
│ [Loans] [Holds] [History ◄]                             │
├─────────────────────────────────────────────────────────┤
│ From: [__________] To: [__________] [Apply] [Clear]     │
├──────────────────────┬────────────┬──────────┬──────────┤
│ Title                │ Checkout   │ Due      │ Status   │
├──────────────────────┼────────────┼──────────┼──────────┤
│ Les Misérables       │ 12 Jan 25  │ 26 Jan 25│ ✅ On time│
│ Harry Potter T1      │ 05 Nov 24  │ 19 Nov 24│ ⚠ Late   │
│ ...                  │ ...        │ ...      │ ...      │
├─────────────────────────────────────────────────────────┤
│ ◄ Previous    Page 1 of 3 (42 items)    Next ►          │
└─────────────────────────────────────────────────────────┘
```

### Item History Tab (RecordDetail)

```
┌─────────────────────────────────────────────────────────┐
│ Les Misérables — Victor Hugo                            │
│ [Details] [Copies] [Holds] [History ◄]                  │
├─────────────────────────────────────────────────────────┤
│ 🔵 Currently on loan to: Léa MARTIN — Due: 29 Mar 26   │
├─────────────────────────────────────────────────────────┤
│ From: [__________] To: [__________] [Apply] [Clear]     │
├───────────────────┬────────────┬────────────┬───────────┤
│ Borrower          │ Checkout   │ Return     │ Status    │
├───────────────────┼────────────┼────────────┼───────────┤
│ Martin DUPONT     │ 12 Jan 25  │ 24 Jan 25  │ ✅ On time│
│ Amira BENALI      │ 05 Nov 24  │ 22 Nov 24  │ ⚠ Late   │
│ ...               │ ...        │ ...        │ ...      │
├─────────────────────────────────────────────────────────┤
│ ◄ Previous    Page 1 of 2 (28 items)    Next ►          │
└─────────────────────────────────────────────────────────┘
```
