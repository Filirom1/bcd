# Implementation Plan: Windows Portable Distribution

**Branch**: `002-windows-portable` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Status**: Implemented (retroactive documentation)

## Summary

Create a zero-installation Windows portable distribution of BCD by bundling the Python runtime, all dependencies, web UI, and database migrations into a standalone executable using PyInstaller. Users extract a ZIP file and double-click `START.bat` to launch the application without requiring Python, Node.js, or any other installations. The system automatically initializes the database on first run, preserves user data across updates, and supports both local and network deployment.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PyInstaller 6.x, FastAPI, Uvicorn, SQLAlchemy, Alembic, Vue 3 (CDN)
**Storage**: SQLite database in `data/bcd.db` (portable location)
**Testing**: Integration tests for portable mode detection, manual testing on clean Windows machines
**Target Platform**: Windows 10/11 (64-bit), GitHub Actions Windows runner for builds
**Project Type**: Single-server application (API + Web UI)
**Performance Goals**: <3s startup (warm), <10s first run with DB init, <50MB exe compressed
**Constraints**: No Python required on target machine, <200MB total distribution size, works offline
**Scale/Scope**: Single-school deployment (10-500 users), file-based distribution via ZIP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **#2 (Library-First Approach)**: Uses PyInstaller (established bundler) vs. custom solution
✅ **#6 (Performance for Legacy Hardware)**: Tested on 5+ year old Windows hardware baseline
✅ **#7 (Database Schema Versioning)**: Alembic migrations bundled and run programmatically
✅ **#10 (Internationalization)**: All i18n files bundled in distribution
⚠️ **#3 (Comprehensive Testing)**: Limited automated testing (manual testing on Windows required)

## Project Structure

### Documentation (this feature)

```text
specs/002-windows-portable/
├── spec.md              # Feature specification (user scenarios)
├── plan.md              # This file (implementation strategy)
├── tasks.md             # Task breakdown (retroactive)
├── research.md          # PyInstaller alternatives analysis
└── contracts/
    └── portable-api.md  # Portable mode API contract
```

### Source Code (repository root)

```text
# PyInstaller Configuration
bcd-api.spec                    # PyInstaller spec file (main build config)

# Portable Mode Support
src/bcd_api/core/portable.py    # Portable detection and path helpers

# Core Application (modified for portable support)
src/bcd_api/
├── core/
│   ├── config.py               # Modified: dynamic .env path
│   ├── database.py             # Modified: dynamic DB path
│   └── portable.py             # NEW: Portable mode helpers
├── main.py                     # Modified: startup event for init
└── ...

# Database Migrations (modified for portable support)
migrations/
├── env.py                      # Modified: portable mode detection
└── versions/
    └── *.py                    # Existing migrations

# Windows Distribution Scripts
scripts/windows_dist/
├── START.bat                   # Main launcher (browser auto-open)
├── START_SERVER_ONLY.bat       # Network mode launcher
├── STOP_SERVER.bat             # Server termination
└── README.txt                  # Quick reference guide

# User Documentation
docs/
└── WINDOWS_QUICKSTART.md       # Complete setup and troubleshooting guide (419 lines)

# CI/CD Automation
.github/workflows/
└── release-windows.yml         # GitHub Actions build pipeline

# Distribution Output (not in repo)
dist/
└── bcd-api/                    # PyInstaller output
    ├── bcd-api.exe             # Main executable
    ├── _internal/              # Bundled dependencies
    │   ├── bcd_web_vue/        # Web UI files
    │   ├── migrations/         # Alembic migrations
    │   ├── config/             # .env.example
    │   ├── alembic.ini         # Migration config
    │   └── [libraries]         # Python packages + shared libs
    ├── data/                   # Created on first run
    └── config/                 # Created on first run
```

## Research Summary

### PyInstaller vs. Alternatives

**PyInstaller (SELECTED)**:
- ✅ Mature (10+ years), widely used
- ✅ Supports complex dependencies (FastAPI, SQLAlchemy, Pandas)
- ✅ Good hook ecosystem for popular packages
- ✅ One-folder mode (fast startup)
- ✅ UPX compression built-in
- ❌ Large bundle size (~200MB with all deps)
- ❌ No cross-compilation (need Windows to build Windows exe)

**py2exe (REJECTED)**:
- ✅ Smaller bundles
- ❌ Python 3.9 max (no 3.11+ support)
- ❌ Fewer hooks for modern packages
- ❌ Less active maintenance

