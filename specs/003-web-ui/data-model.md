# Data Model: Web UI for BCD Library System

**Feature**: Localhost Web UI
**Date**: 2026-01-30
**Status**: Phase 1 Complete

## Overview

The web UI is a **frontend-only feature** that consumes the existing BCD REST API. It does not introduce new database entities or modify existing schemas. This document describes the client-side data structures and their relationship to the API.

---

## Client-Side Data Structures

### 1. UI State (Alpine.js/JavaScript)

These are transient client-side objects that manage UI state, not persisted to database.

#### CurrentCheckout
**Purpose**: Manages active checkout transaction state

```javascript
{
  borrower: {
    borrower_id: string,
    full_name: string,
    class_name: string,
    current_loans: number,
    loan_limit: number,
    overdue_items: array<OverdueItem>
  },
  scannedItems: array<ScannedItem>,
  errors: array<string>,
  isProcessing: boolean
}
```

**Fields**:
- `borrower`: Populated from `GET /api/v1/borrowers/{borrower_id}`
- `scannedItems`: Array of items scanned for checkout
- `errors`: Validation or API error messages
- `isProcessing`: Loading state during API calls

**Lifecycle**: Created on circulation page load, cleared after successful checkout

#### ScannedItem
```javascript
{
  item_id: string,
  title: string,
  barcode: string,
  due_date: string (ISO 8601),
  status: 'pending' | 'confirmed' | 'error'
}
```

#### SearchResults
**Purpose**: Manages catalog/borrower search state

```javascript
{
  query: string,
  results: array<SearchResultItem>,
  filters: {
    availability: 'all' | 'available' | 'on_loan',
    class: string | null
  },
  pagination: {
    page: number,
    page_size: number,
    total: number
  },
  isLoading: boolean
}
```

#### UINotification
**Purpose**: Toast/alert messages

```javascript
{
  id: string,
  type: 'success' | 'error' | 'warning' | 'info',
  message: string,
  translationKey: string,  // For i18n
  interpolations: object,   // Variables for translation
  duration: number          // Auto-dismiss time in ms
}
```

---

## API Entity Mappings

These entities exist in the database and are retrieved via the BCD REST API. The web UI consumes them but does not define them.

### 2. Borrower (from API)

**API Endpoint**: `GET /api/v1/borrowers/{borrower_id}`

**Response Schema** (consumed by web UI):
```json
{
  "borrower_id": "101",
  "full_name": "Amira BENALI",
  "role": "student",
  "class_name": "CP-A",
  "grade_level": "CP",
  "barcode": "BOR-101",
  "is_active": true,
  "current_loans": 2,
  "loan_limit": 2,
  "overdue_count": 0,
  "contact_info": {
    "email": "[email protected]",
    "phone": null
  }
}
```

**Usage in Web UI**:
- Circulation page: Load borrower on ID scan
- Borrower list page: Display in table
- Borrower detail page: Full information display

### 3. Bibliographic Record (from API)

**API Endpoint**: `GET /api/v1/catalog/records/{record_id}`

**Response Schema**:
```json
{
  "record_id": 123,
  "isbn": "9782211234567",
  "title": "Stuart Little",
  "author": "E.B. White",
  "publisher": "École des loisirs",
  "publication_year": 2005,
  "subjects": ["Fiction", "Aventure"],
  "summary": "L'histoire d'une petite souris...",
  "items": [
    {
      "item_id": "785",
      "barcode": "ITEM-785",
      "copy_number": 1,
      "status": "available",
      "location": "Rayon Fiction",
      "due_date": null,
      "borrower_id": null
    }
  ],
  "total_copies": 1,
  "available_copies": 1
}
```

**Usage in Web UI**:
- Catalog search: Display results with availability
- Item detail page: Full bibliographic information
- Cataloging page: Pre-fill form from BNF lookup

### 4. Item (from API)

**API Endpoint**: `GET /api/v1/catalog/items/{item_id}`

