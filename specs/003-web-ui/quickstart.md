# Quick Start Guide: BCD Web UI

**Feature**: Localhost Web UI for BCD Library System
**Date**: 2026-01-30
**Audience**: Developers implementing the web UI

## Prerequisites

Before starting web UI development, ensure you have:

✅ **BCD API Server Running**
```bash
# From project root
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
```

✅ **Database Initialized**
```bash
alembic upgrade head
```

✅ **Sample Data Loaded** (for testing)
```bash
python -m src.bcd_cli.main catalog import data/sample_bibliographic.csv
python -m src.bcd_cli.main borrower import data/sample_borrowers.csv
```

---

## Step 1: Setup Development Environment

### 1.1 Install Additional Dependencies

```bash
# Add to requirements-dev.txt
pip install pytest-playwright
pip install jinja2  # For HTML templates

# Install Playwright browsers
playwright install
```

### 1.2 Verify API Access

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

curl http://localhost:8000/api/v1/borrowers?page=1&page_size=10
# Expected: JSON response with borrower list
```

---

## Step 2: Create Web UI Directory Structure

```bash
# From project root
mkdir -p src/bcd_web/{css,js/components,js/pages,locales,assets/icons,templates/fragments}

# Create main files
touch src/bcd_web/index.html
touch src/bcd_web/css/main.css
touch src/bcd_web/js/app.js
touch src/bcd_web/js/i18n.js
touch src/bcd_web/locales/fr.json
touch src/bcd_web/locales/en.json
```

**Directory Structure:**
```
src/bcd_web/
├── index.html              # SPA shell
├── css/
│   ├── main.css            # Custom styles
│   └── print.css           # Print stylesheet for reports
├── js/
│   ├── app.js              # Main application logic + routing
│   ├── api.js              # API client wrapper
│   ├── i18n.js             # Internationalization
│   ├── components/         # Reusable components
│   │   ├── navigation.js
│   │   ├── notification.js
│   │   └── forms.js
│   └── pages/              # Page-specific logic
│       ├── circulation.js
│       ├── catalog.js
│       └── borrowers.js
├── locales/
│   ├── fr.json             # French translations
│   └── en.json             # English translations
├── assets/
│   └── icons/              # SVG icons
└── templates/
    └── fragments/          # HTML templates for htmx
        ├── borrower_info.html
        ├── search_results.html
        └── ...
```

---

## Step 3: Create Minimal HTML Shell

Create `src/bcd_web/index.html`:

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BCD - Bibliothèque Centre Documentaire</title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link href="/static/css/main.css" rel="stylesheet">

    <!-- Print CSS -->
    <link href="/static/css/print.css" rel="stylesheet" media="print">

    <!-- htmx -->
    <script src="https://unpkg.com/[email protected]"></script>

    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="#" data-i18n="app.title">BCD</a>

            <!-- Language Switcher -->
            <div class="btn-group">
                <button type="button" class="btn btn-sm btn-light" onclick="i18n.switchLanguage('fr')">FR</button>
                <button type="button" class="btn btn-sm btn-light" onclick="i18n.switchLanguage('en')">EN</button>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container-fluid mt-3">
        <div id="app">
            <h1 data-i18n="app.title">Loading...</h1>
        </div>
    </div>

    <!-- Scripts -->
    <script src="/static/js/i18n.js"></script>
    <script src="/static/js/api.js"></script>
    <script src="/static/js/app.js"></script>

    <script>
        // Initialize application
        (async () => {
            await i18n.loadLocale(i18n.locale);
        })();
    </script>
</body>
</html>
```

---

## Step 4: Implement i18n System

Create `src/bcd_web/js/i18n.js`:

