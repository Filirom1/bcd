# Feature Specification: Fast Cataloging Workflow

**Feature Branch**: `015-cataloging-ui`  
**Created**: 2026-11-07  
**Status**: Draft  
**Input**: User description: "dans cataloging, on ne voit nulle part la cover. ON va revoir l'UI de catloging, car elle n'est pas pratique quand on scanne beaucop de livre a la suite. Il faudrait pouvoir passer d'un écran a l'autre sans devoir scroller, Il faut revoir la disposition des bouton et aussi ajouter des racourci clavier. ET également pouvoir recommencer au nouveau livre facilement. Peut etre que le process en trois étapdes soit sauvegardé dans l'url pour pouvori faire retour arriere ?"

## User Scenarios & Testing

### User Story 1 - Catalog books in a fast scanning sequence (Priority: P1)

A librarian scans a book identifier, finds or enters its bibliographic notice, adds a physical copy, then starts the next book without losing time to scrolling or navigating away from the workflow.

**Why this priority**: Cataloging many books consecutively is the primary workflow and the current layout slows each book down.

**Independent Test**: Complete a new-book workflow at a standard laptop viewport, add one copy, and begin another book without scrolling the page.

**Acceptance Scenarios**:

1. **Given** the librarian opens cataloging, **When** the first step is displayed, **Then** the scan field and its primary action are visible and ready for input.
2. **Given** a notice is found or entered, **When** the librarian proceeds through the workflow, **Then** the primary action for each step is visible without page scrolling.
3. **Given** a copy has been added, **When** the librarian chooses to catalog another book, **Then** the workflow returns to identifier entry and is ready for the next scan.

### User Story 2 - Move between workflow steps with keyboard and browser navigation (Priority: P1)

A librarian can use Enter to advance the current cataloging action, Escape to return to the beginning for a new book, and browser Back to revisit a prior step. The URL identifies the current step and active ISBN, ISSN, text query, or saved record; saved notices and copies are reloaded from the catalog.

**Why this priority**: Frequent scanning benefits from fewer mouse actions, and browser navigation should follow the actual persisted workflow rather than maintaining a separate unsaved draft.

**Independent Test**: Scan an ISBN, save a notice and a copy, navigate backward and forward, and verify that the URL and displayed persisted data match the current step.

**Acceptance Scenarios**:

1. **Given** a cataloging step is active, **When** the librarian presses Enter, **Then** the current step's primary action runs and the next step receives focus.
2. **Given** the librarian is in the workflow, **When** Escape is pressed, **Then** the workflow returns to the lookup field for a new book without deleting saved notices or copies.
3. **Given** a notice or copy has been saved, **When** browser Back or Forward changes the workflow step, **Then** the URL identifies that step and any saved data is loaded from the catalog.

### User Story 3 - Find a book by title when its ISBN is unavailable (Priority: P1)

A librarian can search the local catalog by a title or other text first, then search remote book catalogs when there is no local match. The librarian can compare multiple remote candidates, use their covers to identify the right edition, and select the intended record before entering copy details.

**Why this priority**: Many books cannot be scanned because the ISBN is absent or unreadable; searching by title lets the librarian continue without manually rebuilding all bibliographic data.

**Independent Test**: Search for a title with no local match, review selectable remote results with available covers, select one, and verify its bibliographic fields prefill the notice form.

**Acceptance Scenarios**:

1. **Given** a title or free-text query is entered, **When** local search completes with no match, **Then** the first enabled remote book source is searched.
2. **Given** a remote source returns several candidates, **When** its results are shown, **Then** each candidate displays its title and available identifying details and cover, and none is selected automatically.
3. **Given** the librarian chooses a candidate, **When** it is selected, **Then** the bibliographic form is prefilled from that candidate and can be reviewed before saving.
4. **Given** the first source returns no results or is unavailable, **When** the librarian continues, **Then** the next enabled book source can be searched or the librarian can continue with manual entry.
5. **Given** no local or remote result is suitable, **When** the librarian chooses manual entry, **Then** the title query is retained as the initial title without being treated as an ISBN.

### User Story 4 - See the book cover throughout cataloging (Priority: P2)

The librarian can see an available cover while reviewing bibliographic information and while adding a physical copy.

**Why this priority**: A visible cover helps confirm that the scanned identifier resolved to the intended book and clarifies the current omission in the copy-creation step.

**Independent Test**: Catalog a book with an available cover and verify it is visible in the bibliographic review and copy-creation views.

**Acceptance Scenarios**:

1. **Given** a local or provider cover is available, **When** the librarian reviews the notice, **Then** the cover is displayed next to the book information.
2. **Given** the librarian proceeds to add a copy, **When** the copy-creation step is displayed, **Then** the same cover remains visible.
3. **Given** no cover is available, **When** any step is displayed, **Then** the workflow remains usable and does not show a broken-image placeholder.

