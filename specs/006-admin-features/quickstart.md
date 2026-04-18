# Quickstart Guide: Admin Features Development

**Feature**: 006-admin-features
**Date**: 2026-02-07
**Version**: 1.0.0

## Overview

This guide helps developers quickly set up and test the admin features locally. It covers:
1. Development environment setup
2. Running the application
3. Testing admin endpoints with sample data
4. Frontend development workflow
5. Common troubleshooting

---

## Prerequisites

- Python 3.11+ installed
- Git repository cloned
- Nix (recommended) or manual venv setup

---

## 1. Environment Setup

### Option A: Using Nix (Recommended for NixOS)

```bash
# Enter Nix development shell (auto-creates venv and installs dependencies)
nix-shell

# The shell.nix provides:
# - Python 3.13 with pre-built packages
# - Automatic venv creation and activation
# - Playwright browsers configured
# - PYTHONPATH set to include src/
# - .env created from .env.example if missing
```

### Option B: Manual Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Initialize database
alembic upgrade head
```

---

## 2. Load Sample Data

### Reset Database and Simulate Realistic Data

```bash
# Reset database and simulate 9 months of library activity
python reset_and_simulate.py

# This script:
# - Resets database completely (deletes bcd.db and runs migrations)
# - Imports catalog from data/sample_imports/catalog_dublin_core.csv
# - Imports students from data/sample_imports/students_import.csv
# - Simulates 9 months of activity (Sep 2024 - May 2025)
#   - Classes visit every 14 days on Fridays (alternating halves)
#   - Realistic borrowing patterns (1-2 books per student)
#   - 90% on-time returns, 10% late returns, 15% renewals
#   - Generates ~500+ circulation transactions with overdue items
```

**Sample Data Includes**:
- **10 classes**: CP-A, CP-B, CE1-A, CE1-B, CE2-A, CE2-B, CM1-A, CM1-B, CM2-A, CM2-B
- **~500 students**: Assigned to classes with realistic French names
- **~5,000 bibliographic records**: French children's books with ISBNs
- **~7,500 items**: Physical copies with barcodes
- **~500 circulation transactions**: Mix of active loans and returned items

---

## 3. Start the Application

### Start API Server

```bash
# Start API server with web UI
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000 --reload

# --reload enables auto-restart on file changes (development mode)
```

**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Access Web UI

Open browser: **http://127.0.0.1:8000**

**Navigation**:
- **Borrowers Page**: http://127.0.0.1:8000/borrowers
- **Catalog Page**: http://127.0.0.1:8000/catalog
- **Classes Page**: http://127.0.0.1:8000/classes (NEW)

### Access API Documentation

- **Swagger UI**: http://127.0.0.1:8000/api/v1/docs
- **ReDoc**: http://127.0.0.1:8000/api/v1/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/api/v1/openapi.json

---

## 4. Testing Admin Endpoints

### Using Swagger UI (Recommended for Manual Testing)

1. Open http://127.0.0.1:8000/api/v1/docs
2. Expand admin-borrowers or admin-catalog tag
3. Click "Try it out" on any endpoint
4. Fill in request body and click "Execute"

### Using curl

#### Class Management

**List Classes**:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/classes?limit=10" \
  -H "accept: application/json"
```

**Create Class**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/classes" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CP-C",
    "grade_level": "CP",
    "academic_year": "2025-2026",
    "homeroom_teacher": "Mme Dupont",
    "notes": "New class"
  }'
```

**Update Class**:
```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/classes/1" \
  -H "Content-Type: application/json" \
  -d '{
    "homeroom_teacher": "M. Bernard",
    "notes": "Updated teacher"
  }'
```

**Delete Class** (unassigns students):
```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/classes/1" \
  -H "accept: application/json"
```

#### Borrower Single Edit

**Update Borrower**:
```bash
# Get borrower ID first
BORROWER_ID=$(curl -s "http://127.0.0.1:8000/api/v1/borrowers?limit=1" | jq -r '.[0].id')

# Update borrower
curl -X PATCH "http://127.0.0.1:8000/api/v1/borrowers/$BORROWER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Marie",
    "last_name": "DUBOIS",
    "email": "marie.dubois@example.com"
  }'