```javascript
class I18n {
    constructor() {
        this.locale = localStorage.getItem('locale') || 'fr';
        this.translations = {};
        this.initFormatters();
    }

    initFormatters() {
        this.dateFormatter = new Intl.DateTimeFormat(this.locale, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
        this.numberFormatter = new Intl.NumberFormat(this.locale);
        this.pluralRules = new Intl.PluralRules(this.locale);
    }

    async loadLocale(locale) {
        try {
            const response = await fetch(`/static/locales/${locale}.json`);
            this.translations = await response.json();
            this.locale = locale;
            this.initFormatters();
            localStorage.setItem('locale', locale);
            this.updateDOM();
        } catch (error) {
            console.error('Failed to load locale:', error);
        }
    }

    t(key, interpolations = {}) {
        const keys = key.split('.');
        let value = this.translations;
        for (const k of keys) {
            value = value?.[k];
            if (value === undefined) break;
        }

        if (typeof value !== 'string') {
            console.warn(`Missing translation: ${key}`);
            return key;
        }

        return value.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
            return interpolations[varName] ?? match;
        });
    }

    formatDate(date) {
        return this.dateFormatter.format(date);
    }

    updateDOM() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = this.t(key);
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
    }

    async switchLanguage(newLocale) {
        await this.loadLocale(newLocale);
        // Trigger page reload if needed for htmx content
        if (window.htmx) {
            document.querySelectorAll('[hx-get]').forEach(el => {
                htmx.trigger(el, 'refresh');
            });
        }
    }
}

const i18n = new I18n();
```

Create `src/bcd_web/locales/fr.json`:

```json
{
    "app": {
        "title": "BCD - Système de Bibliothèque",
        "subtitle": "Gestion de bibliothèque scolaire"
    },
    "navigation": {
        "circulation": "Circulation",
        "catalog": "Catalogue",
        "borrowers": "Emprunteurs",
        "reports": "Rapports",
        "settings": "Paramètres"
    },
    "circulation": {
        "checkout": "Emprunter",
        "return": "Retourner",
        "borrower_id": "Numéro d'emprunteur",
        "scan_item": "Scanner l'article"
    },
    "common": {
        "save": "Enregistrer",
        "cancel": "Annuler",
        "loading": "Chargement..."
    }
}
```

---

## Step 5: Configure FastAPI to Serve Static Files

Edit `src/bcd_api/main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(...)

# Add after existing middleware configuration

# Serve web UI static files
app.mount("/static", StaticFiles(directory="src/bcd_web"), name="static")

# Templates for htmx fragments
templates = Jinja2Templates(directory="src/bcd_web/templates")

# Serve SPA at root (must be last mount)
app.mount("/", StaticFiles(directory="src/bcd_web", html=True), name="web")
```

---

## Step 6: Test Initial Setup

### 6.1 Start Server

```bash
python -m uvicorn src.bcd_api.main:app --reload
```

### 6.2 Access Web UI

Open browser: `http://localhost:8000/`

You should see:
- Bootstrap-styled page
- "BCD - Système de Bibliothèque" title (in French)
- FR/EN language switcher buttons

### 6.3 Test Language Switching

Click "EN" button → Title should change to "BCD - Library System"

### 6.4 Verify Static Files

Check browser console (F12):
- No 404 errors for CSS/JS files
- i18n.js loaded successfully
- Translations loaded

---

## Step 7: Create First htmx Endpoint

### 7.1 Add Template

Create `src/bcd_web/templates/fragments/borrower_info.html`:

```html
<div class="card">
    <div class="card-body">
        <h5 class="card-title">{{ borrower.full_name }}</h5>
        <p class="text-muted">{{ borrower.class_name }}</p>
        <div class="badge bg-{{ 'success' if borrower.current_loans < borrower.loan_limit else 'danger' }}">
            {{ borrower.current_loans }}/{{ borrower.loan_limit }} emprunts
        </div>
    </div>
</div>
```

### 7.2 Add Dual-Response Endpoint

Edit `src/bcd_api/api/v1/borrowers.py`:

```python
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="src/bcd_web/templates")

@router.get("/borrowers/{borrower_id}")
async def get_borrower(
    borrower_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    borrower = await borrower_service.get_by_id(db, borrower_id)

    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")

    # Check if request is from htmx
    if "HX-Request" in request.headers:
        return templates.TemplateResponse("fragments/borrower_info.html", {
            "request": request,
            "borrower": borrower
        })

    # Standard JSON response
    return borrower
```

### 7.3 Test htmx Integration

Add to `index.html`:

```html
<div id="test-htmx">
    <input type="text"
           id="borrower-id-test"
           hx-get="/api/v1/borrowers/101"
           hx-trigger="change"
           hx-target="#borrower-result"
           placeholder="Enter 101">
    <div id="borrower-result"></div>
</div>
```

Type "101" and press Enter → Should load borrower info card

---

## Step 8: Create E2E Test

Create `tests/e2e/conftest.py`:

