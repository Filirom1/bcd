# Browsing the catalog

Search and browse all books available in the library.

---

## Step 1 — Search for a book

Type a title, author, or ISBN number in the search bar.
Results appear immediately as you type.

![Catalog search bar with results](../images/catalog-01-search.png)

> **Tip:** Leave the search bar empty to display all books in the catalog.

## Step 2 — Check availability

Each book shows the number of available copies and the total number.
A green badge means at least one copy is available. A red badge means all copies are on loan.

![Search results with availability badges](../images/catalog-02-results.png)

## Step 3 — View the detail record

Click on a title to open the full book record.
You will find all copies, their status, and the recent loan history.

![Book detail record with copies listed](../images/catalog-03-detail.png)

> **Tip:** In the detail record, you can add a new copy by clicking "Add a copy".

---

## Admin menu actions

The **Admin** menu in the top right gives access to administrative actions:

| Action | Description |
|--------|-------------|
| **Add a book** | Goes directly to the cataloging page to create a new record. |
| **Import catalog** | Imports a list of books from a CSV file prepared in Excel or exported from BiblioPuce. |
| **Export catalog** | Exports the entire catalog as CSV for backup or migration to another system. |
| **Bulk edit** | Updates one or more fields for the selected records in one operation. |
| **Print labels** | Generates and prints barcode labels to stick on books before cataloging. |

### Bulk edit — available fields

Check the records to update, then click **Bulk edit**. You can update:

| Field | Description |
|-------|-------------|
| **Medium type** | Physical format (e.g., Book, Comic, Magazine). Values configured in Settings. |
| **Genre** | Literary sub-category (e.g., Fantasy, Mystery). Values configured in Settings. |
| **Audience** | Child / Youth / Adult. |
| **Language** | Language of the book (e.g., French, English). Values configured in Settings. |

> **Tip:** Leave a field empty to skip it — only filled fields are updated.

### CSV import file format

The import file is a spreadsheet you prepare in **Excel** or **LibreOffice Calc**, or export directly from **BiblioPuce**.

**If you use BiblioPuce:** export your library as usual, then select the "BiblioPuce" format in the BCD import window. No other steps needed.

**If you prepare the file manually in Excel:**

1. Open a new Excel spreadsheet.
2. In **row 1**, type exactly these column headers (note the dot `.` in each name):

| Column header | What it contains | Required |
|---------------|-----------------|----------|
| `dc.title` | Book title | Yes |
| `dc.identifier` | ISBN number (13 digits on the back cover) | Recommended |
| `dc.creator` | Author(s). If multiple, separate with `\|` | No |
| `dc.publisher` | Publisher (e.g., Gallimard) | No |
| `dc.date` | Publication year (e.g., 2023) | No |
| `dc.language` | Language (write `fr` for French, `en` for English) | No |
| `dc.subject` | Keywords, separated by `\|` | No |
| `dc.description` | Book summary | No |
| `dc.type` | Document type (e.g., Book, Comic, Magazine) | No |
| `dc.format` | Physical format (e.g., paperback, hardcover) | No |

3. Fill in the following rows with one book per row.
4. Click **File → Save As**, then choose **CSV UTF-8 (comma delimited)**.

> **Tip:** Only the title (`dc.title`) is required. The more columns are filled in, the better the search results in the catalog.

> **Tip:** To use bulk edit, check the boxes on the left of the records first. Label printing does not require any prior selection.

### Harmonizing catalog data

The catalog can also be used to **correct and standardize field values** across a set of records in a few clicks — for medium types, genres, or languages.

**Example: unify genre variants**

You have records with `mystery`, `Mystery`, `Crime fiction` and want everything set to `Mystery`:

1. In the **Genre** field of the advanced filters, type `mystery`
2. Set the page size to **500** (at the bottom of the list) to see all results at once
3. Check the top checkbox to **select all**
4. Admin menu → **Bulk edit** → set `Genre = Mystery`
5. Confirm — all selected records are corrected in one operation

> **Tip:** Always review the search results before selecting all. Refine the filters if needed to target only the records you want to change.

**Other common uses:**
- Set audience for a genre: filter Genre = `Picture book` → set Audience = `Child`
- Fix language on an imported batch: filter Language = empty → set `French`

> **Known limitation:** Bulk edit replaces the entire value of a field. It cannot replace a substring (e.g., turning `"crime mystery novel"` into `"Mystery"` while keeping other values). In that case, work in two steps: filter on the exact value, then bulk edit.

---

## Printing barcode labels

BCD4 uses a **label-first** workflow: you print barcodes before cataloging the books, then scan the label during cataloging to assign it to the copy.

### Recommended workflow

1. **Admin → Print labels** — opens the label printing page.
2. Choose how many **labels** to print (the system automatically generates available IDs not yet in use).
3. Choose the **sheet format** matching your adhesive label sheets (the 21-labels-per-A4 format is recommended by default).
4. **Print** the sheets on A4 adhesive paper.
5. **Stick** the labels onto the books to catalog.
6. During **cataloging**, scan the label stuck on the book — it becomes the copy's inventory barcode.

> **Tip:** Cover printed labels with a self-adhesive plastic film: barcodes become hard to scan when the ink wears off. Pre-printed laminated labels on rolls last much longer.

### Available sheet formats

| Format | Labels per A4 | Label size | Recommended use |
|--------|---------------|------------|------------------|
| 8 | 8 | 99.1 × 67.7 mm | Large labels, DVD cases |
| 12 | 12 | 63.5 × 72.0 mm | Large labels |
| 14 | 14 | 99.1 × 38.1 mm | Wide format (DVDs, games) |
| 16 | 16 | 99.1 × 33.9 mm | Wide format |
| 18 | 18 | 63.5 × 46.6 mm | Intermediate size |
| **21** | **21** | **63.5 × 38.1 mm** | **Recommended for books** |
| 24 | 24 | 63.5 × 33.9 mm | Alternative format |
| 27 | 27 | 63.5 × 29.6 mm | Alternative format |
| 48 | 48 | 45.7 × 21.2 mm | Small labels |

### Advanced options

- **Start from**: sets the first ID in the series (useful to continue an existing numbering sequence).
- **Contiguous**: generates consecutive IDs (uncheck to fill gaps in the numbering instead).
- **Library name**: printed on each label (configured in Settings).
- **Advanced settings**: fine-tune margins and spacing if barcodes don’t align exactly on your sheets.

---

## Common Issues

| Problem | Solution |
|---------|----------|
| No results found | Check spelling or try with only part of the title or author name. |
| Book shows available but cannot be found on the shelf | Check the loan history in the detail record to see who borrowed it last. |
| ISBN returns no results | Some older books have no ISBN. Search by title or author instead. |