**Nuitka (REJECTED)**:
- ✅ Compiles to C (faster startup, smaller size)
- ✅ Better performance
- ❌ Long compilation time (30+ minutes for large apps)
- ❌ Requires C compiler on build machine
- ❌ More complex build configuration

**cx_Freeze (REJECTED)**:
- ✅ Cross-platform
- ❌ Weaker FastAPI/SQLAlchemy support
- ❌ Less documentation for web apps

### Decision: PyInstaller + one-folder mode

**Rationale**: Best balance of compatibility, ease of use, and community support. One-folder mode chosen over one-file for faster startup and better antivirus compatibility.

## Architecture Decisions

### 1. Portable Mode Detection

**Pattern**: Runtime detection via `sys.frozen` attribute

```python
def is_portable() -> bool:
    """Check if running as PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
```

**Rationale**: Standard PyInstaller detection pattern. `sys.frozen=True` when bundled, `sys._MEIPASS` points to temp extraction directory.

### 2. Path Resolution Strategy

**Pattern**: All paths relative to executable directory

```python
def get_app_dir() -> Path:
    """Get application directory."""
    if is_portable():
        return Path(sys.executable).parent  # Directory containing .exe
    else:
        return Path(__file__).parent.parent.parent.parent  # Project root
```

**Rationale**: Cannot rely on current working directory (user might launch from elsewhere). Executable's parent directory is stable reference point.

### 3. User Data Location

**Pattern**: Adjacent directories (`data/`, `config/`) at same level as executable

```text
C:\BCD\
├── bcd-api.exe
├── data/           # User data (survives updates)
│   └── bcd.db
├── config/         # User config (survives updates)
│   └── .env
└── _internal/      # Application files (replaced on update)
```

**Rationale**: Keeps user data separate from application files. Updates overwrite `_internal/` and executable but preserve `data/` and `config/`.

### 4. Database Initialization

**Pattern**: Programmatic Alembic invocation on first run

```python
async def init_database_if_needed():
    db_file = Path(settings.database_url.replace('sqlite:///', ''))
    if not db_file.exists():
        from alembic.config import Config
        from alembic.command import upgrade

        alembic_cfg = Config(str(get_alembic_ini_path()))
        upgrade(alembic_cfg, "head")
```

**Rationale**: Cannot use `alembic` CLI in bundle. Programmatic invocation allows automatic initialization without user intervention.

### 5. Configuration Management

**Pattern**: Template-based `.env` creation

```python
def initialize_portable_environment():
    env_file = get_config_dir() / ".env"
    if not env_file.exists():
        env_example = get_bundled_resource("config/.env.example")
        if env_example:
            shutil.copy(env_example, env_file)
```

**Rationale**: Provides working defaults while allowing user customization. Template bundled in `_internal/`, copied to `config/.env` on first run.

### 6. Build Automation

**Pattern**: GitHub Actions workflow triggered on version tags

```yaml
on:
  push:
    tags:
      - 'v*.*.*'  # Trigger on v1.0.0, v1.1.0, etc.
```

**Rationale**: Ensures consistent builds, automates release process, provides download artifacts and checksums.

## Implementation Phases

### Phase 0: Research & Design ✅ COMPLETED

**Outcome**: Selected PyInstaller, designed portable mode architecture

**Decisions**:
- PyInstaller one-folder mode
- Adjacent `data/` and `config/` directories
- Programmatic Alembic migrations
- GitHub Actions for builds

### Phase 1: Core Portable Mode Support ✅ COMPLETED

**Files Modified/Created**:

1. `src/bcd_api/core/portable.py` - NEW
   - `is_portable()` - Runtime detection
   - `get_app_dir()` - Executable directory
   - `get_data_dir()` - User data location
   - `get_config_dir()` - Configuration location
   - `get_migrations_dir()` - Bundled migrations
   - `get_bundled_resource()` - Bundled files in `_MEIPASS`
   - `initialize_portable_environment()` - First-run setup

2. `src/bcd_api/core/config.py` - MODIFIED
   - `_get_env_file_path()` - Dynamic `.env` location
   - `_get_database_url()` - Dynamic DB path
   - Import fallback for portable module

3. `src/bcd_api/main.py` - MODIFIED
   - Import `portable` module with fallback
   - Dynamic `WEB_DIR` based on mode
   - `startup_event()` - Call `initialize_portable_environment()`
   - `init_database_if_needed()` - Programmatic migrations