### Edge Cases

- The cover URL is missing, invalid, or the image request fails.
- A scanner submits an identifier while the librarian is on a different step.
- The librarian goes back after saving a notice or copy; navigation must not undo the saved data.
- The browser is refreshed or navigates away before an unsaved notice has been saved.
- A notice already exists locally and the librarian is adding another physical copy.
- The final copy action succeeds but the librarian immediately starts another book.
- A remote search returns incomplete or duplicate candidate data, or one provider times out while another remains available.
- A remote candidate has no ISBN or cover image.

## Requirements

### Functional Requirements

- **FR-001**: The cataloging workflow MUST present its primary action and essential step content without requiring page scrolling at a standard laptop viewport.
- **FR-002**: The workflow MUST clearly indicate the current step and provide consistently placed controls to proceed, go back, and cancel.
- **FR-003**: Enter MUST run the primary action for the current step; Escape MUST return to lookup to begin another book. Keyboard behavior MUST be contextual to the active input and MUST NOT trigger the same action twice.
- **FR-004**: The URL MUST identify the current cataloging step and its active ISBN, ISSN, text query, or saved record identifier. Browser Back and Forward MUST navigate between valid workflow steps and reload saved notices and copies from the catalog. Unsaved notice-form fields are not a persisted draft; only the active lookup value may be retained, and those fields MUST NOT be represented as saved data in the URL.
- **FR-005**: When a cover is available, the workflow MUST display it during bibliographic review and copy creation; when absent or unavailable, the workflow MUST remain usable without a broken-image placeholder.
- **FR-006**: The existing actions to start over, catalog another book, and navigate workflow steps MUST be repositioned so they are visible without scrolling; no duplicate actions are required. The existing new-book action MUST return to ISBN entry and focus the scan field.
- **FR-007**: Browser navigation MUST NOT delete or undo a notice or copy that has already been saved. Returning to a saved step MUST show the persisted catalog data; unsaved form changes may be discarded when the librarian explicitly starts another book.
- **FR-008**: For a free-text query, the workflow MUST search the local catalog first. Only when no local match exists may it search enabled remote sources (BnF, Google Books, and SUDOC). Existing ISBN/ISSN lookup behavior MUST remain unchanged.
- **FR-009**: Remote text-search results MUST be presented as a selectable list showing available title, author, publisher/year, source, and cover information. The workflow MUST NOT automatically select a text-search result; selecting one MUST prefill the bibliographic form for review.
- **FR-010**: Remote text searches MUST return a bounded candidate list. A provider with no results, disabled configuration, timeout, or error MUST NOT prevent searching the next enabled source or continuing with manual entry.
- **FR-011**: The URL MUST retain the active lookup value (ISBN, ISSN, or text) while it is unsaved, and retain the saved record identifier after a notice is persisted. Remote result details and unsaved form fields MUST NOT be serialized into the URL.

### Key Entities

- **Workflow navigation state**: The active step and its ISBN or saved record identifier. It does not persist entered form data.
- **Bibliographic notice**: The book or periodical record being selected or created.
- **Physical copy**: The individual library item created from the selected notice.

### Assumptions and Constraints

- The workflow has no persistent unsaved draft. The active lookup value (ISBN, ISSN, or text) is retained in the URL through lookup and bibliographic entry; after a notice is saved, its catalog identifier is used to restore later steps. Reloading an unsaved bibliographic form restores at most the lookup value, not the other form fields.
- Browser history represents navigation only. It never reverses or deletes saved catalog records or copies.
- Existing workflow controls remain available; the feature changes their placement and visibility rather than adding duplicate buttons.
- Free-text searches can use BnF, Google Books, and SUDOC. Existing ISBN and ISSN searches retain their current source routing.

## Success Criteria

### Measurable Outcomes

- **SC-001**: At a 1280×720 viewport, the scan input and primary action for every cataloging step are visible without vertical scrolling.
- **SC-002**: A librarian can begin cataloging the next book with no more than one explicit action after finishing a copy.
- **SC-003**: All primary workflow actions can be completed using Enter and Escape without moving focus unexpectedly.
- **SC-004**: Browser Back and Forward restore the expected step and its persisted notice or copy data in all tested workflows.
- **SC-005**: When a cover is available, it is visible in both bibliographic review and copy creation; cover retrieval failure never blocks completion of cataloging.
- **SC-006**: For a text query with no local match, the librarian can see up to 10 selectable results from each searched remote source, with no candidate chosen automatically.
- **SC-007**: A provider timeout or error leaves a visible path to another enabled source or manual entry; it does not block the cataloging workflow.
