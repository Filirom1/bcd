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
| **Languages** | Comma-separated list of ISO 639-1 language codes (e.g., `fr, en, es, de, ar`). These codes are used in cataloging forms and inventory filters. |

> **Tip:** These lists are suggestions only — you can always type a value not on the list.

**Best practices for keeping the catalog consistent:**

The classification lists act as a reference for the entire collection. The more carefully they are followed during cataloging, the fewer variants you will need to correct later (e.g., `mystery`, `Mystery`, `Crime fiction` all meaning the same thing).

- **Define the lists once, before you start cataloging**
- **Use simple, consistent names** to avoid duplicates (e.g., `Mystery` rather than `Crime mystery novel`)
- **Check regularly** via Catalog → advanced filters → medium type empty or unusual → fix with bulk edit
- If a value is entered outside the list by mistake, it stays in the database until you correct it manually via bulk edit in the catalog

## Step 4 — Dewey colors

The **color daisy** (marguerite des couleurs) assigns a color to each of the 10 main Dewey classes (000 to 900). These colors appear on call-number badges in the catalog and inventory, making it easy to spot a book's section at a glance.

| Class | Theme |
|-------|-------|
| **000** | General works, dictionaries, computing |
| **100** | Philosophy, psychology |
| **200** | Religion |
| **300** | Social sciences, education |
| **400** | Language |
| **500** | Natural sciences, mathematics |
| **600** | Technology, medicine, cookery |
| **700** | Arts, music, sport, leisure |
| **800** | Literature |
| **900** | History, geography, biographies |

**For each class you can:**
- **Enable or disable** the color with the checkbox (if disabled, the call number is shown without a color badge)
- **Pick the color** using the color picker

The default colors follow the **marguerite des couleurs** standard used in French school libraries.

> **Tip:** If you already color-code the physical labels on your books, configure the same colors here so the on-screen display matches what students see on the shelves.

## Step 5 — Shelf locations

This list defines the **physical locations** in your library (Fiction, Picture books, Comics, Non-fiction…). Each location can have its own color.

These locations appear as colored badges in:
- The **catalog** (search results and book records)
- The **inventory** (item list)
- The **cataloging** form (location picker instead of a free-text field)

**Managing the list:**
- **Add** a location: click "+ Add a location"
- **Name** each location in the text field (e.g., `Fiction`, `Picture books`)
- **Color** (optional): tick the checkbox then pick a color
- **Delete** a location: click the bin icon

> **Tip:** Use the same names as the physical signs on your shelves. Students will find books more easily if the on-screen names match what they see in the library.

## Step 6 — Automatic call number rules

These rules automatically pre-fill the **call number** of a book during cataloging based on its medium type and/or shelf location.

The system applies the **first matching rule (from top to bottom)**.

### Wildcard support (`*`)
To avoid duplicating rules when you have sub-locations or custom medium types, you can use the `*` character as a wildcard on both location and medium type fields:
- A location configured as `Documentaires*` will automatically match `Documentaires`, `Documentaires - Sciences`, `Documentaires - Nature`, etc.
- A medium type configured as `Book*` will match `Book`, `Book with CD`, etc.
- A value configured as `*` will match any text.

### Available placeholders for patterns:
- `{AUT1}` / `{AUT3}`: 1 or 3 first uppercase letters of the author's last name (normalized, no accents).
- `{SER1}` / `{SER3}`: 1 or 3 first uppercase letters of the collection/series (or author if empty).
- `{TIT1}` / `{TIT3}`: 1 or 3 first uppercase letters of the title (ignoring leading articles).
- `{DEWEY}`: The Dewey classification number (mostly used for non-fiction).

## Step 7 — Save settings

Click **"Save"** to apply all changes.
A confirmation message appears at the top of the screen.

---

## Common Issues

| Problem | Solution |
|---------|----------|
| The new loan duration does not apply to existing loans | Settings only apply to new loans. Existing loans keep their original due date. |
| The scanner cannot distinguish cards from books | Check that the borrower and item prefixes are configured correctly and are different. |
| Changes are not saved | Click the "Save" button to confirm the changes. |

---

## Step 8 — Advanced Settings (Configuration file .env)

For schools managing their own IT setup or wanting to customize backup locations, cover images folders, or the database path, BCD allows direct editing of its configuration file.

![Configuration file .env](../images/settings-env.png)

### Why customize these settings?
This section is aimed at people in charge of the school's IT setup (IT coordinators, local council technical team, etc.). It allows you to:
* **Switch the database**: to move from a local installation to a database shared between several computers in the school (PostgreSQL).
* **Change storage paths**: if you prefer to save automatic backups or downloaded cover images on a USB drive or network share instead of the main computer's hard drive.

### How to modify a setting?
1. Edit or add configuration lines directly in the text area. Lines starting with a `#` are informational comments.
2. Click **"Save"**.
3. **IMPORTANT:** You must fully restart the BCD application for these new folders or settings to take effect.

