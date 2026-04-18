# Feature Specification: Windows Portable Distribution

**Feature Branch**: `002-windows-portable`
**Created**: 2026-01-30 (retroactive documentation)
**Completed**: 2026-02-05
**Status**: Implemented
**Input**: User requirement: "Create a zero-installation Windows portable archive that bundles BCD as a standalone executable with all dependencies, no Python required"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Zero-Installation Deployment (Priority: P1)

A school librarian receives a USB drive or downloads a ZIP file containing BCD. They extract the ZIP to any folder on their Windows 10/11 computer (e.g., `C:\BCD`) and double-click `START.bat`. The application automatically initializes a database, starts the server, opens a web browser to the UI, and is ready to use - all without installing Python, Node.js, or any other dependencies.

**Why this priority**: This is the primary deployment method for non-technical users in schools. Without this, librarians would need to install Python, dependencies, and configure environments - a non-starter for most school IT policies. This enables 95% of target users to run BCD.

**Independent Test**: Can be fully tested by extracting the ZIP on a clean Windows machine with no Python installed, double-clicking START.bat, and verifying the web UI opens. Delivers immediate value by removing all technical barriers to adoption.

**Acceptance Scenarios**:

1. **Given** a Windows 10/11 computer with no Python installed, **When** user extracts BCD ZIP file to `C:\BCD` and double-clicks `START.bat`, **Then** server starts, database is initialized, and browser opens to `http://127.0.0.1:8000` within 5 seconds
2. **Given** BCD has never been run before, **When** user first launches `START.bat`, **Then** system creates `data/` directory, creates `config/.env` file from template, runs Alembic migrations to initialize `data/bcd.db`, and displays "First-time setup: Initializing database..." message
3. **Given** BCD data directory exists from previous run, **When** user launches `START.bat`, **Then** system skips initialization, starts server immediately, and preserves all existing library data
4. **Given** port 8000 is already in use, **When** user edits `config/.env` to set `API_PORT=8001` and restarts, **Then** server starts on port 8001 and browser opens to `http://127.0.0.1:8001`
5. **Given** BCD is running, **When** user presses `Ctrl+C` in the console window, **Then** server shuts down gracefully and releases the port

---

### User Story 2 - Network Access for Multiple Workstations (Priority: P2)

A librarian wants to access BCD from multiple computers on the school network. They edit `config/.env` to set `API_HOST=0.0.0.0`, restart the server using `START_SERVER_ONLY.bat`, find their computer's IP address (e.g., 192.168.1.100), and other computers browse to `http://192.168.1.100:8000` to access the shared library system.

**Why this priority**: Important for schools with multiple library workstations but not essential for single-computer deployments. Enables shared access without setting up a dedicated server.

**Independent Test**: Can be tested by configuring network binding and accessing from another computer on the same LAN. Delivers value by enabling multi-user access.

**Acceptance Scenarios**:

1. **Given** librarian runs BCD on computer with IP 192.168.1.100, **When** they edit `config/.env` to set `API_HOST=0.0.0.0` and restart server, **Then** server binds to all network interfaces
2. **Given** BCD server is bound to 0.0.0.0, **When** another computer on the network browses to `http://192.168.1.100:8000`, **Then** web UI loads and functions identically to local access
3. **Given** Windows Firewall is enabled, **When** BCD tries to bind to 0.0.0.0, **Then** Windows prompts for firewall permission (user must allow access)
4. **Given** `START_SERVER_ONLY.bat` is used, **When** server starts, **Then** browser does not auto-launch (console shows IP instructions instead)

---

### User Story 3 - Data Backup and Restore (Priority: P3)

A librarian needs to back up their library database before a major catalog import or at end of term. They stop the server using `Ctrl+C` or `STOP_SERVER.bat`, copy the entire `data/` folder to a USB drive or network location, and restart the server. To restore, they stop the server, replace the `data/` folder with the backup copy, and restart.

