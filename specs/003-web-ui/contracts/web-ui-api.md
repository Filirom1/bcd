# Web UI API Contract

**Feature**: Localhost Web UI for BCD Library System
**Date**: 2026-01-30
**Status**: Phase 1 Complete

## Overview

This document defines the API contract between the BCD web UI (client) and the FastAPI server. The web UI uses a **dual-response pattern** where endpoints return either:
- **HTML fragments** for htmx requests (identified by `HX-Request` header)
- **JSON responses** for standard API clients (CLI, future mobile app)

---

## Dual-Response Pattern

### Request Identification

The server detects htmx requests using the `HX-Request` header:

```python
from fastapi import Request

@app.get("/api/v1/borrowers/search")
async def search_borrowers(query: str, request: Request):
    borrowers = await borrower_service.search(query)

    # Check if request is from htmx
    if "HX-Request" in request.headers:
        return templates.TemplateResponse("borrower_list.html", {
            "request": request,
            "borrowers": borrowers
        })

    # Standard JSON response for other clients
    return {"borrowers": [b.dict() for b in borrowers]}
```

### Response Types

| Client | Request Header | Response Type | Content-Type |
|--------|----------------|---------------|--------------|
| **htmx** | `HX-Request: true` | HTML Fragment | `text/html` |
| **CLI** | None | JSON | `application/json` |
| **Future Mobile** | None | JSON | `application/json` |

---

## htmx-Specific Headers

### Request Headers (from htmx)

| Header | Description | Example |
|--------|-------------|---------|
| `HX-Request` | Always `true` for htmx requests | `true` |
| `HX-Trigger` | ID of element that triggered request | `search-input` |
| `HX-Trigger-Name` | Name of triggered element | `query` |
| `HX-Target` | ID of target element for response | `results-container` |
| `HX-Current-URL` | Current URL before request | `/circulation` |

### Response Headers (to htmx)

| Header | Description | Usage |
|--------|-------------|-------|
| `HX-Trigger` | Trigger client-side event after swap | `HX-Trigger: showSuccessToast` |
| `HX-Redirect` | Client-side redirect | `HX-Redirect: /circulation` |
| `HX-Refresh` | Force page refresh | `HX-Refresh: true` |
| `HX-Replace-Url` | Update browser URL | `HX-Replace-Url: /borrower/101` |

---

## Circulation Endpoints

### 1. GET /borrowers/{borrower_id}

**Purpose**: Load borrower information for checkout

**htmx Usage**:
```html
<input type="text"
       id="borrower-id"
       hx-get="/api/v1/borrowers/{value}"
       hx-trigger="change"
       hx-target="#borrower-info"
       hx-swap="innerHTML">

<div id="borrower-info"></div>
```

**HTML Fragment Response** (htmx):
```html
<div class="borrower-panel">
  <h4>Amira BENALI</h4>
  <p class="text-muted">CP-A</p>
  <div class="loan-status">
    <span class="badge bg-success">2/2 emprunts</span>
  </div>

  <!-- Overdue warning if applicable -->
  <div class="alert alert-danger" x-show="hasOverdue">
    <strong>Articles en retard :</strong>
    <ul>
      <li>Stuart Little - 3 jours</li>
    </ul>
  </div>
</div>
```

**JSON Response** (CLI/API):
```json
{
  "borrower_id": "101",
  "full_name": "Amira BENALI",
  "class_name": "CP-A",
  "current_loans": 2,
  "loan_limit": 2,
  "overdue_items": [
    {
      "item_id": "785",
      "title": "Stuart Little",
      "days_overdue": 3
    }
  ]
}
```

### 2. POST /circulation/checkout

**Purpose**: Complete checkout transaction

**htmx Usage**:
```html
<form hx-post="/api/v1/circulation/checkout"
      hx-target="#checkout-result"
      hx-swap="innerHTML">
  <input type="hidden" name="borrower_id" value="101">
  <input type="hidden" name="item_ids" value='["785", "787"]'>
  <button type="submit">Confirmer l'emprunt</button>
</form>

<div id="checkout-result"></div>
```

**HTML Fragment Response** (htmx):
```html
<div class="alert alert-success">
  <h5>✓ Emprunt confirmé</h5>
  <p>2 articles empruntés à Amira BENALI</p>
  <ul>
    <li>Stuart Little - À retourner le 13/02/2026</li>
    <li>Charlotte's Web - À retourner le 13/02/2026</li>
  </ul>
</div>
```

