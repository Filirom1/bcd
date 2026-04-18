# Quickstart: Aide Contextuelle Intégrée

**Branch**: `001-contextual-help`

---

## Development Setup

```bash
# From project root, ensure on feature branch
git checkout 001-contextual-help

# Activate nix-shell (handles Python venv + Playwright)
nix-shell

# Verify dependencies
python -c "import playwright; print('Playwright OK')"
python -m pytest --version
```

---

## Generate Realistic Test Data

```bash
# Reset DB and populate with 9 months of simulated activity
# + enriched scenarios (overdue, blocks, holds, teachers, in-repair items)
python scripts/reset_and_simulate.py
```

Expected output includes:
- `✓ Created teachers and staff (N borrowers)`
- `✓ Diversified item statuses (N lost, N in_repair)`
- `✓ Created demo holds (waiting: N, ready: N)`
- `✓ Created demo current loans (overdue: N, renewed: N, at-limit: N)`

---

## Generate Help Screenshots

```bash
# Terminal 1: Start server
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Generate screenshots (takes ~2 minutes)
python scripts/generate_help_screenshots.py
```

Expected: 21 PNG files created in `src/bcd_web_vue/help/images/`

---

## Test the Help Panel in Browser

```bash
# Server must be running
open http://127.0.0.1:8000/#/checkout
# Click "Aide" button in page header → panel should open from right
# Scroll through content → screenshots should display
# Switch language (FR→EN) → content should update
# Navigate to another page → panel should close
```

---

## Run Tests

```bash
# Unit/integration tests
pytest tests/unit/ tests/integration/ -v

# E2E tests (requires server running + simulated data)
pytest tests/e2e/test_help_panel.py -v

# Full E2E suite
pytest tests/e2e/ -v --headed  # --headed to see browser
```

---

## Verify All 8 Pages Have Help

| Page | URL | Help Section |
|------|-----|-------------|
| Emprunter | `/#/checkout` | checkout |
| Retourner | `/#/return` | return |
| Catalogue | `/#/catalog` | catalog |
| Catalogage | `/#/cataloging` | cataloging |
| Élèves | `/#/borrowers` | borrowers |
| Classes | `/#/classes` | classes |
| Rapports | `/#/reports/overdue` | reports |
| Paramètres | `/#/settings` | settings |

---

## Verify Simulation Scenarios

```bash
# After running reset_and_simulate.py, check key states in DB
python - <<'EOF'
import sqlite3
conn = sqlite3.connect('data/bcd.db')
c = conn.cursor()

print("=== Simulation Verification ===")

# Overdue loans
c.execute("SELECT COUNT(*) FROM circulation WHERE return_date IS NULL AND due_date < date('now')")
print(f"Active overdue loans: {c.fetchone()[0]} (expect > 0)")

# Blocked borrowers
c.execute("SELECT COUNT(*) FROM borrower WHERE active = 0")
print(f"Blocked borrowers: {c.fetchone()[0]} (expect > 0)")

# Holds waiting
c.execute("SELECT COUNT(*) FROM hold WHERE status = 'waiting'")
print(f"Holds waiting: {c.fetchone()[0]} (expect > 0)")

# Holds ready
c.execute("SELECT COUNT(*) FROM hold WHERE status = 'ready'")
print(f"Holds ready: {c.fetchone()[0]} (expect > 0)")

# Items in repair
c.execute("SELECT COUNT(*) FROM item WHERE status = 'in_repair'")
print(f"Items in repair: {c.fetchone()[0]} (expect > 0)")

# Renewed loans
c.execute("SELECT COUNT(*) FROM circulation WHERE renewal_count > 0 AND return_date IS NULL")
print(f"Renewed active loans: {c.fetchone()[0]} (expect > 0)")

# Teachers with loans
c.execute("""SELECT COUNT(*) FROM circulation c
    JOIN borrower b ON c.borrower_id = b.id
    WHERE b.role = 'teacher' AND c.return_date IS NULL""")
print(f"Teacher active loans: {c.fetchone()[0]} (expect > 0)")

conn.close()
EOF
```

---

## File Structure Reference

```
src/bcd_web_vue/
├── vendor/js/marked.min.js           # Markdown renderer
├── help/
│   ├── fr/                           # 8 French markdown files
│   ├── en/                           # 8 English markdown files
│   └── images/                       # 21 PNG screenshots
├── index.html                        # +marked.min.js script
├── css/main.css                      # +.help-markdown styles
├── locales/{fr,en}.json              # +help.* translation keys
└── js/
    ├── components/ui/HelpPanel.js    # Reusable offcanvas component
    └── pages/*.js                    # 7 pages modified

scripts/
├── reset_and_simulate.py             # Enriched simulation
└── generate_help_screenshots.py      # New screenshot script

tests/e2e/
└── test_help_panel.py                # New E2E tests
```