**Response Schema**:
```json
{
  "item_id": "785",
  "bibliographic_record_id": 123,
  "barcode": "ITEM-785",
  "copy_number": 1,
  "status": "available" | "on_loan" | "damaged" | "lost",
  "location": "Rayon Fiction",
  "condition": "good",
  "acquisition_date": "2025-09-01",
  "current_loan": {
    "borrower_id": "101",
    "borrower_name": "Amira BENALI",
    "due_date": "2026-02-13",
    "is_overdue": false,
    "days_overdue": 0
  }
}
```

**Usage in Web UI**:
- Checkout: Validate availability before checkout
- Return: Display borrower info for returned item
- Catalog detail: Show all copies with status

### 5. Circulation Transaction (from API)

**API Endpoint**: `POST /api/v1/circulation/checkout`

**Request Schema** (sent from web UI):
```json
{
  "borrower_id": "101",
  "item_ids": ["785", "787"]
}
```

**Response Schema**:
```json
{
  "transaction_ids": [1, 2],
  "due_dates": ["2026-02-13", "2026-02-13"],
  "borrower": {
    "borrower_id": "101",
    "full_name": "Amira BENALI",
    "class_name": "CP-A",
    "current_loans": 2,
    "loan_limit": 2
  },
  "items": [
    {
      "item_id": "785",
      "title": "Stuart Little",
      "due_date": "2026-02-13"
    }
  ]
}
```

### 6. System Settings (from API)

**API Endpoint**: `GET /api/v1/admin/settings`

**Response Schema**:
```json
{
  "loan_duration_days": 14,
  "max_loans_per_borrower": 2,
  "academic_year_start": "2025-09-01",
  "barcode_format": "CODE128",
  "library_name": "BCD École Élémentaire Victor Hugo",
  "librarian_email": "[email protected]"
}
```

**Usage in Web UI**:
- Settings page: Display and update configuration
- Circulation: Use loan_duration_days for due date calculation display

---

## Translation Structure (i18n)

### Translation Files (JSON)

**File**: `/src/bcd_web/locales/fr.json`

```json
{
  "app": {
    "title": "BCD - Système de Bibliothèque",
    "subtitle": "Gestion de bibliothèque scolaire"
  },
  "navigation": {
    "circulation": "Circulation",
    "catalog": "Catalogue",
    "borrowers": "Emprunteurs",
    "reports": "Rapports",
    "settings": "Paramètres"
  },
  "circulation": {
    "checkout": "Emprunter",
    "return": "Retourner",
    "borrower_id": "Numéro d'emprunteur",
    "scan_item": "Scanner l'article",
    "items_one": "{{count}} article emprunté",
    "items_other": "{{count}} articles empruntés"
  },
  "errors": {
    "borrower_not_found": "Emprunteur {{borrower_id}} introuvable",
    "item_unavailable": "Article {{item_id}} non disponible",
    "over_limit": "Limite d'emprunt atteinte ({{current}}/{{max}})"
  }
}
```

**Structure**:
- Hierarchical key-value pairs
- Interpolation with `{{variable}}` syntax
- Pluralization with `_one` and `_other` suffixes (French: 0-1 = "one", 2+ = "other")

---

## Component State Patterns

### 1. Checkout Page State Flow

```
Initial State:
  borrower = null
  scannedItems = []
  errors = []

User scans borrower ID "101":
  → Call GET /api/v1/borrowers/101
  → Update borrower = { borrower_id: "101", ... }
  → Display borrower info panel

User scans item "785":
  → Call GET /api/v1/catalog/items/785
  → Validate item.status === "available"
  → Add to scannedItems = [{item_id: "785", status: "pending", ...}]
  → Display in running list

User clicks "Confirmer l'emprunt":
  → Call POST /api/v1/circulation/checkout
  → Update scannedItems status to "confirmed"
  → Show success notification
  → Reset state for next transaction
```

### 2. Search Page State Flow