**JSON Response** (CLI/API):
```json
{
  "transaction_ids": [1, 2],
  "due_dates": ["2026-02-13", "2026-02-13"],
  "borrower": {
    "borrower_id": "101",
    "full_name": "Amira BENALI"
  },
  "items": [
    {"item_id": "785", "title": "Stuart Little"},
    {"item_id": "787", "title": "Charlotte's Web"}
  ]
}
```

### 3. POST /circulation/return

**Purpose**: Process item returns

**htmx Usage**:
```html
<form hx-post="/api/v1/circulation/return"
      hx-target="#return-result"
      hx-swap="innerHTML">
  <input type="text"
         name="item_ids"
         placeholder="Scanner code-barres">
  <button type="submit">Retourner</button>
</form>

<div id="return-result"></div>
```

**HTML Fragment Response** (htmx):
```html
<div class="return-confirmation">
  <div class="alert alert-success">
    <h5>✓ Retour enregistré</h5>
  </div>
  <table class="table">
    <tr>
      <td>Stuart Little</td>
      <td>Amira BENALI</td>
      <td><span class="badge bg-danger">3 jours de retard</span></td>
    </tr>
  </table>
</div>
```

**JSON Response** (CLI/API):
```json
{
  "returned": [
    {
      "item_id": "785",
      "title": "Stuart Little",
      "borrower_name": "Amira BENALI",
      "was_overdue": true,
      "days_overdue": 3
    }
  ]
}
```

---

## Catalog Endpoints

### 4. GET /catalog/search

**Purpose**: Search bibliographic records

**htmx Usage**:
```html
<input type="search"
       name="q"
       hx-get="/api/v1/catalog/search"
       hx-trigger="input changed delay:300ms"
       hx-target="#search-results"
       hx-include="[name='available_only']">

<label>
  <input type="checkbox" name="available_only" value="true">
  Disponibles seulement
</label>

<div id="search-results"></div>
```

**HTML Fragment Response** (htmx):
```html
<table class="table table-striped">
  <thead>
    <tr>
      <th>Titre</th>
      <th>Auteur</th>
      <th>Disponibilité</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Stuart Little</td>
      <td>E.B. White</td>
      <td><span class="badge bg-success">● Disponible</span></td>
    </tr>
    <tr>
      <td>Charlotte's Web</td>
      <td>E.B. White</td>
      <td><span class="badge bg-warning">● Emprunté (retour le 15/02)</span></td>
    </tr>
  </tbody>
</table>

<!-- Pagination -->
<nav>
  <ul class="pagination">
    <li class="page-item active"><a class="page-link" href="#" hx-get="/api/v1/catalog/search?page=1">1</a></li>
    <li class="page-item"><a class="page-link" href="#" hx-get="/api/v1/catalog/search?page=2">2</a></li>
  </ul>
</nav>
```

**JSON Response** (CLI/API):
```json
{
  "results": [
    {
      "record_id": 123,
      "title": "Stuart Little",
      "author": "E.B. White",
      "isbn": "9782211234567",
      "available_copies": 1,
      "total_copies": 1,
      "status": "available"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 234,
    "total_pages": 5
  }
}
```

### 5. POST /catalog/lookup-isbn

**Purpose**: Retrieve bibliographic data from BNF API

**htmx Usage**:
```html
<form hx-post="/api/v1/catalog/lookup-isbn"
      hx-target="#isbn-result"
      hx-swap="innerHTML">
  <input type="text" name="isbn" placeholder="ISBN">
  <button type="submit">Rechercher BNF</button>
</form>

<div id="isbn-result"></div>
```

**HTML Fragment Response** (htmx - success):
```html
<div class="card">
  <div class="card-body">
    <h5>Résultat de la recherche BNF</h5>
    <form hx-post="/api/v1/catalog/records"
          hx-target="#cataloging-result">
      <div class="mb-3">
        <label>Titre</label>
        <input type="text" class="form-control" name="title" value="Stuart Little">
      </div>
      <div class="mb-3">
        <label>Auteur</label>
        <input type="text" class="form-control" name="author" value="E.B. White">
      </div>
      <div class="mb-3">
        <label>Éditeur</label>
        <input type="text" class="form-control" name="publisher" value="École des loisirs">
      </div>
      <button type="submit" class="btn btn-primary">Enregistrer</button>
    </form>
  </div>
</div>
```