```

#### Borrower Bulk Operations

**Bulk Change Class**:
```bash
# Get 3 borrower IDs from CP-A
BORROWER_IDS=$(curl -s "http://127.0.0.1:8000/api/v1/borrowers?limit=3" | jq -r '[.[].id]')

# Change their class to CE1-A (class_id=3)
curl -X POST "http://127.0.0.1:8000/api/v1/admin/borrowers/bulk-edit" \
  -H "Content-Type: application/json" \
  -d "{
    \"operation\": \"change_class\",
    \"borrower_ids\": $BORROWER_IDS,
    \"target_class_id\": 3
  }"
```

**Bulk Change Role**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/borrowers/bulk-edit" \
  -H "Content-Type: application/json" \
  -d "{
    \"operation\": \"change_role\",
    \"borrower_ids\": [123, 124],
    \"target_role\": \"teacher\"
  }"
```

**Bulk Delete Borrowers**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/borrowers/bulk-delete" \
  -H "Content-Type: application/json" \
  -d '{
    "borrower_ids": [123, 124, 125]
  }'
```

#### Catalog Bulk Operations

**Bulk Edit Records**:
```bash
# Get 3 record IDs
RECORD_IDS=$(curl -s "http://127.0.0.1:8000/api/v1/catalog/records?limit=3" | jq -r '[.[].id]')

# Update common fields
curl -X POST "http://127.0.0.1:8000/api/v1/admin/catalog/bulk-edit" \
  -H "Content-Type: application/json" \
  -d "{
    \"record_ids\": $RECORD_IDS,
    \"fields\": {
      \"category\": \"Fiction\",
      \"genre\": \"Album\",
      \"target_audience\": \"child\"
    }
  }"
```

**Bulk Delete Records** (CASCADE deletes items):
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/catalog/bulk-delete" \
  -H "Content-Type: application/json" \
  -d '{
    "record_ids": [456, 457, 458]
  }'
```

---

## 5. Frontend Development Workflow

### File Structure

```
src/bcd_web_vue/
├── js/
│   ├── components/
│   │   ├── admin/
│   │   │   ├── AdminDropdown.js          # NEW: Reusable admin dropdown
│   │   │   ├── BulkEditModal.js          # NEW: Bulk operations modal
│   │   │   ├── ConfirmDialog.js          # NEW: Confirmation dialog
│   │   │   └── ProgressIndicator.js      # NEW: Progress bar
│   │   ├── borrowers/
│   │   │   ├── BorrowerList.js           # MODIFY: Add admin dropdown
│   │   │   ├── BorrowerEditForm.js       # NEW: Single edit modal
│   │   │   └── BorrowerImport.js         # MODIFY: Move to admin dropdown
│   │   ├── catalog/
│   │   │   ├── SearchResults.js          # MODIFY: Add admin dropdown
│   │   │   ├── RecordEditForm.js         # NEW: Single edit modal
│   │   │   └── CatalogImport.js          # MODIFY: Move to admin dropdown
│   │   └── classes/
│   │       ├── ClassList.js              # NEW: Classes table
│   │       ├── ClassForm.js              # NEW: Create/edit modal
│   │       └── ClassDeleteDialog.js      # NEW: Delete confirmation
│   ├── pages/
│   │   ├── BorrowersPage.js              # MODIFY: Integrate AdminDropdown
│   │   ├── CatalogPage.js                # MODIFY: Integrate AdminDropdown
│   │   └── ClassesPage.js                # NEW: Classes management
│   ├── composables/
│   │   ├── useBulkOperations.js          # NEW: Bulk edit/delete logic
│   │   └── useSelection.js               # NEW: Multi-select checkbox logic
│   └── router.js                         # MODIFY: Add /classes route
└── locales/
    ├── en.json                           # MODIFY: Add admin UI strings
    └── fr.json                           # MODIFY: Add admin UI strings
```

### Development Server (Auto-Reload)

The `--reload` flag in uvicorn watches for file changes and auto-restarts the server.

**Files watched**:
- `src/bcd_api/**/*.py` (backend)
- `src/bcd_web_vue/**/*.js` (frontend - served as static files)
- `src/bcd_web_vue/**/*.html`

**To test frontend changes**:
1. Edit `.js` file in `src/bcd_web_vue/js/`
2. Save file
3. Refresh browser (no need to restart server)

### Live Reload with Browser Extension (Optional)

