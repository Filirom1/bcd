# BCD Developer Documentation

Technical documentation for developers working on BCD.

## Project Background

BCD was developed as a **research project to test AI-assisted software development** using Claude Code and the spec-kit methodology. This project demonstrates how AI can assist in creating production-ready software through structured specification and iterative development.

### Development Methodology

**Spec-Kit Approach**:
- Specification-driven development using markdown templates
- Task decomposition with dependency tracking
- Iterative implementation with checkpoint validation
- AI-assisted code generation following architectural patterns

**AI Partnership**:
- Requirements gathering and clarification
- Architecture design and technical decisions
- Code implementation following best practices
- Test generation and validation
- Documentation creation

**Key Learnings**:
This project validates that AI-assisted development with proper specifications can produce:
- Production-ready code with 90%+ test coverage
- Consistent architectural patterns
- Comprehensive documentation
- Maintainable codebase structure

---

## Architecture Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────┐
│         Web UI (Vue 3)                  │
│  - Single-Page Application              │
│  - Vendored deps, no build tools        │
│  - Component-based architecture         │
└─────────────────────────────────────────┘
                  ↓ HTTP/JSON
┌─────────────────────────────────────────┐
│         REST API (FastAPI)              │
│  - Business logic layer                 │
│  - Service pattern                      │
│  - Pydantic validation                  │
└─────────────────────────────────────────┘
                  ↓ SQLAlchemy
┌─────────────────────────────────────────┐
│      Database (SQLite/PostgreSQL)       │
│  - ORM models                           │
│  - Alembic migrations                   │
│  - Referential integrity                │
└─────────────────────────────────────────┘
```

### Technology Stack

**Backend**:
- FastAPI 0.100+ (async API framework)
- SQLAlchemy 2.0 (ORM with async support)
- Alembic (database migrations)
- Pydantic (data validation)
- Python 3.11+ (required for modern type hints)

**Frontend**:
- Vue 3.4.21 (reactive framework, vendored locally)
- Vue Router 4.2.5 (client-side routing)
- Vue I18n 9.9.1 (internationalization)
- Bootstrap 5.3.3 + Bootstrap Icons 1.11.3 (UI framework)
- JsBarcode 3.11.6 (client-side barcode rendering)
- No build tools (ES6 modules, direct browser support)
- All dependencies vendored in `src/bcd_web_vue/vendor/` — works fully offline

**Database**:
- SQLite (development and small deployments)
- PostgreSQL (production, optional)

**External Services**:
- BNF SRU API (French National Library catalog lookup)

### Project Structure

```
bcd/
├── src/
│   ├── bcd_api/              # REST API server
│   │   ├── api/v1/           # API endpoints (routes)
│   │   ├── core/             # Config, database, dependencies
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # Business logic layer
│   │   └── utils/            # Utilities (BNF API, barcodes)
│   │
│   ├── bcd_cli/              # CLI client
│   │   └── commands/         # CLI command implementations
│   │
│   ├── bcd_web_vue/          # Vue 3 web UI
│   │   ├── js/
│   │   │   ├── api/          # API client
│   │   │   ├── components/   # Vue components
│   │   │   ├── composables/  # Vue composables (hooks)
│   │   │   ├── models/       # TypeScript-style models
│   │   │   └── pages/        # Page components
│   │   ├── locales/          # i18n translations
│   │   ├── css/              # Styles
│   │   └── vendor/           # Vendored JS/CSS deps (offline, see vendor.json)
│   │
│   └── shared/               # Shared constants/validators
│
├── migrations/               # Alembic database migrations
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── cli/                  # CLI tests
│   └── e2e/                  # End-to-end tests (Playwright)
│
├── data/                     # Sample and fixture data
├── docs/                     # Documentation
├── vendor.json               # Frontend dependency manifest (versions + download URLs)
├── specs/                    # Spec-kit specifications
│   ├── 001-school-library-system/
│   ├── 002-tauri-desktop-app/
│   └── 003-web-ui/           # Vue 3 migration spec
└── .specify/                 # Spec-kit configuration
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- A code editor (VS Code recommended)

