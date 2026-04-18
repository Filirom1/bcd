# Reports

View reports to monitor library activity and manage overdue items.

---

## Step 1 — Choose a report type

Three reports are available in the tabs at the top of the page:
- **Overdue**: list of books not returned on time, grouped by class
- **Most borrowed**: ranking of the most popular titles
- **CREW - Weeding**: systematic collection evaluation using the CREW method
- **Holds**: list of active reservations and their status
- **Active loans**: list of all items currently on loan
- **Holds**: list of active reservations and their status
- **Active loans**: list of all items currently on loan

![Report type selection tabs](../images/reports-01-tabs.png)

## Step 2 — View the overdue report

The overdue report shows all loans whose due date has passed.
Loans are grouped by class to make follow-up easier.

![Overdue report grouped by class](../images/reports-02-overdue.png)

> **Tip:** Click on a student's name to open their record directly in the Borrowers page.

## Step 2b — Most borrowed report

Ranks titles by number of checkouts over a chosen period.
Useful for identifying popular titles and making reacquisition decisions.

**Available filters:**
- **Period**: last 30 days, last year, or all time
- **Number of results**: top 10, 25, or 50 titles

For each title, the report shows:
- Rank (gold/silver/bronze medals for the top 3)
- Title and author (clickable to the catalog record)
- Total checkout count with a proportional visual bar

> **Acquisition tip**: Use this report alongside the CREW report. Weeding frees up space and budget; the most borrowed titles reveal the genres and themes in demand — targeted purchases in those categories maximize collection usage.

## Step 3 — CREW Weeding Report

The CREW report helps identify weeding candidates in a systematic and objective way. It uses multiple criteria to calculate a **CREW score** for each item.

![CREW method selection](../images/reports-04-crew-method.png)

### CREW Evaluation Methods

Choose a method based on your goals:

**1. Never Borrowed**
- Items never borrowed since acquisition
- Ideal for identifying books unsuited to your audience or poorly placed
- Filter by minimum age (6 months, 1 year, 2 years, 3 years)

**2. Low Circulation**
- Items with 2 or fewer checkouts in the last 2 years
- Helps identify books that are no longer circulating
- Useful for making room for new acquisitions

**3. Damaged + Old**
- Damaged items that have been in collection for 3+ years
- Priority weeding candidates (poor condition + age)
- Frees space for new items in good condition

**4. High Score (≥5)**
- Shows all items with a CREW score of 5 or higher
- Quick overview of priority weeding candidates
- Combines all weeding criteria (age, condition, circulation)

**5. Never Inventoried**
- Items never physically verified (minimum age: 1 year)
- Identifies potentially missing or lost items
- Useful for annual inventory and loss management

**6. Duplicate Low Demand**
- Titles with 3 or more copies and low average circulation
- Average circulation: less than 2 checkouts per copy over 2 years
- Helps reduce duplicate copies of low-demand titles to free up space

### CREW Score

Each item receives a **score from 0 to 7+** based on:
- 🟢 **Score 0-2**: Keep — recent item or in good condition
- 🟠 **Score 3-4**: Review — may need closer examination
- 🔴 **Score 5+**: Weed — priority weeding candidate

**Score calculation criteria:**
- **Age in collection**: +1 to +3 points (1 year = +1, 2 years = +2, 3+ years = +3)
- **Physical condition**: +2 points if damaged
- **Old publication** (nonfiction): +1 to +2 points if >5 years or >10 years
- **Zero circulation**: +2 points if never borrowed
- **Low circulation**: +1 point if only 1 checkout

### Advanced Filters

Refine your search with filters:
- **Medium Type**: Book, CD, DVD, etc.
- **Genre**: Adventure, Fantasy, Mystery, etc.
- **Level**: CP, CE1, CE2, CM1, CM2, etc.
- **Target Audience**: Child, Youth, Adult
- **Minimum Age**: Limit to items acquired more than X months ago

### Information Displayed

For each item, the report shows:
- **CREW score** with color-coded badge
- **Score reasons** (age, condition, circulation, etc.)
- **Barcode** and **title** (clickable to catalog record)
- **Medium type** and **physical condition**
- **Shelf location**
- **Age in collection** (in years and days)
- **Publication year**

![CREW results with scores](../images/reports-05-crew-results.png)

> **Tip:** Start with items scoring ≥5 and in damaged condition. Physically examine the item before making weeding decisions.

## Step 3 — Print or export

Click the "Print" button to open the print-optimized view.
The report can also be exported as a CSV file for processing in a spreadsheet.

![Report print button](../images/reports-03-print.png)

## Step 4 — Holds report

Lists all active reservations with their current status.

**Available filters:**
- **Class**: filter to see reservations for a specific group

For each hold, the report shows:
- Borrower name and class
- Reserved book title
- **Status** (colour-coded):
  - 🟦 **Waiting** — in the queue
  - 🟢 **Ready** — item is available, borrower can collect it
  - 🔴 **Expired** — not collected within the deadline
  - ⚪ **Cancelled / Fulfilled** — hold is closed
- **Queue position**
- **Expiration date**

## Step 5 — Active loans report

Lists all items currently on loan, grouped by class.

**Available filters:**
- **Class**: filter to show only one group

For each loan, the report shows:
- Borrower name
- Book title
- **Checkout date**
- **Due date**
- **Days remaining** (green badge if ≥4 days, orange if ≤3, red if overdue)

> **Tip:** Use this report to anticipate returns — filter by class to let a teacher know which books from their group are due back soon.

## Common Issues

| Problem | Solution |
|---------|----------|
| The overdue report is empty | No loans are currently overdue — that is good news! |
| A book still appears as overdue after being returned | Check in the book record that the return was properly recorded. |
| The "Never borrowed" report is very long | Filter by acquisition year to see recent acquisitions that have not yet been borrowed. |

> **Coming soon**: a **Global statistics** tab (total loans, active borrower rate, daily average, late return rate) is planned. The calculation engine is already in place, only the display is missing.
