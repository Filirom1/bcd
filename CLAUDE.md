# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BCD is a school library management system for French elementary schools:
- **REST API** (FastAPI) — business logic layer
- **CLI Client** (Click) — thin client over the API
- **Web UI** (Vue 3) — SPA served as native ESM by FastAPI in dev; Vite builds offline production assets
- **Godot Client** (Godot 4.6) — kid-friendly client for students (ages 6-11)
- SQLite for development, PostgreSQL-ready for production
- Bilingual (English/French), single-server (API + Web UI on same origin)

## Commands

### Development Setup

```bash
# NixOS (recommended): auto-creates venv, sets PYTHONPATH, configures Playwright
nix-shell
npm ci

# Manual:
python3.11 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
npm ci
alembic upgrade head
```

### Running

```bash
# Start server (API + Web UI)
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
# Web UI: http://127.0.0.1:8888
# API docs: http://127.0.0.1:8888/api/v1/docs

# Build/test Web UI production (no Vite dev server or proxy)
npm run web -- --manual             # serve build/web/ manually via FastAPI
npm run web -- --e2e                # production Playwright smoke test
npm run web -- --portable --manual  # package and launch the portable executable

# CLI
python -m src.bcd_cli.main checkout
python -m src.bcd_cli.main catalog import data/sample_bibliographic.csv

# Godot Client (kids interface)
# 1. Open bcd_kids/project.godot in Godot 4.6
# 2. Press F5 to run
# Auto-discovers the server via mDNS on localhost:8888
```

### Testing

The recommended way to run tests is using the unified central test runner:

```bash
python run_tests.py             # Run all active Python + JS tests (complete suite)
python run_tests.py --fast      # Run fast Python + JS tests (ideal before commit)
python run_tests.py --js        # Run JavaScript Vitest tests only
python run_tests.py --python    # Run Python Pytest tests only
python run_tests.py --cov       # Run selected suites with coverage enabled
```

Alternatively, you can run individual suites directly:

```bash
# Pure JavaScript (Vitest)
npm run test:js                                                # Run JS tests
npm run test:js:coverage                                       # Run JS tests with coverage

# Pure Python (Pytest)
pytest tests -m "not e2e and not slow"                         # Fast Python suite
pytest tests                                                   # Complete Python suite (excluding deactivated E2E)
pytest tests/integration/services/ -v                           # Service-layer integration tests
pytest tests/integration/test_catalog_service.py -v            # Run a single file
```

Pre-commit hook: `./scripts/install-hooks.sh` (runs `pytest tests/integration tests/unit` before each commit; skips CLI tests due to known setup issues).

### Database Migrations

```bash
alembic revision --autogenerate -m "description"    # create
alembic upgrade head                                # apply
alembic downgrade -1                                # rollback
```

### Simulate Realistic Data

```bash
python reset_and_simulate.py   # drops DB, re-migrates, imports catalog/students,
                                # simulates 9 months of circulation activity (~500+ transactions)
```

### Code Quality

```bash
black src/ tests/
ruff src/ tests/
```

### Version Management

**Unified versioning** for entire project (API + CLI + Kids client):
```bash
# Show current version
python scripts/bump_version.py --current

# Bump version (updates API AND Kids client)
python scripts/bump_version.py patch   # 1.0.0 -> 1.0.1
python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0
python scripts/bump_version.py major   # 1.0.0 -> 2.0.0

# Bump and push (triggers ALL releases)
python scripts/bump_version.py patch --push
```

The script:
- Updates `pyproject.toml` (single source of truth)
- Synchronizes `bcd_kids/export_presets.cfg` with the same version
- Creates a git commit
- Creates ONE annotated git tag:
  - `v*.*.*` → triggers `.github/workflows/release.yml` (unified: tests + Windows + Linux + Godot builds)
- Optionally pushes to trigger GitHub Actions releases

**Important**: The project uses a single version number for all components. API and Kids client versions are always synchronized.

## Architecture

### Source Layout

```
src/
├── bcd_api/          # FastAPI REST API
│   ├── api/v1/       # Thin route handlers (call services, no business logic)
│   ├── services/     # All business logic (one file per domain)
│   ├── models/       # SQLAlchemy ORM models
│   ├── schemas/      # Pydantic request/response schemas
│   └── core/         # database.py, config.py, deps.py, portable.py, mdns.py
├── bcd_cli/          # Click CLI (thin HTTP client over API)
│   └── commands/     # One module per command group
├── bcd_web_vue/      # Vue 3 SPA source (native ESM in development)
│   ├── js/           # ~80 Vue 3 components organized by feature
│   ├── locales/      # i18n: en.json, fr.json
│   └── templates/    # shared SPA shell for source and Vite builds
├── bcd_converters/   # One-off data migration scripts (Bibliopuce, ONDE, XLS)
└── shared/           # constants.py, validators.py, version.py

bcd_kids/             # Godot 4.6 client (kid-friendly, ages 6-11) — at repo root
├── autoload/         # Singletons: GS (state), API (HTTP), I18n (i18n), Mgr (navigation)
├── src/
│   ├── BCDTheme.gd       # Color palette + UI helpers
│   ├── components/       # Reusable components (each has .tscn + .gd)
│   └── screens/          # Screens (each has SNomEcran.tscn + SNomEcran.gd)
├── locales/          # i18n: fr.json, en.json
├── project.godot
└── export_presets.cfg    # Windows/Linux export configs

bcd_kids_rs/          # Legacy Rust/egui kids client (superseded by Godot client)
```