### First-Time Setup

```bash
# Clone repository
git clone <repository-url>
cd bcd

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install all dependencies (including dev, CLI, converters)
pip install -e ".[dev]"

# Initialize database
alembic upgrade head

# Run tests to verify setup
pytest

# Start development server
uvicorn src.bcd_api.main:app --reload
```

### Development Tools

**Recommended VS Code Extensions**:
- Python (Microsoft)
- Pylance (Microsoft)
- SQLite Viewer
- Vue Language Features (Volar)
- ESLint

**Code Quality Tools**:
```bash
# Format code (Black)
black src/ tests/

# Lint code (Ruff)
ruff check src/ tests/

# Type checking (Pyright)
pyright src/ tests/

# Run all checks
black src/ tests/ && ruff check src/ tests/ && pytest
```

---

## Testing

### Test Organization

```
tests/
├── unit/                     # Fast, isolated unit tests
│   ├── services/             # Service layer tests
│   ├── models/               # ORM model tests
│   └── schemas/              # Pydantic schema tests
│
├── integration/              # Database integration tests
│   ├── services/             # Service tests with real DB
│   └── api/                  # API endpoint tests
│
├── cli/                      # CLI command tests
│   └── test_e2e_real_data.py # End-to-end CLI workflow
│
└── e2e/                      # Browser-based E2E tests
    ├── test_vue_web_ui.py    # Vue UI tests
    ├── test_borrowers_vue.py # Borrower page tests
    └── test_cataloging_vue.py # Cataloging tests
```

### Running Tests

```bash
# All tests
pytest

# Specific test suite
pytest tests/unit -v
pytest tests/integration -v
pytest tests/cli -v
pytest tests/e2e -v

# With coverage
pytest --cov=src --cov-report=html
# View coverage: open htmlcov/index.html

# Specific test file
pytest tests/unit/services/test_catalog_service_unit.py -v

# Specific test function
pytest tests/unit/services/test_catalog_service_unit.py::test_create_bibliographic_record -v

# Fast tests only (skip slow markers)
pytest -m "not slow"

# Run in parallel (faster)
pytest -n auto
```

### Test Coverage Goals

- Service layer: 90%+ coverage
- Models: 95%+ coverage
- Schemas: 100% coverage (Pydantic validates everything)
- API endpoints: 80%+ coverage

**Current Status**:
- Unit tests: 199 passing
- Integration tests: 110 passing
- CLI tests: 10 passing
- E2E tests: 11/12 passing

### Writing Tests

**Follow AAA Pattern** (Arrange-Act-Assert):

```python
def test_checkout_book():
    # Arrange: Set up test data
    borrower = create_test_borrower()
    item = create_test_item()

    # Act: Perform the action
    result = circulation_service.checkout_item(
        db_session, borrower.id, item.id
    )

    # Assert: Verify the outcome
    assert result.item_id == item.id
    assert result.borrower_id == borrower.id
    assert result.status == "on_loan"
```

**Use Fixtures** (defined in `conftest.py`):

```python
def test_search_catalog(db_session, sample_catalog):
    # db_session: Clean database session
    # sample_catalog: Pre-populated catalog data
    results = catalog_service.search(db_session, query="Stuart")
    assert len(results) > 0
```

---

## Database

### Schema Management

**Migrations** (Alembic):

```bash
# Create new migration
alembic revision --autogenerate -m "Add overdue_fine_amount to borrowers"

# Review generated migration in migrations/versions/

# Apply migration
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

**Important**: Always review auto-generated migrations before applying.

### Models

Located in `src/bcd_api/models/`, using SQLAlchemy 2.0 declarative mapping.

**Example**:

```python
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Borrower(Base):
    __tablename__ = "borrowers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    borrower_id: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    class_: Mapped["Class"] = relationship(back_populates="borrowers")
    loans: Mapped[list["Loan"]] = relationship(back_populates="borrower")