### All .env settings explained

Here is the complete list of settings you can customize in your `.env` file, grouped by category:

#### 1. Database & Custom Storage Folders
*Use these if you want to move folders to a network drive, a USB key, or to use an external PostgreSQL database.*

| Parameter | Default value | Description |
|-----------|---------------|-------------|
| **`DATABASE_URL`** | `sqlite:///./data/bcd.db` | **Database connection URL.** For SQLite: `sqlite:///path/to/bcd.db`. For PostgreSQL: `postgresql://user:password@host:port/dbname`. |
| **`DATA_DIR_PATH`** | `data` | **Data directory path.** Where local database and related files are stored. |
| **`CONFIG_DIR_PATH`** | `.` | **Configuration directory path.** Where the `.env` file and settings reside. |
| **`LOG_DIR_PATH`** | `logs` | **Logs directory path.** Where application error and activity logs are written. |
| **`COVERS_DIR_PATH`** | `data/covers` | **Covers storage path.** Folder where downloaded book cover images are saved. |
| **`BACKUPS_DIR_PATH`** | `backups` | **Backups folder path.** Folder where automatic database backups are exported. |

#### 2. Network & Server Configuration

| Parameter | Default value | Description |
|-----------|---------------|-------------|
| **`API_HOST`** | `127.0.0.1` | **Network bind address.** `127.0.0.1` allows local access only. Set to `0.0.0.0` to allow other computers on your network to connect to this server. |
| **`API_PORT`** | `8888` | **Port.** The network port used to access the BCD interface and API. |
| **`CORS_ORIGINS`** | `http://localhost:3000, http://localhost:8888` | Allowed origins for web requests (mostly used in development). |

#### 3. Client & Portable Mode Options

| Parameter | Default value | Description |
|-----------|---------------|-------------|
| **`CLIENT_ONLY`** | `false` | **Client-only mode.** If set to `true`, this machine will not run a database or local server. It will act purely as a terminal connecting to the remote server IP specified in `API_HOST`. |
| **`UI_MODE`** | `webview` | **Startup interface.** Choose which window opens on startup:<br>- `webview`: Native desktop application window.<br>- `browser`: Opens the management portal in your system browser.<br>- `kids`: Launches the kid-friendly student client. |
| **`KIDS_CLIENT_PATH`** | *(empty)* | **Student client executable path.** Absolute or relative path to the BCD Kids student application executable (e.g. `BCD-Kids.exe` or `./BCD-Kids.x86_64`). |
| **`AUTO_UPDATE`** | `true` | **Automatic updates.** If `true`, checks GitHub for newer portable releases at startup and offers to update. |

#### 4. Security & Authentication

| Parameter | Default value | Description |
|-----------|---------------|-------------|
| **`AUTH_USERNAME`** | *(empty)* | **Admin/Librarian username.** Fill this to password-protect the librarian interface. |
| **`AUTH_PASSWORD`** | *(empty)* | **Admin/Librarian password.** Must be set along with `AUTH_USERNAME` to enable authentication. |
| **`AUTH_SCHEME`** | `basic` | **Authentication protocol.** Choose `basic` (standard, high compatibility) or `digest` (more secure over HTTP). |

#### 5. External Cataloging APIs (ISBN Lookups)
*Toggle these to enable/disable or rate-limit external books metadata search engines.*

| Parameter | Default value | Description |
|-----------|---------------|-------------|
| **`BNF_ENABLED`** | `true` | Enable/disable lookup on the French National Library (BnF). |
| **`BNF_API_URL`** | `https://catalogue.bnf.fr/api/SRU` | API endpoint for BnF. |
| **`BNF_RATE_LIMIT`** | `1` | Rate limit for BnF requests (requests per second; BnF requests maximum 1 req/sec). |
| **`GOOGLE_BOOKS_ENABLED`** | `true` | Enable/disable lookup on Google Books. |
| **`GOOGLE_BOOKS_API_KEY`** | *(empty)* | Optional API key to increase Google Books quota. |
| **`GOOGLE_BOOKS_RATE_LIMIT`** | `1` | Rate limit for Google Books (requests per second). |
| **`SUDOC_ENABLED`** | `true` | Enable/disable lookup on SUDOC (French university library catalog, great fallback). |
| **`SUDOC_API_URL`** | `https://www.sudoc.abes.fr/cbs/sru/` | API endpoint for SUDOC. |
| **`SUDOC_RATE_LIMIT`** | `1` | Rate limit for SUDOC requests (requests per second). |

#### 6. Development & Logs

| Parameter | Default value | Description |
|-----------|---------------|-------------|
| **`LOG_LEVEL`** | `INFO` | Verbosity of logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| **`ENVIRONMENT`** | `production` | Set to `development` to enable hot reload and detailed debug tools. |



