# Settings

Configure loan rules and library options.

---

## Step 1 — Loan settings

These settings define the loan rules applied to all new checkouts.

![Main settings page](../images/settings-01-main.png)

### Detail of each setting

| Setting | Role | Default |
|---------|------|---------|
| **Loan duration (days)** | Number of days before the due date. Applies to all new checkouts. | 14 days |
| **Loan limit (students)** | Maximum number of books a student can have at the same time. | 3 books |
| **Loan limit (teachers)** | Maximum number of books a teacher can have at the same time. | 10 books |
| **Number of renewals** | How many times a loan can be extended without returning the book. Set to 0 to disallow renewals. | 2 |
| **Hold expiration (days)** | Number of days a borrower has to collect a book that has been put aside for them before the hold is cancelled. | 3 days |
| **Max active holds per borrower** | Maximum number of simultaneous holds (waiting or ready) a borrower can have at the same time. | 1 |
| **Current academic year** | Academic year label (e.g., 2024-2025). Used in reports. | — |

> **Tip:** Changes to loan duration or limits do not apply to loans already in progress.

## Step 2 — Barcode format

These settings allow the scanner to automatically distinguish student cards from book barcodes.

| Setting | Role | Example |
|---------|------|---------|
| **Borrower barcode prefix** | Character(s) added before the borrower number on cards. | `%` → card reads as `%12345` |
| **Item barcode prefix** | Character(s) added before the inventory number on book labels. | `.` → label reads as `.00785` |
| **ID format** | Validation format for borrower numbers (numeric, alphanumeric, custom). | numeric |

> **Tip:** If your scanner reads the raw number without a prefix, leave the prefix fields empty.

## Step 3 — Classification lists

These lists define the suggested values in cataloging forms and in bulk edit.

| Setting | Role |
|---------|------|
| **Medium types** | List of medium types (e.g., Book, Comic, Magazine, CD, DVD). |
| **Genres** | List of available genres (e.g., Adventure, Mystery, Fantasy, Historical). |
| **Languages** | Comma-separated list of ISO 639-1 language codes (e.g., `fr, en, es, de, ar`). These codes are used in cataloging forms and inventory filters. |

> **Tip:** These lists are suggestions only — you can always type a value not on the list.

**Best practices for keeping the catalog consistent:**

The classification lists act as a reference for the entire collection. The more carefully they are followed during cataloging, the fewer variants you will need to correct later (e.g., `mystery`, `Mystery`, `Crime fiction` all meaning the same thing).

- **Define the lists once, before you start cataloging**
- **Use simple, consistent names** to avoid duplicates (e.g., `Mystery` rather than `Crime mystery novel`)
- **Check regularly** via Catalog → advanced filters → genre/medium type empty or unusual → fix with bulk edit
- If a value is entered outside the list by mistake, it stays in the database until you correct it manually via bulk edit in the catalog

## Step 4 — Save settings

Click **"Save"** to apply all changes.
A confirmation message appears at the top of the screen.

---

## Common Issues

| Problem | Solution |
|---------|----------|
| The new loan duration does not apply to existing loans | Settings only apply to new loans. Existing loans keep their original due date. |
| The scanner cannot distinguish cards from books | Check that the borrower and item prefixes are configured correctly and are different. |
| Changes are not saved | Click the "Save" button to confirm the changes. |