```

### Database Pattern

**StaticPool for SQLite**:

```python
# In src/bcd_api/core/database.py
engine = create_engine(
    "sqlite:///bcd.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Single connection for SQLite
)
```

This ensures transaction isolation in tests while maintaining performance.

---

## API Development

### Service Layer Pattern

**Business logic belongs in services**, not in API routes.

**Bad** (logic in route):
```python
@router.post("/checkout")
def checkout(item_id: str, borrower_id: str):
    item = db.query(Item).filter_by(id=item_id).first()
    if item.status != "available":
        raise HTTPException(400, "Item not available")
    item.status = "on_loan"
    db.commit()
    return item
```

**Good** (logic in service):
```python
# In api/v1/circulation.py
@router.post("/checkout")
def checkout(
    checkout_data: CheckoutSchema,
    db: Session = Depends(get_db)
):
    return circulation_service.checkout_item(
        db, checkout_data.borrower_id, checkout_data.item_id
    )

# In services/circulation_service.py
def checkout_item(db: Session, borrower_id: str, item_id: str):
    # Validation, business rules, database operations
    item = get_item_or_404(db, item_id)
    borrower = get_borrower_or_404(db, borrower_id)

    if item.status != "available":
        raise ItemNotAvailableError(item_id)

    if borrower.current_loans_count >= borrower.loan_limit:
        raise LoanLimitExceededError(borrower_id)

    # ... create loan, update item status, etc.
    return loan
```

### Adding New API Endpoints

1. **Define schema** in `src/bcd_api/schemas/`:
   ```python
   class CheckoutSchema(BaseModel):
       borrower_id: str
       item_id: str
       due_date: Optional[date] = None
   ```

2. **Implement service** in `src/bcd_api/services/`:
   ```python
   def checkout_item(db: Session, borrower_id: str, item_id: str):
       # Business logic here
       pass
   ```

3. **Write tests** in `tests/integration/services/`:
   ```python
   def test_checkout_item(db_session):
       # Test the service
       pass
   ```

4. **Add route** in `src/bcd_api/api/v1/`:
   ```python
   @router.post("/checkout", response_model=LoanSchema)
   def checkout(
       data: CheckoutSchema,
       db: Session = Depends(get_db)
   ):
       return circulation_service.checkout_item(db, data.borrower_id, data.item_id)
   ```

5. **Test API** using Swagger UI at http://127.0.0.1:8000/api/v1/docs

---

## Frontend Development

### Vue 3 Architecture

**Component-Based**: Each feature is a self-contained Vue component.

**No Build Tools**: Components use ES6 modules loaded directly by the browser.

**Vendor Dependencies** (locally hosted in `src/bcd_web_vue/vendor/`, works offline):
- Vue 3.4.21
- Vue Router 4.2.5
- Vue I18n 9.9.1
- Bootstrap 5.3.3 + Bootstrap Icons 1.11.3
- JsBarcode 3.11.6

To update a dependency, edit `vendor.json` and re-run:
```bash
python scripts/download-vendor.py
```

### Component Structure

```javascript
// src/bcd_web_vue/js/components/Example.js
const { defineComponent, ref, computed } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'ExampleComponent',

    props: {
        itemId: {
            type: String,
            required: true
        }
    },

    emits: ['item-selected'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Reactive state
        const loading = ref(false);
        const item = ref(null);

        // Computed properties
        const isAvailable = computed(() =>
            item.value?.status === 'available'
        );

        // Methods
        async function loadItem() {
            loading.value = true;
            item.value = await apiClient.get(`/items/${props.itemId}`);
            loading.value = false;
        }

        function selectItem() {
            emit('item-selected', item.value);
        }

        // Lifecycle
        onMounted(() => {
            loadItem();
        });

        return {
            loading,
            item,
            isAvailable,
            loadItem,
            selectItem,
            t
        };
    },

    template: `
        <div class="example-component">
            <div v-if="loading">{{ t('common.loading') }}</div>
            <div v-else-if="item">
                <h3>{{ item.title }}</h3>
                <span :class="{'badge': true, 'bg-success': isAvailable}">
                    {{ t('catalog.status.' + item.status) }}
                </span>
                <button @click="selectItem">
                    {{ t('common.select') }}
                </button>
            </div>
        </div>
    `
});
```

### Composables (Reusable Logic)

Located in `src/bcd_web_vue/js/composables/`:

```javascript
// useNotification.js
export function useNotification() {
    const notifications = ref([]);

    function success(message) {
        notifications.value.push({ type: 'success', message });
    }

    function error(message) {
        notifications.value.push({ type: 'error', message });
    }

    return { notifications, success, error };
}