```
Initial State:
  query = ""
  results = []
  filters = { availability: "all", class: null }
  pagination = { page: 1, page_size: 50, total: 0 }

User types "Stuart":
  → Debounce 300ms
  → Call GET /api/v1/catalog/search?q=Stuart&page=1&page_size=50
  → Update results = [...]
  → Update pagination.total = response.total

User selects "Available only" filter:
  → Update filters.availability = "available"
  → Call GET /api/v1/catalog/search?q=Stuart&available_only=true
  → Update results

User clicks page 2:
  → Update pagination.page = 2
  → Call GET /api/v1/catalog/search?q=Stuart&page=2
  → Update results
```

---

## Validation Rules

### Client-Side Validation (before API call)

**Borrower ID**:
- Required
- Pattern: Alphanumeric, 1-20 characters
- Error message: "Veuillez entrer un numéro d'emprunteur valide"

**Item Barcode**:
- Required
- Pattern: Alphanumeric, 1-50 characters
- Error message: "Veuillez scanner ou saisir un code-barres valide"

**Search Query**:
- Minimum 1 character for search
- Maximum 100 characters

**Checkout Validation**:
- At least 1 item scanned
- Borrower must be active (`is_active === true`)
- Borrower not over loan limit (`current_loans < loan_limit`)
- All items must be available (`status === "available"`)

### Server-Side Validation (API enforces)

The API validates all business rules and returns appropriate HTTP status codes:
- `400 Bad Request`: Invalid input format
- `404 Not Found`: Borrower/item not found
- `409 Conflict`: Business rule violation (overlimit, unavailable item)
- `422 Unprocessable Entity`: Validation errors

Web UI displays server errors using translation keys.

---

## Error Handling

### Error Response Structure (from API)

```json
{
  "success": false,
  "error": "checkout_overlimit",
  "message": "Borrower has reached maximum loan limit",
  "details": {
    "borrower_id": "101",
    "current_loans": 2,
    "loan_limit": 2
  }
}
```

### Client-Side Error Mapping

```javascript
const errorTranslations = {
  'borrower_not_found': 'errors.borrower_not_found',
  'item_unavailable': 'errors.item_unavailable',
  'checkout_overlimit': 'errors.over_limit',
  'network_error': 'errors.network'
};

function displayError(apiError) {
  const translationKey = errorTranslations[apiError.error] || 'errors.generic';
  const message = i18n.t(translationKey, apiError.details);
  showNotification({ type: 'error', message });
}
```

---

## Performance Considerations

### Caching Strategy

**No client-side caching** - Always fetch fresh data from API to ensure accuracy:
- Borrower information (loan counts change frequently)
- Item availability (status changes with checkouts/returns)
- Search results (catalog updates in real-time)

**Exception**: Translation files cached in browser after first load

### Pagination

All list endpoints support pagination:
- Default page size: 50 items
- Maximum page size: 100 items
- Server-side pagination to prevent memory issues

---

## Security Considerations

### No Authentication (Per Spec)

The web UI is accessed on local network without authentication (single librarian use case).

**Security measures**:
- API validates all input server-side
- No sensitive data exposed (school library context)
- CORS configured for same-origin only
- Rate limiting on API endpoints

### Input Sanitization

All user input sanitized before display:
- HTML entities escaped to prevent XSS
- API validates and sanitizes all input
- No eval() or innerHTML usage in JavaScript

---

## Related Documents

- [Specification](spec.md) - Feature requirements and user stories
- [Research](research.md) - Technology decisions and rationale
- [API Specification](../001-school-library-system/contracts/api-spec.yaml) - Existing REST API contracts
- [Existing Data Model](../001-school-library-system/data-model.md) - Database schema documentation

---

## Summary

The web UI is a **presentation layer** that:
1. **Consumes existing API entities** (Borrower, Item, Bibliographic Record, etc.)
2. **Manages ephemeral UI state** (current checkout, search results, notifications)
3. **Uses i18n translations** (French/English JSON files)
4. **Validates client-side** (before API calls for UX)
5. **Defers to API** (for all business logic and persistence)

**No database changes required** - All data interactions through existing BCD REST API.
