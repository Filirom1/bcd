# Find a notice API/client contract

The cataloging client searches the local catalog before it requests an external
source. The source route is deliberately fixed:

- `isbn` → `bnf`, then `google_books`
- `issn` or `ean977` → `sudoc`
- `unsupported_barcode` and free text → local search/manual entry only

## Local search

```http
GET /api/v1/catalog/notices/search?q=Wapiti&limit=20&offset=0
```

This endpoint never calls BnF, Google Books, or SUDOC. The response contains
`items`, `total`, `input_type`, `identifier_type`, `normalized_identifier`,
`derived_from_ean`, and `external_sources`. Notice items include the
identifier, publisher, publication year, medium type, copy count, authors, and
`issues_present` for periodicals.

## One external source

```http
POST /api/v1/catalog/notices/lookup
Content-Type: application/json

{"query":"9782070612758","source":"bnf"}
```

`source` is one of `bnf`, `google_books`, or `sudoc`. The service rechecks the
local catalog before making the request. It returns `found`, `not_found`,
`disabled`, `error`, or `local` in `status`; external responses include
`elapsed_ms` and `data` when available. An ISBN request is never sent to
SUDOC.

The aliases `GET /api/v1/catalog/external-sources` and
`POST /api/v1/catalog/external-sources/{source}/test` expose source status and
the Settings test action. The Settings page also uses
`POST /api/v1/admin/settings/external-sources/{source}/test`.

## Source settings

The admin settings response/update contains these fields:

```json
{
  "bnf_enabled": true,
  "bnf_timeout": 4,
  "google_books_enabled": true,
  "google_books_timeout": 4,
  "sudoc_enabled": true,
  "sudoc_timeout": 5
}
```

Timeouts are in seconds and are bounded to 1–60. Disabling a source does not
change routing; it makes that source return `disabled` so the client can
continue to the next applicable source or manual entry.

## Periodical copies

The client displays an explicit **Issue number** field for periodical notices.
For compatibility with the existing schema and imports, its value is sent as
`call_number` when creating an item:

```json
{
  "item_id":"BCD-440",
  "bibliographic_record_id":12,
  "call_number":"440"
}
```

No `issue_number` database or API field is added. The internal BCD barcode is a
separate value from the press barcode used to find the notice.