```python
from multiprocessing import Process
import pytest
import uvicorn
import time
from src.bcd_api.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8888, log_level="error")

@pytest.fixture(scope="session")
def live_server():
    proc = Process(target=run_server, daemon=True)
    proc.start()
    time.sleep(2)
    yield "http://localhost:8888"
    proc.kill()
```

Create `tests/e2e/test_web_ui.py`:

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.browser
def test_home_page_loads(page: Page, live_server):
    page.goto(live_server)
    expect(page).to_have_title("BCD - Bibliothèque Centre Documentaire")

@pytest.mark.browser
def test_language_switching(page: Page, live_server):
    page.goto(live_server)

    # Click English button
    page.click("button:text('EN')")

    # Wait for translation to load
    page.wait_for_timeout(500)

    # Check title updated
    expect(page.locator("h1")).to_contain_text("Library System")
```

Run tests:
```bash
pytest tests/e2e --browser chromium
```

---

## Step 9: Development Workflow

### Daily Development

1. **Start API server with auto-reload**:
```bash
python -m uvicorn src.bcd_api.main:app --reload
```

2. **Edit files in `src/bcd_web/`**:
   - HTML/CSS/JS changes reflect immediately (browser refresh)
   - No build step required

3. **View changes**:
   - Open `http://localhost:8000/`
   - Use browser DevTools (F12) for debugging

### Testing Workflow

```bash
# Run E2E tests
pytest tests/e2e --browser chromium

# Run with visible browser (headed mode)
pytest tests/e2e --headed --browser chromium

# Cross-browser testing
pytest tests/e2e --browser chromium --browser firefox --browser webkit
```

### Debugging

1. **API Logs**: Check uvicorn terminal for API requests
2. **Browser Console**: Check for JavaScript errors
3. **Network Tab**: Inspect htmx/fetch requests
4. **Playwright Trace**: `pytest tests/e2e --tracing on`

---

## Step 10: Next Steps

Now that basic setup is complete, proceed with:

1. **Implement Circulation Page**:
   - Create `src/bcd_web/js/pages/circulation.js`
   - Add checkout/return htmx forms
   - Test barcode scanning

2. **Implement Catalog Search**:
   - Create search interface with htmx
   - Add result filtering
   - Test pagination

3. **Add Navigation**:
   - Build full navigation menu
   - Implement client-side routing
   - Test page transitions

4. **Complete i18n**:
   - Add all translation strings
   - Test French/English switching
   - Verify date formatting

5. **Style with Bootstrap**:
   - Apply consistent component styling
   - Add status badges (available/on loan/overdue)
   - Create print CSS for reports

---

## Troubleshooting

### Issue: 404 on static files

**Symptoms**: CSS/JS files not loading, console shows 404

**Solution**:
```python
# Ensure mount order in main.py:
# 1. /static mount first
# 2. / mount last (catches all remaining routes)
```

### Issue: htmx not swapping content

**Symptoms**: htmx request succeeds but content doesn't update

**Solution**:
- Check `hx-target` selector is correct
- Verify template returns valid HTML
- Check for JavaScript errors in console

### Issue: Translations not updating

**Symptoms**: Language switching doesn't update text

**Solution**:
- Ensure elements have `data-i18n` attribute
- Call `i18n.updateDOM()` after language switch
- Check JSON file has the translation key

### Issue: Playwright tests timeout

**Symptoms**: Tests hang waiting for server

**Solution**:
- Increase `time.sleep(2)` in conftest.py
- Check uvicorn is not already running on port 8888
- Use different port for tests

---

## Resources

- **htmx Documentation**: https://htmx.org/docs/
- **Alpine.js Documentation**: https://alpinejs.dev/start-here
- **Bootstrap 5 Documentation**: https://getbootstrap.com/docs/5.3/
- **Playwright Python**: https://playwright.dev/python/
- **FastAPI Static Files**: https://fastapi.tiangolo.com/tutorial/static-files/

---

## Summary Checklist

Before proceeding to full implementation:

- [ ] API server running and accessible
- [ ] Static file serving configured in FastAPI
- [ ] HTML shell loads with Bootstrap styling
- [ ] i18n system working (FR/EN switching)
- [ ] htmx integration tested with sample endpoint
- [ ] Playwright E2E tests passing
- [ ] Development workflow established

**Next**: Implement full circulation page with checkout/return functionality
