# Cataloging Design Plan

## Goal

Make cataloging fast and simple when:

- a book has a supported ISBN;
- a periodical has an ISSN;
- a periodical has a press barcode that is not an ISBN, such as `3780237306003` for *Wapiti*;
- the librarian already knows that the bibliographic notice exists in the local catalog.

The librarian must never be forced to wait for several external services before being able to continue manually.

## Design principles

- One local computer per school.
- No multi-user concurrency design.
- No response cache.
- No local database of French press codes.
- No background jobs, WebSockets, SSE, or complex lookup orchestration.
- One cataloging screen with one main search field.
- Search the local catalog before calling any external service.
- A barcode is an input hint, not necessarily an ISBN.
- A bibliographic notice and a physical copy are different things.

## Main screen

The first cataloging screen should be renamed conceptually from **ISBN lookup** to **Find a notice**.

```text
Add to catalog

Scan or enter an ISBN, ISSN, barcode, or title
[                                             ] [Search]

[Create a new notice manually]
```

The same field accepts:

- ISBN-10 or ISBN-13;
- ISSN;
- EAN-13 periodical barcode;
- unsupported press barcode;
- title;
- title and issue number;
- author or other text.

The user does not need to select a search mode first.

## Search order

### 1. Local catalog search

Always search the local catalog first. This search must be immediate and must not call an external service.

Search fields:

- exact ISBN;
- exact ISSN;
- title;
- title without a periodical issue suffix;
- author;
- the entered barcode as raw text.

If a matching notice is found, display it immediately and let the librarian select it.

### 2. External lookup only when appropriate

External services are called only when the local catalog has no suitable notice.

The automatic source order is fixed and simple:

```text
ISBN       -> BnF -> Google Books
ISSN/977   -> SUDOC
Unknown barcode -> ask for title -> local catalog search
```

There is no automatic SUDOC ISBN rescue step after BnF and Google Books.

### ISBN route

```text
Local catalog
    -> BnF
    -> Google Books
    -> Manual entry
```

BnF is the primary source for French books. Google Books is tried if BnF does not return a usable result.

Suggested default timeout:

- BnF: 4 seconds;
- Google Books: 4 seconds.

The automatic ISBN lookup must therefore finish or become manually bypassable within approximately 8 seconds.

### ISSN route

```text
Local catalog
    -> SUDOC
    -> Manual entry
```

ISSN is the normal route for periodicals. BnF and Google Books must not be called for an ISSN.

Suggested default timeout:

- SUDOC: 4–5 seconds.

### EAN-977 route

An EAN-13 beginning with `977` is treated as a periodical barcode from which an ISSN can be derived.

```text
EAN-977
    -> extract ISSN
    -> local catalog search
    -> SUDOC if not found locally
    -> Manual entry
```

### Unsupported press barcode route

For a barcode such as:

```text
3780237306003
```

BCD must not treat the value as an ISBN. It should display an inline message:

```text
This barcode is not a supported ISBN or ISSN.

Search for the notice by title:
[                                             ] [Search]
```

The original barcode remains visible in the current cataloging draft, but it is not automatically stored as an ISBN.

The user can enter:

```text
Wapiti
```

The local catalog search then returns the existing `Wapiti` notice.

No French press-code mapping table is required.

## Example: Wapiti number 440

### Input

```text
3780237306003
```

### Screen response

```text
Unsupported bibliographic barcode.
Search for the notice by title:
[ Wapiti                                      ] [Search]
```

### Local result

```text
Wapiti
Periodical · ISSN 0984-2314 · Milan
Existing copies: 12

[Use this notice]
```

### Add the physical copy

```text
Notice: Wapiti
ISSN: 0984-2314

Issue number:
[440]

Internal BCD barcode:
[Scan barcode]

[Create copy]
```

The press barcode and the internal BCD barcode are separate concepts. The press barcode must not automatically replace the internal copy barcode because it may not uniquely identify the physical copy or the issue.

## Existing-notice results

Results must be compact but sufficient for selecting the correct notice.

### Periodical result

```text
Wapiti
Periodical · ISSN 0984-2314
Publisher: Milan
Copies: 12
Issues already present: 147, 230, 414, 440
[Use this notice]
```