**HTML Fragment Response** (htmx - not found):
```html
<div class="alert alert-warning">
  <strong>ISBN non trouvé dans la BNF</strong>
  <p>Veuillez saisir les informations manuellement.</p>
  <a href="#" hx-get="/api/v1/catalog/manual-entry" hx-target="#isbn-result">
    Saisie manuelle
  </a>
</div>
```

**JSON Response** (CLI/API):
```json
{
  "found": true,
  "bibliographic_data": {
    "isbn": "9782211234567",
    "title": "Stuart Little",
    "author": "E.B. White",
    "publisher": "École des loisirs",
    "publication_year": 2005,
    "subjects": ["Fiction", "Aventure"]
  }
}
```

---

## Borrower Management Endpoints

### 6. GET /borrowers

**Purpose**: List borrowers with filters

**htmx Usage**:
```html
<select name="class_name"
        hx-get="/api/v1/borrowers"
        hx-trigger="change"
        hx-target="#borrower-table"
        hx-include="[name='search']">
  <option value="">Toutes les classes</option>
  <option value="CP-A">CP-A</option>
  <option value="CP-B">CP-B</option>
</select>

<input type="search"
       name="search"
       hx-get="/api/v1/borrowers"
       hx-trigger="input changed delay:300ms"
       hx-target="#borrower-table"
       hx-include="[name='class_name']">

<div id="borrower-table"></div>
```

**HTML Fragment Response** (htmx):
```html
<table class="table table-hover">
  <thead>
    <tr>
      <th>ID</th>
      <th>Nom</th>
      <th>Classe</th>
      <th>Emprunts</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>101</td>
      <td>Amira BENALI ⚠️</td>
      <td>CP-A</td>
      <td>2/2</td>
      <td>
        <a href="#"
           hx-get="/api/v1/borrowers/101"
           hx-target="#modal-content"
           class="btn btn-sm btn-primary">
          Détails
        </a>
      </td>
    </tr>
  </tbody>
</table>
```

**JSON Response** (CLI/API):
```json
{
  "borrowers": [
    {
      "borrower_id": "101",
      "full_name": "Amira BENALI",
      "class_name": "CP-A",
      "current_loans": 2,
      "has_overdue": true
    }
  ],
  "pagination": {
    "page": 1,
    "total": 156
  }
}
```

---

## Reports Endpoints

### 7. GET /reports/overdue

**Purpose**: Generate overdue items report

**htmx Usage**:
```html
<button hx-get="/api/v1/reports/overdue"
        hx-target="#report-content"
        hx-swap="innerHTML">
  Générer rapport des retards
</button>

<div id="report-content"></div>
```

**HTML Fragment Response** (htmx):
```html
<div class="report-container">
  <h3>Articles en retard par classe</h3>
  <p class="text-muted">Généré le 30/01/2026</p>

  <!-- CP-A -->
  <div class="class-report">
    <h4>CP-A</h4>
    <table class="table table-sm">
      <thead>
        <tr>
          <th>Emprunteur</th>
          <th>Titre</th>
          <th>Date de retour</th>
          <th>Retard</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Amira BENALI</td>
          <td>Stuart Little</td>
          <td>27/01/2026</td>
          <td class="text-danger">3 jours</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Print button -->
  <button onclick="window.print()" class="btn btn-secondary">
    🖨️ Imprimer
  </button>
</div>
```

**JSON Response** (CLI/API):
```json
{
  "report_date": "2026-01-30",
  "overdue_by_class": [
    {
      "class_name": "CP-A",
      "overdue_items": [
        {
          "borrower_id": "101",
          "borrower_name": "Amira BENALI",
          "item_id": "785",
          "title": "Stuart Little",
          "due_date": "2026-01-27",
          "days_overdue": 3
        }
      ]
    }
  ]
}
```

---

## Settings Endpoints

### 8. GET /admin/settings

**Purpose**: Retrieve system settings

**htmx Usage**:
```html
<div hx-get="/api/v1/admin/settings"
     hx-trigger="load"
     hx-target="this"
     hx-swap="innerHTML">
  Chargement...
</div>
```