4. `migrations/env.py` - MODIFIED
   - Portable mode detection
   - `sys.path` adjustments for bundled imports

### Phase 2: PyInstaller Configuration ✅ COMPLETED

**File Created**: `bcd-api.spec`

**Key Configuration**:

```python
# Hidden imports (68 modules)
hiddenimports = [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', ...
    'fastapi', 'starlette', ...
    'sqlalchemy', 'sqlalchemy.ext.baked', ...
    'alembic', 'alembic.runtime', ...
    'pydantic', 'pydantic_settings', ...
    'pandas', 'pymarc', 'reportlab', 'python_barcode', ...
]

# Data files
datas = [
    ('src/bcd_web_vue', 'bcd_web_vue'),
    ('migrations', 'migrations'),
    ('alembic.ini', '.'),
    ('.env.example', 'config'),
]

# Exclusions (reduce size)
excludes = [
    'pytest', 'black', 'ruff', 'mypy', 'ipython',
    'matplotlib', 'scipy', 'jupyter', 'notebook',
]

# Build settings
upx=True  # Enable compression
console=True  # Show server logs
```

### Phase 3: Windows Distribution Scripts ✅ COMPLETED

**Files Created**: `scripts/windows_dist/`

1. **START.bat** (37 lines)
   - Creates `data/` and `config/` directories
   - Detects first run (missing `bcd.db`)
   - Opens browser to `http://127.0.0.1:8000`
   - Runs `bcd-api.exe`
   - Handles paths with spaces

2. **START_SERVER_ONLY.bat** (24 lines)
   - Network mode (no browser launch)
   - Shows IP address instructions
   - Supports `API_HOST=0.0.0.0` binding

3. **STOP_SERVER.bat** (18 lines)
   - `taskkill /F /IM bcd-api.exe`
   - Success/failure message

4. **README.txt** (145 lines)
   - Quick start guide
   - System requirements
   - First run explanation
   - Configuration options
   - Backup/update procedures
   - Troubleshooting

### Phase 4: User Documentation ✅ COMPLETED

**File Created**: `docs/WINDOWS_QUICKSTART.md` (419 lines)

**Sections**:
- Installation (system requirements, directory structure)
- First Run (initialization process)
- Basic Usage (web interface, features)
- Configuration (editing `.env`, common changes)
- Network Access (binding to 0.0.0.0, firewall setup)
- Backup and Restore (procedures, automation)
- Updating (safe upgrade process)
- Troubleshooting (8 common issues + solutions)
- Advanced Topics (CLI options, CSV import, PostgreSQL migration)

### Phase 5: CI/CD Automation ✅ COMPLETED

**File Created**: `.github/workflows/release-windows.yml` (212 lines)

**Pipeline**:

1. **Test Stage** (Ubuntu)
   - Run unit tests
   - Run integration tests
   - Only proceed if tests pass

2. **Build Stage** (Windows)
   - Install Python 3.11 + dependencies
   - Download UPX 4.2.2
   - Run PyInstaller: `pyinstaller --clean --upx-dir=upx bcd-api.spec`
   - Create distribution folder:
     ```
     BCD-v1.0.0-Windows/
     ├── bcd-api.exe
     ├── _internal/
     ├── START.bat
     ├── START_SERVER_ONLY.bat
     ├── STOP_SERVER.bat
     ├── README.txt
     ├── VERSION.txt
     ├── LICENSE.txt
     ├── docs/WINDOWS_QUICKSTART.md
     └── config/.env.example
     ```
   - Create ZIP archive
   - Generate SHA256 checksums

3. **Release Stage**
   - Create GitHub Release
   - Upload ZIP file
   - Upload checksums
   - Auto-generate release notes

**Trigger**: Git tags matching `v*.*.*` (e.g., `v1.0.0`)

## Testing Strategy

### Automated Testing

1. **Unit Tests** (Python)
   - `test_portable.py` - Test portable mode detection
   - `test_paths.py` - Test path resolution
   - Mock `sys.frozen` to simulate bundle

2. **Integration Tests** (Python)
   - Test first-run initialization
   - Test database migration execution
   - Test `.env` creation

### Manual Testing (Critical)

1. **Clean Machine Test**
   - Extract ZIP on Windows 10/11 with no Python
   - Double-click `START.bat`
   - Verify browser opens, UI works

2. **Network Mode Test**
   - Configure `API_HOST=0.0.0.0`
   - Access from second computer
   - Verify full functionality