### Key Architectural Rules

- **Service layer**: ALL business logic lives in `src/bcd_api/services/`. Routes are thin — they validate input, call a service, return the response.
- **Dependency injection**: `db: Session = Depends(get_db)` everywhere. Never create sessions manually.
- **Exception flow**: Services raise `BCDException` subclasses. The API layer in `main.py` converts them to HTTP responses (400/409/422).
- **API-first**: CLI and Web UI are pure clients. They contain no business logic.
- **SQLite StaticPool**: `core/database.py` uses `StaticPool` to maintain a single SQLite connection across threads — do not change this without understanding the implications.

### Database

7 tables: `bibliographic_record`, `item`, `borrower`, `class`, `circulation`, `hold`, `system_settings`. All schema changes via Alembic migrations. Foreign keys enforced via SQLite PRAGMA. Comprehensive indexing on all WHERE/JOIN/ORDER BY fields.

### Configuration (`src/bcd_api/core/config.py`)

Key settings (via `.env`):
- `DATABASE_URL` — defaults to `sqlite:///./data/bcd.db`
- `API_HOST`, `API_PORT` — server bind address
- `BNF_API_URL`, `BNF_RATE_LIMIT` — French National Library (1 req/s)
- `UI_MODE` — `webview`/`browser`/`godot`: choose which interface to launch on startup; used for portable builds
- `KIDS_CLIENT_PATH` — path to Kids client executable (required when `UI_MODE=godot`)
- `WEB_ASSETS_MODE` — `source` (default native ESM development) or `build` (local production-build test)

### Portable Builds

PyInstaller spec at `bcd.spec`. Run `npm run verify:web-build` before PyInstaller; it packages `build/web/`, not the web sources or `node_modules`. `src/bcd_api/core/portable.py` handles bundled resource detection. The `--ui-mode` flag (or `UI_MODE` in .env) chooses which interface to launch: `webview` (native window), `browser` (system browser), or `godot` (Kids client).

### mDNS Discovery

`src/bcd_api/core/mdns.py` — announces the server on the local network via Zeroconf at startup.

## Testing Philosophy

Prefer **service-layer integration tests** in `tests/integration/services/`. Each test uses the `db_session` fixture (transaction rollback isolation — no cleanup needed). Follow AAA pattern with descriptive names: `test_<action>_<condition>_<expected_result>`. Mock BNF API calls (`src/bcd_api/services/bnf_service.py`) to avoid network dependencies.

E2E tests use Playwright with page objects in `tests/e2e/page_objects/`. API-layer tests (`tests/api/`) may be skipped due to TestClient/database isolation conflicts.

Coverage goals: 80%+ minimum, 90%+ for services.

## Project Constitution & Spec-Kit

Full constitution at `.specify/memory/constitution.md` (v1.2.0), architecture patterns at `.specify/architecture-patterns.md` (v1.0.0). These are the authoritative references — read them before implementing new features.

Feature workflow: `/speckit.specify` → `/speckit.plan` → `/speckit.clarify` → `/speckit.tasks` → `/speckit.analyze` (pre-implementation gate) → `/speckit.implement` → `/speckit.review` (post-implementation gate, required before merge).

Feature specs live in `specs/<feature-id>/` (spec.md, plan.md, tasks.md, research.md, contracts/).

Key constitution rules to internalize:
- ≤2 clicks for primary actions; smart defaults
- All user-facing text externalized (no hard-coded en/fr strings)
- All DB changes via Alembic with up/down scripts
- Performance target: 5+ year old hardware (2 GHz CPU, 4 GB RAM), response ≤500 ms
- Cross-platform: Linux & Windows, use `pathlib` for all file operations

## Internationalization

Web UI translations: `src/bcd_web_vue/locales/en.json` and `fr.json`. Both files must be updated together. Missing keys fall back to English.

## Auto-Update (Portable Builds)

`src/bcd_api/core/updater.py` — runs at startup in portable mode only.