// Usage in component:
const { success, error } = useNotification();
success('Book checked out successfully');
```

### Internationalization

**Translation Files**: `src/bcd_web_vue/locales/en.json`, `fr.json`

```json
{
    "common": {
        "loading": "Loading...",
        "save": "Save"
    },
    "circulation": {
        "checkout": "Checkout",
        "return": "Return"
    }
}
```

**Usage in Components**:
```javascript
const { t } = useI18n();
console.log(t('common.loading')); // "Loading..." or "Chargement..."
```

**Adding New Translations**:
1. Add key to both `en.json` and `fr.json`
2. Use in template: `{{ t('your.new.key') }}`
3. Test in both languages

---

## Spec-Kit Methodology

### What is Spec-Kit?

Spec-kit is a specification-driven development methodology that uses structured markdown templates for:
- Feature specifications
- Implementation planning
- Task decomposition
- Progress tracking

### Directory Structure

```
specs/
└── 003-web-ui/                 # Feature ID
    ├── spec.md                 # User stories & acceptance criteria
    ├── plan.md                 # Technical implementation plan
    ├── tasks.md                # Decomposed task list
    ├── research.md             # Research findings
    ├── checklists/             # Quality checklists
    │   └── requirements.md
    └── contracts/              # API contracts
```

### Spec-Kit Commands

These commands were used during development:

```bash
# Generate specification from description
/speckit.specify "Add Vue 3 web UI with barcode scanner support"

# Create implementation plan
/speckit.plan

# Ask clarifying questions
/speckit.clarify

# Generate task breakdown
/speckit.tasks

# Execute implementation
/speckit.implement

# Analyze consistency
/speckit.analyze
```

### Development Workflow

1. **Specification** (`spec.md`)
   - Define user stories
   - List acceptance criteria
   - Specify functional requirements

2. **Planning** (`plan.md`)
   - Choose technology stack
   - Design architecture
   - Identify dependencies
   - Create mockups

3. **Task Decomposition** (`tasks.md`)
   - Break into implementable tasks
   - Define dependencies
   - Estimate effort

4. **Implementation**
   - Execute tasks in order
   - Validate checkpoints
   - Write tests
   - Update documentation

5. **Validation**
   - Run test suite
   - Check against spec
   - Cross-artifact analysis

### Constitution-Driven Development

Located at `.specify/memory/constitution.md`, defines project principles:

1. Code Quality & DRY
2. Library-First Approach
3. Comprehensive Testing (80%+ coverage)
4. User Experience Consistency
5. Click Minimization (≤2 steps for primary actions)
6. Performance for Legacy Hardware
7. Database Schema Versioning (Alembic only)
8. Research-First Feature Design
9. Design-First Implementation (mockups before code)
10. Internationalization (EN+FR required)

All features must comply with these principles.

---

## Code Style Guidelines

### Python (Backend)

Follow PEP 8 with these additions:

```python
# Type hints required
def create_loan(db: Session, borrower_id: str, item_id: str) -> Loan:
    pass

