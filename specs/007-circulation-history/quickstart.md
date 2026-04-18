# Quickstart: Circulation History Pagination

**Feature**: 007-circulation-history
**Branch**: `007-circulation-history`

---

## Prerequisites

```bash
# Enter Nix dev shell (installs all dependencies, activates venv)
nix-shell

# Verify you're on the right branch
git branch --show-current   # should print: 007-circulation-history
```

---

## Run the server

```bash
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Apply the migration (after implementing)

```bash
# Apply the return_date index migration
alembic upgrade head

# Verify migration applied
alembic history
```

---

## Test the paginated endpoints manually

```bash
# Borrower history — page 1, default page size
curl "http://127.0.0.1:8000/api/v1/circulation/borrower/101/history"

# Borrower history — page 2
curl "http://127.0.0.1:8000/api/v1/circulation/borrower/101/history?page=2"

# Borrower history — filtered by date range
curl "http://127.0.0.1:8000/api/v1/circulation/borrower/101/history?date_from=2024-09-01&date_to=2025-06-30"

# Item history — page 1
curl "http://127.0.0.1:8000/api/v1/circulation/item/BK-00142/history"

# Item history — page 2 with date filter
curl "http://127.0.0.1:8000/api/v1/circulation/item/BK-00142/history?page=2&date_from=2024-01-01"
```

---

## Load realistic test data

Use the simulation script to generate a multi-year transaction history:

```bash
python reset_and_simulate.py
```

This generates ~500+ circulation transactions across 9 months of activity — enough to verify pagination works for borrowers and items with many historical records.

---

## Run the tests

```bash
# All tests
pytest

# Only circulation-related tests
pytest tests/integration/test_circulation_service.py -v

# New pagination-specific tests
pytest tests/integration/test_circulation_history_pagination.py -v

# With coverage
pytest tests/integration/test_circulation_history_pagination.py --cov=src/bcd_api/services/circulation_service --cov-report=term-missing
```

---

## Verify in the web UI

1. Open `http://127.0.0.1:8000` in a browser
2. Navigate to **Borrowers** → open any borrower with many past loans
3. Click the **History** tab → verify paginated table with Previous/Next controls and date filter
4. Navigate to **Catalog** → open any frequently borrowed book → **History** tab → verify same

---

## Verify i18n

Switch the UI language to French:
1. Open the app settings or language toggle
2. Verify the History tab shows French labels:
   - "Du" / "Au" for date range
   - "Appliquer" / "Effacer" for filter buttons
   - "Précédent" / "Suivant" for page navigation
   - "Aucun historique trouvé pour cette période." for empty filtered results
