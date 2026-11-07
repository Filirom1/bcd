# Cataloging Route Contract

## URL state

The application uses Vue Router's existing hash history. Cataloging workflow parameters are query values within the cataloging route.

| Route state | Required values | Rendered state |
|---|---|---|
| Lookup | `step=lookup`; optional `query` | Search field, prefilled with an ISBN, ISSN, or text query |
| Unsaved bibliographic form | `step=bibliographic-form`; optional `query` | New bibliographic form; only the original lookup value may be prefilled |
| Saved bibliographic form | `step=bibliographic-form&record_id={id}` | Saved record loaded from the catalog |
| Copy creation | `step=item-creation&record_id={id}` | Saved record and its existing copies loaded from the catalog |

An existing local notice selected from lookup may navigate directly to copy creation. A malformed step/identifier combination must not be interpreted as a saved record. If a referenced record cannot be loaded, show the existing error handling and offer a way to restart.

## External text lookup contract

`POST /catalog/notices/lookup` continues to receive `{ query, source }`. For ISBN/ISSN queries, its existing single-result `found` response remains unchanged. For free-text queries:

- The local search is rechecked first; if it finds matches, the existing `local` response is returned without an external call.
- BnF, Google Books, and SUDOC are applicable to free-text searches, in that order. Existing ISBN/ISSN routing remains unchanged.
- A provider response with candidates returns `status=results`, `items` containing at most 10 normalized bibliographic candidate objects, `total`, `source`, and `elapsed_ms`. SUDOC candidates may not include a cover.
- Empty, disabled, or failed providers return an empty result/status as they do today, allowing the client to offer the next source or manual entry.
- A candidate is not saved or selected by the API. The client requires an explicit selection and opens the existing bibliographic form.

## Navigation semantics

- Moving to another workflow step adds a browser-history entry.
- Once a new bibliographic notice is saved, replace the current unsaved-form entry with the saved `record_id` state, then push the copy-creation state. Browser Back from copy creation therefore returns to the persisted notice.
- Browser Back/Forward changes only route state. It never deletes or reverses a saved notice or copy.
- Escape and the existing new-book action replace the current route with a clean lookup state and focus the identifier scanner.
- Reloading an unsaved form may restore its lookup value, but never restores other unsaved bibliographic fields, remote results, or copy fields.

## API contract impact

No endpoint is added. The existing lookup response is extended with a bounded `results` candidate-list shape for free-text provider lookups; the existing identifier lookup response remains unchanged. The UI uses existing catalog operations to save notices and copies and to reload the record and its items. The route contract remains independent of API response shape beyond the existing record and item data used by those components.