# Docstrings for public functions
def calculate_due_date(loan_date: date, duration: int) -> date:
    """Calculate due date for a loan.

    Args:
        loan_date: Date the item was loaned
        duration: Loan duration in days

    Returns:
        Due date for the loan
    """
    return loan_date + timedelta(days=duration)

# Use Pydantic for validation
class CheckoutSchema(BaseModel):
    borrower_id: str = Field(..., min_length=1, max_length=50)
    item_id: str = Field(..., min_length=1, max_length=50)

    @validator('borrower_id')
    def validate_borrower_id(cls, v):
        if not v.startswith('BOR'):
            raise ValueError('Borrower ID must start with BOR')
        return v
```

### JavaScript (Frontend)

Follow ES6+ conventions:

```javascript
// Named exports preferred
export function formatDate(date) {
    return date.toLocaleDateString('fr-FR');
}

// Destructuring
const { ref, computed, onMounted } = Vue;

// Arrow functions for callbacks
items.filter(item => item.status === 'available')

// Template literals
const message = `Book ${title} is ${status}`;

// Async/await for promises
async function loadData() {
    const data = await apiClient.get('/items');
    return data;
}
```

### Git Commit Messages

Follow Conventional Commits:

```bash
feat: add overdue report with class grouping
fix: correct ISBN normalization for 10-digit ISBNs
docs: update README with barcode scanner setup
test: add integration tests for circulation service
refactor: extract date formatting to utility function
perf: optimize catalog search query with indexes
```

---

## Performance Considerations

### Backend

- Use database indexes (defined in models)
- Paginate large result sets
- Cache expensive operations
- Use async where appropriate (FastAPI native)

### Frontend

- Lazy load components
- Debounce search inputs
- Pagination for large lists
- Virtual scrolling for very long lists

### Database

**SQLite Limitations**:
- Max ~50 concurrent writes
- Recommend PostgreSQL for >10 concurrent users

**Query Optimization**:
- Use EXPLAIN to analyze queries
- Add indexes for frequently queried columns
- Avoid N+1 queries (use eager loading)

---

## Auto-Update (Portable Builds)

### Overview

`src/bcd_api/core/updater.py` implements GitHub-based self-update for the portable (PyInstaller) build. It runs synchronously in `main()` after `initialize_portable_environment()`, before the UI starts. It is a no-op in dev mode (`is_portable()` returns `False`).

### Flow

```
main() [portable only]
  └─ check_and_apply_update(current_version, app_dir)
       ├─ _cleanup_stale_update()          remove bcd.exe.old + update/
       ├─ _is_online()                     socket check to api.github.com:443 (3 s timeout)
       │    └─ False → return (no dialog)
       ├─ check_for_update()               GET /repos/Filirom1/bcd/releases/latest
       │    └─ None → return (up to date)
       ├─ _show_yes_no()                   tkinter dialog: "BCD vX.Y.Z available?"
       │    └─ No  → return
       ├─ _download_with_progress()        urllib.request + tkinter progress window
       └─ _apply_update_{windows,linux}()
            ├─ extract ZIP / tar.gz to update/extracted/
            ├─ write update.bat / update.sh
            ├─ launch script (detached / new session)
            └─ sys.exit(0)