### Book result

```text
The Little Prince
Author: Antoine de Saint-Exupéry
Publisher: Gallimard · 1946
ISBN: 978...
Copies: 3
[Use this notice]
```

When several similar results exist, do not merge them automatically. Show the identifier, publisher, year, medium type, and copy count so the librarian can choose.

For periodicals, prefer the exact title with an ISSN over issue-like notices such as `Wapiti n°414` or `Wapiti: Touche pas à mon goûter`.

## Notice versus physical copy

The cataloging workflow has two distinct actions:

1. select or create a bibliographic notice;
2. add a physical copy to that notice.

For books:

```text
Select notice -> scan internal BCD barcode -> create copy
```

For periodicals:

```text
Select periodical notice -> enter issue number -> scan internal BCD barcode -> create copy
```

The periodical issue number must be presented as an explicit issue-number field. It should not be conceptually confused with the call number.

## External-source status

External lookup should remain on the same screen. A compact inline status area is enough:

```text
External search

BnF          Searching... 3.1 s       [Skip]
Google Books Waiting                    [Start]
SUDOC        Not applicable

[Continue with manual entry]
```

The librarian must be able to:

- skip the current source;
- start the next source;
- continue manually immediately;
- return to title search.

There is no need for a separate results window or a multi-source dashboard.

## Settings

Add a simple **External catalog sources** section in Settings.

```text
BnF          [enabled]    Timeout [4 s]
Google Books [enabled]    Timeout [4 s]
SUDOC        [enabled]    Timeout [5 s]
```

The settings should provide:

- enable/disable BnF;
- enable/disable Google Books;
- enable/disable SUDOC;
- timeout per source;
- a test button for each source.

The routing remains fixed:

- BnF and Google Books are used for ISBNs;
- SUDOC is used for ISSNs and periodicals;
- unsupported barcodes are handled through title search.

No priority editor, press-code directory, cache management, or advanced source profiles are needed for this first version.

## Manual entry

The manual-entry action must always be visible and immediately usable:

```text
[Create a new notice manually]
```

It must be available:

- before external lookup;
- while a source is waiting;
- after a timeout;
- after no result;
- after an unsupported barcode.

If the librarian has already entered a title, ISBN, ISSN, or barcode, preserve that value when opening the manual form.

## Proposed user flows

### Existing book

```text
Enter title or ISBN
    -> local notice found
    -> select notice
    -> scan internal copy barcode
    -> create copy
```

### New book with ISBN

```text
Scan ISBN
    -> local catalog search
    -> BnF
    -> Google Books if needed
    -> review metadata
    -> create notice
    -> scan internal copy barcode
    -> create copy
```

### Existing periodical with ISSN

```text
Scan or enter ISSN
    -> local notice found or SUDOC lookup
    -> select/create periodical notice
    -> enter issue number
    -> scan internal copy barcode
    -> create copy
```

### Existing periodical with unsupported press barcode

```text
Scan press barcode
    -> barcode not interpreted as ISBN
    -> enter title, e.g. Wapiti
    -> local notice search
    -> select Wapiti
    -> enter issue number, e.g. 440
    -> scan internal copy barcode
    -> create copy
```

### New document without an identifier

```text
Enter title
    -> local search
    -> no notice found
    -> manual entry
    -> create notice
    -> scan internal copy barcode
    -> create copy
```

## Out of scope

This design deliberately does not include:

- a database of all French press codes;
- automatic mapping from every EAN press barcode to an ISSN;
- an external title-search cascade across all providers;
- SUDOC as an automatic ISBN fallback;
- response caching;
- concurrent external requests;
- background lookup jobs;
- automatic notice merging;
- automatic inference of the exact periodical issue from a press barcode.

## Success criteria

- A known local notice can be selected by title without any external request.
- `Wapiti` can be found by typing its title after scanning `3780237306003`.
- An ISSN uses SUDOC only.
- An ISBN uses BnF then Google Books.
- An unsupported barcode never waits through an ISBN lookup cascade.
- Manual entry is always available.
- Adding a periodical issue requires an explicit issue number.
- The librarian can move from scan to copy creation without creating a duplicate notice.