- Checks `https://api.github.com/repos/Filirom1/bcd/releases/latest` (skipped silently if offline)
- Compares tag version with `settings.app_version`; detects OS language via `locale.getdefaultlocale()` and shows a tkinter yes/no dialog in French or English if a newer release exists
- Downloads the platform archive (`BCD-v{VERSION}-Windows.zip` or `BCD-v{VERSION}-Linux.tar.gz`) with a progress window
- **Windows**: writes `update.bat`, launches it fully detached (`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`), then calls `sys.exit(0)` — the batch waits ~4 s (ping trick), renames `bcd.exe` → `bcd.exe.old`, copies new exe + uses `robocopy /R:5 /W:2` for `_internal/` (handles briefly-locked DLLs), replaces Kids client, then relaunches
- **Linux**: writes `update.sh`, launches it in a new session, then exits — plain `cp` after `sleep 2` is safe (kernel keeps old inode open)
- Cleans up `bcd.exe.old` and `update/` on every startup (handles interrupted updates)
- All errors are non-fatal; startup continues normally on any failure

## External Integrations

**BNF API** (French National Library): `src/bcd_api/services/bnf_service.py`. SRU protocol, XML responses, rate-limited to 1 req/s. Always mock in tests.

## Branch & Commit Conventions

- Main branch: `main`
- Feature branches: `<feature-id>-<brief-description>`
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)

## Godot Client

See [`bcd_kids/README.md`](bcd_kids/README.md) for complete documentation.

**Key points**:
- Godot 4.6 project (each screen and component has paired `.tscn` + `.gd` files)
- Kid-friendly interface for ages 6-11 (CP-CM2)
- Autoload singletons: GS (state), API (HTTP client), I18n (translations), Mgr (navigation)
- 9 screens: ServerDiscovery → ClassSelect → NameInput → MainMenu → Checkout/Return/Search/Holds
- Export presets: Windows Desktop, Linux/X11
- GitHub Actions: Continuous builds on push to main/develop; releases triggered by `v*.*.*` tags (via unified `release.yml`)
- CI/CD workflows:
  - `.github/workflows/build-godot.yml` — continuous builds (artifacts 14 days)
  - `.github/workflows/release.yml` — unified release (tag `v*.*.*`): runs tests, builds Windows + Linux + Godot
  - `.github/workflows/release-godot.yml` — manual Godot-only release (`workflow_dispatch`)

**Architecture**:
- All screens use `class_name S*` (e.g., `SMainMenu`, `SSearch`)
- Components use `class_name ComponentName` (e.g., `Breadcrumb`, `BookCard`)
- BCDTheme provides color palette and UI helpers (buttons, labels, panels, etc.)
- Navigation: `Mgr.push(screen)`, `Mgr.pop()`, `Mgr.replace(screen)`
- API calls return untyped (can be Dictionary or Array) — handle both
- Translations: `I18n.t(key)` or `I18n.t(key, params)`

**UI rules (critical)**:
- Every screen → `SNomEcran.tscn` + `SNomEcran.gd`; every component → `NomDuComposant.tscn` + `NomDuComposant.gd`
- `.gd` contains only logic (signals, data, API calls); `.tscn` contains all visual structure (layout, sizes, colors)
- **Zero procedural UI** in `.gd` files — no `Node.new()` or `add_child()` for layout construction
- Shared font/theme: defined once in `theme.tres`, applied via `theme = ExtResource("theme.tres")` on root node; Labels inherit automatically — no per-Label font overrides
- Only allowed per-Label overrides: `theme_override_font_sizes/font_size` and `theme_override_colors/font_color` when they differ from the default

**Colors** (BCDTheme):
- BG: `#F2F8FF` (light blue sky)
- PRIMARY: `#4D99F2` (bright blue)
- SUCCESS: `#33CC66` (green)
- ERROR: `#F24D66` (soft red)
- WARNING: `#F2BF33` (yellow)
- AVAILABLE: green, RESERVED: yellow, ON_LOAN: red

**Build/Export**:
- Local: Open project in Godot 4.6 → Project → Export
- Release: Use `python scripts/bump_version.py patch --push` (creates `v*.*.*` tag → triggers unified `release.yml`)
- Platforms: Windows (`.exe`), Linux (`.x86_64`)

**Optimisations pour vieux PC**:
- OpenGL Compatibility renderer (pas Vulkan)
- VSync activé (limite 60 FPS)
- Anti-aliasing désactivé (MSAA=0)
- Textures S3TC compressées (BPTC désactivé)
- Console wrapper désactivé (évite faux positifs antivirus)
- Binaire unique embed_pck (pas de .pck séparé)
- Métadonnées Windows complètes (file_version, product_name, etc.)
- Limite mémoire messages queue: 4MB
- Target: 4GB RAM, HDD, Windows 10, GPU Intel HD Graphics 2000+

Voir `bcd_kids/DEPLOYMENT.md` pour guide complet déploiement PC scolaires.