**Why this priority**: Essential for data safety but typically done monthly or before major changes. Not a daily operation.

**Independent Test**: Can be tested by creating library data, backing up `data/` folder, modifying data, restoring backup, and verifying original data returns. Delivers value by ensuring data safety.

**Acceptance Scenarios**:

1. **Given** BCD is running with library data in `data/bcd.db`, **When** librarian stops server, copies `data/` folder to `D:\Backups\BCD-2026-02-05\`, and restarts server, **Then** BCD continues running with same data
2. **Given** backup exists at `D:\Backups\BCD-2026-02-05\`, **When** librarian stops server, deletes current `data/` folder, copies backup to `data/`, and restarts, **Then** BCD restores to backup state
3. **Given** librarian wants to start fresh, **When** they stop server, delete `data/bcd.db` file, and restart, **Then** BCD re-initializes empty database using migrations

---

### User Story 4 - Version Updates (Priority: P3)

A librarian receives notification of BCD v1.1.0 release with new features. They download the new ZIP file, stop the current server, extract the new version over the existing installation (overwriting all files), and restart. The update preserves all library data and configuration settings. If database schema changed, migrations run automatically on first launch.

**Why this priority**: Important for long-term maintenance but typically done quarterly. Not a daily operation.

**Independent Test**: Can be tested by simulating upgrade from v1.0.0 to v1.1.0 with data preservation. Delivers value by enabling safe updates.

**Acceptance Scenarios**:

1. **Given** BCD v1.0.0 is running with library data, **When** librarian stops server, extracts BCD v1.1.0 ZIP over existing folder, and restarts, **Then** executable updates, data preserves, and version shows v1.1.0 in console output
2. **Given** v1.1.0 includes new database columns, **When** librarian first launches updated version, **Then** Alembic migrations run automatically and display "Running migrations..." message
3. **Given** extraction overwrites `config/.env`, **When** librarian had custom settings (port 8001), **Then** custom settings are lost (documented in upgrade notes to backup config/)

---

### Edge Cases

- What happens when user extracts BCD to a path with spaces (e.g., `C:\Program Files\BCD`)? → Batch files use `cd /d "%~dp0"` to handle paths with spaces correctly
- How does system handle Windows Defender blocking the executable? → Documentation includes steps to add firewall exception or click "Run anyway"
- What if database file is corrupted? → User can delete `data/bcd.db` and restart to reinitialize (data loss, must restore from backup)
- Can multiple BCD instances run simultaneously? → Yes, if using different ports (edit `config/.env` for each instance)
- What happens if Alembic migrations fail during first run? → Error message displayed, database remains uninitialized, user must check logs or report issue

## Requirements *(mandatory)*

### Functional Requirements

1. **Bundling Requirements**
   - Bundle entire Python runtime and all dependencies into standalone executable
   - Include FastAPI server, SQLAlchemy, Alembic, Pandas, Pillow, ReportLab, lxml, pymarc
   - Bundle Vue 3 web UI (HTML/CSS/JS files)
   - Bundle Alembic migrations for database initialization
   - Include configuration template (`.env.example`)

2. **Portable Mode Detection**
   - Detect when running as PyInstaller bundle vs. development mode
   - Use executable's directory as application root (not current working directory)
   - Create `data/` and `config/` directories adjacent to executable
   - Load `.env` from `config/` instead of project root

3. **First-Run Initialization**
   - Detect missing `data/bcd.db` and trigger initialization
   - Run Alembic migrations programmatically to create schema
   - Copy `.env.example` to `config/.env` if missing
   - Create `data/sample_imports/` for CSV imports

4. **Batch Launchers**
   - `START.bat` - Launch server and open browser
   - `START_SERVER_ONLY.bat` - Launch server without browser (for network mode)
   - `STOP_SERVER.bat` - Forcefully terminate server process

5. **Update Preservation**
   - `data/` and `config/` directories preserved across updates
   - Migrations run automatically on first launch after update
   - Version number displayed in console output

### Non-Functional Requirements

1. **Performance**
   - First launch (with initialization): < 10 seconds on 5-year-old hardware
   - Subsequent launches: < 3 seconds
   - Executable size: < 50 MB (compressed with UPX)
   - Total distribution size: < 200 MB (as ZIP)

2. **Platform Support**
   - Windows 10 (64-bit) minimum
   - Windows 11 (64-bit) supported
   - No Python installation required on target machine
   - No internet connection required for normal operation (except BNF API lookups)

3. **User Experience**
   - Double-click to start (no command-line knowledge required)
   - Browser auto-launches to correct URL
   - Clear console messages for initialization and errors
   - Visual feedback for all operations

4. **Security**
   - No embedded credentials or secrets
   - Default binding to localhost only (127.0.0.1)
   - SHA256 checksums provided for download verification
   - Documented firewall configuration for network mode

5. **Maintainability**
   - PyInstaller spec file version-controlled
   - CI/CD automation via GitHub Actions
   - Deterministic builds (same inputs → same outputs)
   - Clear separation of application code and user data

### Constitution Compliance

This feature aligns with:

- **Principle #6 (Performance for Legacy Hardware)**: Runs on 5+ year old Windows computers, tested on minimal specs
- **Principle #2 (Library-First Approach)**: Uses PyInstaller (established tool) instead of custom bundling
- **Principle #8 (Research-First Feature Design)**: Based on analysis of PyInstaller, py2exe, Nuitka alternatives
- **Principle #7 (Database Schema Versioning)**: Alembic migrations bundled and run programmatically
- **Principle #10 (Internationalization)**: All i18n strings bundled with application

## Technical Constraints

1. **PyInstaller Limitations**
   - Cannot cross-compile (Windows build requires Windows runner)
   - Hidden imports must be explicitly declared in spec file
   - Some packages require hooks (pydantic, sqlalchemy, uvicorn, pandas)
   - One-folder mode preferred over one-file (faster startup, better antivirus compatibility)

2. **Path Resolution**
   - All file paths must be relative to executable directory
   - Cannot rely on current working directory
   - Bundled resources in `_internal/` or `_MEIPASS` temp directory
   - Database path must use absolute path in SQLite URL

3. **Migration Constraints**
   - Alembic must run programmatically (no CLI available in bundle)
   - Migration directory must be discoverable at runtime
   - `alembic.ini` must support portable paths

4. **Windows-Specific**
   - Batch files use Windows path separators (`\`)
   - Process termination via `taskkill /IM bcd-api.exe`
   - Browser launch via `start` command
   - Console window required (not windowed application)

## Open Questions

- [RESOLVED] How to handle Alembic migrations in bundle? → Run programmatically via `alembic.command.upgrade()`
- [RESOLVED] Where to store user data? → Adjacent to executable in `data/` directory
- [RESOLVED] How to detect portable mode? → Check `sys.frozen` and `sys._MEIPASS`
- [RESOLVED] One-file or one-folder? → One-folder (faster, better compatibility)
- [RESOLVED] How to minimize size? → UPX compression + exclude dev dependencies

## Success Metrics

- [ ] ZIP file downloads and extracts successfully on Windows 10/11
- [ ] `START.bat` launches server and opens browser within 5 seconds (subsequent runs)
- [ ] First-time initialization completes within 10 seconds
- [ ] Database persists across restarts
- [ ] Configuration changes in `.env` apply after restart
- [ ] Network mode works when `API_HOST=0.0.0.0`
- [ ] Backup and restore via `data/` folder copy works correctly
- [ ] Update from v1.0.0 → v1.1.0 preserves data and runs migrations
- [ ] No Python installation required on target machine
- [ ] Total distribution size < 200 MB
- [ ] SHA256 checksum verification passes
