# Quickstart: Fast Cataloging Workflow

## Automated validation

Run the JavaScript suite from the repository root:

```bash
python run_tests.py js
```

The focused cataloging UI and backend tests should cover URL transitions, browser history restoration, Enter/Escape behavior, reset/focus, local-first text lookup, bounded candidates from BnF, Google Books, and SUDOC, cover visibility, provider timeouts, and error handling when a referenced record cannot be loaded. Provider HTTP responses are mocked; the existing `browser_smoke` journey is reused and no new E2E permutations are added.

## Manual acceptance walkthrough

1. Open the cataloging page at a 1280×720 viewport. Confirm the stepper, scan field, and primary action are visible without vertical page scrolling.
2. Scan an ISBN and press Enter. Confirm the URL retains the ISBN and the lookup/form transition works.
3. Save a notice and create a copy. Confirm the URL uses the saved `record_id`, the available cover is visible on the bibliographic and copy screens, and the copy remains listed after reloading.
4. Use browser Back and Forward. Confirm the prior step is restored from saved catalog data and no saved notice or copy is deleted.
5. On an unsaved bibliographic form, refresh. Confirm only the ISBN is retained and other fields are not restored as a draft.
6. Press Escape from each workflow step. Confirm the workflow clears to lookup and the scan field receives focus, without changing any saved data.
7. Finish adding a copy and use the existing new-book action. Confirm it takes one action to reach the next focused scan field.
8. Repeat keyboard and layout checks in both English and French; confirm missing/failed covers do not show a broken-image placeholder or block cataloging.
9. Search for a title absent from the local catalog. Confirm the remote search starts only after the local miss, displays selectable candidates from each enabled source (BnF, Google Books, then SUDOC), and allows the librarian to start the next source or continue manually.
10. Select a remote candidate without an ISBN. Confirm its available data prefill the bibliographic form, no remote candidate is auto-selected, and manual saving remains possible.
11. Simulate an empty or failing provider response. Confirm the next enabled source and manual entry remain available.

## Live provider PoC status

The previous BnF probe returned matching SRU records, including a diagnostic record that must be ignored. Google Books returned HTTP 429 and SUDOC reset the connection, so those probes were inconclusive. Do not make live provider availability a prerequisite for the automated test suite.