Install browser extension for auto-refresh:
- Chrome/Edge: [Live Server Web Extension](https://chrome.google.com/webstore/detail/live-server-web-extension/fiegdmejfepffgpnejdinekhfieaogmj)
- Firefox: [Live Reload](https://addons.mozilla.org/en-US/firefox/addon/live-reload/)

---

## 6. Running Tests

### Run All Tests

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Suites

```bash
# Service-layer integration tests (admin operations)
pytest tests/integration/services/test_class_service.py -v
pytest tests/integration/services/test_borrower_service_bulk.py -v
pytest tests/integration/services/test_catalog_service_bulk.py -v

# API endpoint tests
pytest tests/integration/api/test_admin_endpoints.py -v
pytest tests/integration/api/test_classes_endpoints.py -v

# Unit tests
pytest tests/unit/ -v
```

### Run Tests on File Save (Watch Mode)

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests in watch mode
ptw -- -v tests/integration/services/
```

### Pre-Commit Hook (Prevent Commits with Failing Tests)

```bash
# Install pre-commit hook (run once)
./scripts/install-hooks.sh

# The hook will:
# - Automatically run tests before each commit
# - Block commits if any tests fail
# - Ensure code quality
```

---

## 7. Database Inspection

### SQLite Browser (GUI)

Install DB Browser for SQLite: https://sqlitebrowser.org/

```bash
# Open database
db-browser-sqlite bcd.db
```

**Useful Queries**:

```sql
-- View all classes with student count
SELECT c.id, c.name, c.grade_level, c.academic_year, COUNT(b.id) AS student_count
FROM class c
LEFT JOIN borrower b ON b.class_id = c.id
GROUP BY c.id
ORDER BY c.name;

-- View borrowers by class
SELECT b.borrower_id, b.full_name, b.role, c.name AS class_name
FROM borrower b
LEFT JOIN class c ON b.class_id = c.id
ORDER BY c.name, b.full_name;

-- View circulation history (with CASCADE delete relationships)
SELECT ct.id, b.full_name AS borrower, br.title, i.item_id, ct.checkout_date, ct.due_date, ct.return_date
FROM circulation_transaction ct
JOIN borrower b ON ct.borrower_id = b.id
JOIN item i ON ct.item_id = i.id
JOIN bibliographic_record br ON ct.bibliographic_record_id = br.id
ORDER BY ct.checkout_date DESC
LIMIT 20;

-- Test CASCADE delete (verify FK relationships)
PRAGMA foreign_key_list(borrower);  -- Should show class_id with ON DELETE SET NULL
PRAGMA foreign_key_list(item);      -- Should show bibliographic_record_id with ON DELETE CASCADE
```

### Command Line SQLite

```bash
# Open database in CLI
sqlite3 bcd.db

# Enable foreign keys (verify CASCADE works)
sqlite> PRAGMA foreign_keys = ON;

# Show tables
sqlite> .tables

# Describe table schema
sqlite> .schema borrower

# Run query
sqlite> SELECT COUNT(*) FROM borrower;

# Exit
sqlite> .exit
```

---

## 8. Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution**: Ensure `PYTHONPATH` includes project root:

```bash
export PYTHONPATH=/home/nixos/src/local/bcd4:$PYTHONPATH
# Or use nix-shell which sets this automatically
```

### Issue: "alembic.util.exc.CommandError: Can't locate revision identified by 'head'"

**Solution**: Reset migrations:

```bash
# Delete database
rm bcd.db

# Run migrations
alembic upgrade head

# Load sample data
python reset_and_simulate.py
```

### Issue: "sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed"

**Solution**: Enable foreign keys in SQLite (should be automatic):

```python
# In src/bcd_api/core/database.py
# Verify this event listener exists:
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### Issue: "Port 8000 already in use"

**Solution**: Kill existing process:

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8001
```

### Issue: "CSS/JavaScript not loading (404 errors)"

**Solution**: Verify static file mounting in `src/bcd_api/main.py`:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="src/bcd_web_vue"), name="static")
```

### Issue: "Frontend error: 'Cannot read property of undefined'"

**Solution**: Check browser console for errors. Common causes:
- API endpoint not returning expected structure
- Missing error handling in frontend
- i18n translation key not found

**Debug Steps**:
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for API response
4. Verify API response matches expected schema

---

## 9. Sample API Requests (Postman Collection)

### Import Postman Collection

Create file `admin-features.postman_collection.json`:

```json
{
  "info": {
    "name": "BCD Admin Features",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Classes",
      "item": [
        {
          "name": "List Classes",
          "request": {
            "method": "GET",
            "url": "http://127.0.0.1:8000/api/v1/classes?limit=10"
          }
        },
        {
          "name": "Create Class",
          "request": {
            "method": "POST",
            "url": "http://127.0.0.1:8000/api/v1/classes",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"name\": \"CP-C\",\n  \"grade_level\": \"CP\",\n  \"academic_year\": \"2025-2026\"\n}"
            }
          }
        },
        {
          "name": "Delete Class",
          "request": {
            "method": "DELETE",
            "url": "http://127.0.0.1:8000/api/v1/classes/1"
          }
        }
      ]
    },
    {
      "name": "Bulk Operations",
      "item": [
        {
          "name": "Bulk Change Class",
          "request": {
            "method": "POST",
            "url": "http://127.0.0.1:8000/api/v1/admin/borrowers/bulk-edit",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"operation\": \"change_class\",\n  \"borrower_ids\": [1, 2, 3],\n  \"target_class_id\": 2\n}"
            }
          }
        },
        {
          "name": "Bulk Delete Borrowers",
          "request": {
            "method": "POST",
            "url": "http://127.0.0.1:8000/api/v1/admin/borrowers/bulk-delete",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"borrower_ids\": [1, 2, 3]\n}"
            }
          }
        }
      ]
    }
  ]
}
```

Import in Postman: **File → Import → Upload Files**

---

## 10. Next Steps

### Implementation Checklist

After reviewing this quickstart:

1. ✅ **Environment setup**: Verify development environment works
2. ✅ **Sample data loaded**: Run `reset_and_simulate.py`
3. ✅ **API endpoints accessible**: Test with Swagger UI
4. ⏭️ **Implement service layer**: Start with `class_service.py` CRUD operations
5. ⏭️ **Write integration tests**: Test service methods with sample data
6. ⏭️ **Implement API endpoints**: Create admin routes
7. ⏭️ **Implement frontend components**: Create admin dropdown, bulk edit modal
8. ⏭️ **Add i18n strings**: Update en.json and fr.json
9. ⏭️ **Manual testing**: Use web UI to test all admin operations
10. ⏭️ **Pre-commit hook**: Ensure all tests pass before committing

### Code Review Preparation

Before submitting code for review:

1. Run full test suite: `pytest --cov=src`
2. Check coverage report (target 80%+)
3. Verify i18n completeness (all error codes translated)
4. Test on legacy hardware (5+ year old laptop)
5. Run `/speckit.review` to validate constitution compliance

---

## 11. Useful Commands Reference

```bash
# Development
python -m uvicorn src.bcd_api.main:app --reload  # Start dev server
pytest --cov=src -v                               # Run tests with coverage
ptw -- -v tests/integration/                      # Watch mode tests

# Database
alembic upgrade head                              # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
python reset_and_simulate.py                      # Reset DB + load sample data
sqlite3 bcd.db                                    # Open DB in CLI

# Code Quality
black src/ tests/                                 # Format code
ruff src/ tests/                                  # Lint code
pytest --cov=src --cov-report=html                # Coverage report

# Git
./scripts/install-hooks.sh                        # Install pre-commit hook
git status                                        # Check status
git add .                                         # Stage changes
git commit -m "feat: add admin features"          # Commit (tests run automatically)
```

---

## 12. Additional Resources

- **OpenAPI Docs**: http://127.0.0.1:8000/api/v1/docs
- **Project Constitution**: `.specify/memory/constitution.md`
- **Architecture Patterns**: `.specify/architecture-patterns.md`
- **Feature Spec**: `specs/006-admin-features/spec.md`
- **Data Model**: `specs/006-admin-features/data-model.md`
- **API Contract**: `specs/006-admin-features/contracts/api-endpoints.yaml`
- **Error Codes**: `specs/006-admin-features/contracts/error-codes.md`

---

## Document Status

**Status**: ✅ Complete
**Reviewed**: 2026-02-07
**Next Steps**: Begin implementation with `/speckit.tasks` to generate task list

---

**Happy Coding!** 🚀

If you encounter any issues not covered in this guide, please update this document or reach out to the team.
