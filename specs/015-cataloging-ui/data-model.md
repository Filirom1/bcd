# Data Model: Fast Cataloging Workflow

## Existing persisted entities

No database model or migration is introduced.

### Bibliographic notice

- Existing catalog record with a persisted `record_id` and bibliographic fields.
- May have an associated cover reference/image.
- Loaded from the existing catalog API when a route contains its `record_id`.
- A newly entered notice becomes persisted only after the existing save action succeeds.

### Physical copy

- Existing catalog item associated with a bibliographic notice.
- Persisted by the existing copy-creation action.
- Reloaded from the catalog when returning to the copy-creation step.

## Client-side navigation state

| Field | Source | Validation | Persistence |
|---|---|---|---|
| `step` | URL query | One of lookup, bibliographic form, or item creation; invalid combinations normalize to a safe valid step. | Browser history only |
| `query` | URL query / lookup input | 1-200 characters; ISBN/ISSN values use existing identifier classification, otherwise treated as title/free text. | URL while the notice is not yet persisted |
| `record_id` | URL query after notice save or local match | Must identify an existing catalog record; invalid or missing records use the existing error/restart behavior. | Database; its ID is referenced by the URL |
| Unsaved bibliographic fields | Form component state | Existing form validation | Memory only; discarded on reload or explicit reset |
| Unsaved copy fields | Copy component state | Existing item validation | Memory only; saved item data is reloaded from the catalog |
| Remote candidate | Single-provider lookup response | Candidate must have a usable title; at most 10 candidates per source; source is BnF, Google Books, or SUDOC for free text. | Transient UI state; never serialized or saved until selected and explicitly submitted |

## Candidate data

Remote candidates reuse the existing bibliographic result shape. They may include title, authors, publisher, publication year, ISBN, cover URL, and source. Missing ISBN or cover does not prevent selection; the librarian reviews the candidate in the bibliographic form before saving.

## State transitions

```text
lookup(query)
  ├─ local notice selected ──────────────────> item creation(record_id)
  ├─ remote candidate selected ──────────────> bibliographic form(query)
  └─ manual entry ───────────────────────────> bibliographic form(query)
       └─ save succeeds ─────────────────────> bibliographic form(record_id)
                                                 └─ continue ─> item creation(record_id)
item creation(record_id)
  ├─ browser Back ───────────────────────────> saved bibliographic form(record_id)
  ├─ browser Forward ─────────────────────────> item creation(record_id)
  └─ new book / Escape ───────────────────────> lookup (clean URL)
```

For text queries, a local search runs first. With no local match, remote candidates are fetched from one enabled provider at a time in BnF, Google Books, then SUDOC order; the next provider can be started without clearing earlier candidates. History changes do not mutate persisted entities. The browser may discard unsaved fields when leaving their form.