```

### Windows file-locking strategy

Windows locks the running executable and every DLL loaded from `_internal/`. The update script runs *after* `sys.exit(0)` closes all handles:

| File | Technique |
|------|-----------|
| `bcd.exe` | `move bcd.exe bcd.exe.old` (rename works on open handles), then `copy` new exe |
| `_internal/*.dll` | `robocopy /R:5 /W:2` — 5 retries × 2 s for any briefly-locked DLL |
| `BCD-Kids.exe` + `.pck` | Plain `copy` (never locked by `bcd.exe`) |

The batch script uses `ping -n 5 127.0.0.1` (~4 s wait) before touching files, giving the Python runtime time to fully exit. `bcd.exe.old` and `update/` are cleaned up on the *next* startup via `_cleanup_stale_update()`.

### Linux

Linux allows overwriting a running binary (the kernel keeps the old inode open until the last reference drops). A plain `cp` after `sleep 2` is sufficient. The script runs in a new session (`start_new_session=True`).

### GitHub release assets

The updater matches assets by suffix:

| Platform | Asset |
|----------|-------|
| `win32` | `BCD-v{VERSION}-Windows.zip` |
| Linux | `BCD-v{VERSION}-Linux.tar.gz` |

These are produced by `.github/workflows/release.yml` on every `v*.*.*` tag.

### Adding the updater to a new platform

1. Add a new `_apply_update_{platform}()` function in `updater.py`
2. Extend the `sys.platform` branch in `check_and_apply_update()`
3. Match the correct asset suffix in `check_for_update()`

### Language detection

All dialog strings are localised. `_detect_lang()` calls `locale.getdefaultlocale()` which reads the OS UI language (Windows locale settings on Windows, `LANG`/`LC_ALL` on Linux). Returns `'fr'` when the locale starts with `fr`, `'en'` otherwise. Strings are defined in the `_STRINGS` dict at the top of `updater.py`; `_t(key, **kwargs)` retrieves the right one.

To add a language, add a new entry to `_STRINGS` and extend `_detect_lang()`.

### tkinter in the PyInstaller bundle

`tkinter` and `tkinter.messagebox` are listed in `hiddenimports` in `bcd.spec` so PyInstaller includes them. No extra runtime dependency is needed — tkinter ships with every CPython 3.x distribution.

---

## Deployment

See [INSTALL.md](INSTALL.md) for detailed deployment instructions.

**Production Checklist**:
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up reverse proxy (nginx/Apache)
- [ ] Enable HTTPS
- [ ] Configure firewall
- [ ] Set up automated backups
- [ ] Monitor error logs
- [ ] Set up systemd service
- [ ] Test disaster recovery

---

## Contributing

### Branch Strategy

- `main`: Stable releases
- `003-web-ui`: Web UI development (default for PRs)
- `feature/*`: Feature branches

### Pull Request Process

1. Create feature branch from `003-web-ui`
2. Write tests first (TDD)
3. Implement feature
4. Ensure all tests pass: `pytest`
5. Run code quality checks: `black src/ tests/ && ruff check src/ tests/`
6. Update documentation if needed
7. Submit PR with clear description

### Code Review Checklist

- [ ] Tests included and passing
- [ ] Code follows style guidelines
- [ ] No hard-coded strings (use i18n)
- [ ] Documentation updated
- [ ] Database migration if schema changed
- [ ] Backward compatible or noted in CHANGELOG

---

## Resources

**Internal Documentation**:
- [User Guide](README.md)
- [Installation Guide](INSTALL.md)
- [Vue Migration Guide](docs/vue-migration.md)
- [Component Guide](docs/component-guide.md)

**External References**:
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/
- Vue 3: https://vuejs.org/guide/
- Alembic: https://alembic.sqlalchemy.org/

**API Documentation**:
- Swagger UI: http://127.0.0.1:8000/api/v1/docs
- ReDoc: http://127.0.0.1:8000/api/v1/redoc

---

## License

MIT License - See LICENSE file for details

---

## Development Team

This project was developed using AI-assisted development with Claude Code (Anthropic) and the spec-kit methodology. It serves as a demonstration of how AI can partner with developers to create production-quality software through structured specification and iterative implementation.

**Research Questions Explored**:
- Can AI follow architectural patterns consistently?
- How effective is specification-driven development with AI?
- Can AI generate production-ready code with proper testing?
- What are the limits of AI-assisted refactoring?

**Findings**:
- AI excels at implementing well-specified features
- Test-first development works well with AI assistance
- Architecture decisions benefit from human oversight
- AI can maintain code quality across large refactorings (HTMX → Vue 3)

This project demonstrates that with proper specification and methodology, AI-assisted development can produce maintainable, well-tested, production-ready software.