3. **Update Test**
   - Run v1.0.0, create data
   - Extract v1.1.0 over existing
   - Verify data persists, migrations run

4. **Backup/Restore Test**
   - Copy `data/` folder
   - Modify database
   - Restore from backup
   - Verify original data returns

### Performance Testing

- First launch (with init): < 10s on 5-year-old hardware
- Subsequent launches: < 3s
- Memory usage: < 200MB at idle
- Disk space: < 200MB total

## Deployment Process

### Development Build (Linux/macOS)

```bash
# Install PyInstaller
pip install pyinstaller

# Build (creates Linux/macOS executable)
pyinstaller --clean bcd-api.spec

# Output: dist/bcd-api/
```

### Production Build (Windows)

**Option 1: GitHub Actions** (Recommended)

```bash
# Tag version
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# GitHub Actions automatically:
# - Runs tests
# - Builds on Windows runner
# - Creates release with ZIP
```

**Option 2: Local Windows Build**

```powershell
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Download UPX (optional, for compression)
Invoke-WebRequest -Uri "https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-win64.zip" -OutFile "upx.zip"
Expand-Archive upx.zip
Rename-Item upx-4.2.2-win64 upx

# Build
pyinstaller --clean --upx-dir=upx bcd-api.spec

# Create distribution
mkdir BCD-v1.0.0-Windows
Copy-Item -Recurse dist/bcd-api/* BCD-v1.0.0-Windows/
Copy-Item scripts/windows_dist/*.bat BCD-v1.0.0-Windows/
Copy-Item docs/WINDOWS_QUICKSTART.md BCD-v1.0.0-Windows/docs/
Copy-Item scripts/windows_dist/README.txt BCD-v1.0.0-Windows/
Copy-Item .env.example BCD-v1.0.0-Windows/config/

# Create ZIP
Compress-Archive -Path BCD-v1.0.0-Windows -DestinationPath BCD-v1.0.0-Windows.zip

# Generate checksum
certutil -hashfile BCD-v1.0.0-Windows.zip SHA256 > BCD-v1.0.0-Windows.zip.sha256
```

## Rollout Plan

### Phase 1: Internal Testing (Week 1)

- Build v1.0.0-rc1
- Test on 3 different Windows machines (Win10, Win11, legacy hardware)
- Verify all user scenarios
- Document issues

### Phase 2: Beta Release (Week 2)

- Build v1.0.0-rc2 with fixes
- Release to 2-3 school librarians for field testing
- Gather feedback on installation, usability
- Update documentation

### Phase 3: General Availability (Week 3)

- Build v1.0.0 final
- Create GitHub Release
- Publish download links
- Announce to user community

### Phase 4: Maintenance

- Monitor GitHub Issues for bug reports
- Release patch versions (v1.0.1, v1.0.2) as needed
- Plan feature releases (v1.1.0, v1.2.0) quarterly

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Windows Defender blocks executable | High | High | Document firewall exception steps, code-sign executable (future) |
| PyInstaller fails to bundle dependency | Medium | High | Extensive testing, explicit hidden imports, hook development |
| Database corruption during update | Low | High | Backup procedures in docs, atomic migration execution |
| Antivirus false positive | Medium | Medium | Submit to antivirus vendors, use VirusTotal, code signing |
| Large bundle size (>200MB) | High | Low | Accept tradeoff, UPX compression, exclude dev deps |
| Migration fails on startup | Low | High | Catch exceptions, display clear error, fallback to fresh DB |

## Success Criteria

✅ Build pipeline creates < 200MB ZIP file
✅ Executable runs on clean Windows 10/11 without Python
✅ First launch completes initialization in < 10s
✅ Subsequent launches in < 3s
✅ Database persists across restarts
✅ Configuration changes apply correctly
✅ Network mode works with 0.0.0.0 binding
✅ Updates preserve user data
✅ SHA256 checksums provided and verified
✅ Comprehensive documentation (419 lines)
✅ Automated CI/CD pipeline functional

## Future Enhancements

- [ ] Code signing certificate (eliminate Windows Defender warnings)
- [ ] Auto-update mechanism (check for new versions, download, apply)
- [ ] Installer wizard (alternative to ZIP extraction)
- [ ] System tray icon (minimize to tray, quick actions)
- [ ] Bundled PostgreSQL option (for multi-user deployments)
- [ ] MacOS portable app bundle (`.app` format)
- [ ] Linux AppImage distribution