**HTML Fragment Response** (htmx):
```html
<form hx-put="/api/v1/admin/settings"
      hx-target="#save-result">
  <div class="mb-3">
    <label>Durée de prêt (jours)</label>
    <input type="number" class="form-control" name="loan_duration_days" value="14">
  </div>
  <div class="mb-3">
    <label>Limite d'emprunts par personne</label>
    <input type="number" class="form-control" name="max_loans_per_borrower" value="2">
  </div>
  <div class="mb-3">
    <label>Date de début d'année scolaire</label>
    <input type="date" class="form-control" name="academic_year_start" value="2025-09-01">
  </div>
  <button type="submit" class="btn btn-primary">Enregistrer</button>
</form>
<div id="save-result"></div>
```

### 9. PUT /admin/settings

**Purpose**: Update system settings

**htmx Usage**: (form above submits here)

**HTML Fragment Response** (htmx - success):
```html
<div class="alert alert-success">
  ✓ Paramètres enregistrés avec succès
</div>
```

**JSON Response** (CLI/API):
```json
{
  "success": true,
  "updated_settings": {
    "loan_duration_days": 21,
    "max_loans_per_borrower": 3
  }
}
```

---

## Error Responses

### htmx Error Fragment

```html
<div class="alert alert-danger" role="alert">
  <strong>Erreur</strong>
  <p>Emprunteur 999 introuvable</p>
</div>
```

### JSON Error Response

```json
{
  "success": false,
  "error": "borrower_not_found",
  "message": "Borrower 999 not found",
  "details": {
    "borrower_id": "999"
  }
}
```

### HTTP Status Codes

| Status | Usage |
|--------|-------|
| `200 OK` | Successful GET request |
| `201 Created` | Successful POST creating resource |
| `400 Bad Request` | Invalid input format |
| `404 Not Found` | Resource not found |
| `409 Conflict` | Business rule violation |
| `422 Unprocessable Entity` | Validation errors |
| `500 Internal Server Error` | Server error |

---

## Template Organization

### HTML Fragment Templates

```
src/bcd_web/templates/
├── fragments/
│   ├── borrower_info.html         # Borrower panel for circulation
│   ├── borrower_list.html         # Borrower table rows
│   ├── checkout_confirmation.html # Checkout success message
│   ├── return_confirmation.html   # Return success message
│   ├── search_results.html        # Catalog search results table
│   ├── isbn_lookup_result.html    # BNF ISBN lookup form
│   ├── overdue_report.html        # Overdue report by class
│   ├── settings_form.html         # Settings edit form
│   └── error.html                 # Generic error alert
└── layouts/
    └── base.html                  # Full page template (for initial load)
```

---

## Static File Serving

### FastAPI Configuration

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Serve static assets
app.mount("/static", StaticFiles(directory="src/bcd_web"), name="static")

# Templates for htmx fragments
templates = Jinja2Templates(directory="src/bcd_web/templates")

# Serve SPA at root
app.mount("/", StaticFiles(directory="src/bcd_web", html=True), name="web")
```

### URL Structure

- `/` → `src/bcd_web/index.html` (SPA shell)
- `/static/css/main.css` → `src/bcd_web/css/main.css`
- `/static/js/app.js` → `src/bcd_web/js/app.js`
- `/static/locales/fr.json` → `src/bcd_web/locales/fr.json`
- `/api/v1/*` → API endpoints (dual-response)

---

## CORS Configuration

Since web UI is served from same origin as API, no CORS headers needed.

```python
# CORS already configured in main.py for future mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # Same origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Security Considerations

1. **Input Validation**: All user input validated server-side
2. **CSRF Protection**: Not required (no authentication, local network only)
3. **XSS Prevention**: Template engine auto-escapes HTML
4. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
5. **Rate Limiting**: API endpoints rate-limited to prevent abuse

---

## Related Documents

- [Specification](../spec.md) - Feature requirements
- [Research](../research.md) - Framework decisions
- [Data Model](../data-model.md) - Client-side state structures
- [Existing API Spec](../../001-school-library-system/contracts/api-spec.yaml) - Full REST API documentation

---

## Summary

This contract defines:
1. **Dual-response pattern** for htmx (HTML) and standard clients (JSON)
2. **htmx-specific headers** for request/response communication
3. **HTML fragment templates** for dynamic UI updates
4. **Error handling** for both htmx and JSON clients
5. **Static file serving** strategy for SPA assets

All endpoints maintain **backward compatibility** with existing CLI and enable **future mobile app** development.
