# BCD Scripts

Utilities for BCD development and deployment.

## Version Management

### bump_version.py (UNIFIED)

A unified script that manages versions for the entire project (API + CLI + Kids client).

**Usage**:
```bash
# Show the current version
python scripts/bump_version.py --current

# Bump the version (updates both the API and Kids client)
python scripts/bump_version.py patch   # 1.0.0 -> 1.0.1 (bug fixes)
python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0 (new features)
python scripts/bump_version.py major   # 1.0.0 -> 2.0.0 (breaking changes)

# Bump and push (triggers all releases)
python scripts/bump_version.py patch --push
```

**Actions**:
- Updates `pyproject.toml` (the single source of truth)
- Updates `bcd_kids/export_presets.cfg` to match `pyproject.toml`
- Creates a `chore: bump version to X.X.X` commit
- Creates two annotated tags:
  - `vX.X.X` → triggers API releases (Windows + Linux)
  - `godot-vX.X.X` → triggers Kids client releases (Windows + Linux)
- With `--push`, pushes the commit and tags to trigger these workflows:
  - `.github/workflows/release-windows.yml`
  - `.github/workflows/release-linux.yml`
  - `.github/workflows/release-godot.yml`

**Options**:
- `--current` — Show the current version
- `--push` — Push automatically after creating the tags
- `--no-commit` — Update files only; do not create a commit or tags

**Important**: The entire project uses a single version. The script keeps the API and Kids client versions in sync.

## Release Workflow

### Python Backend

1. Run the tests (the commands are explicit; no global filter hides unmarked tests):
   ```bash
   pytest tests -m "not external and not e2e and not slow"  # fast phase with coverage gate
   pytest tests -m "slow or external or e2e"                # remaining phase, exactly once
   ```

2. Bump the version and push:
   ```bash
   python scripts/bump_version.py patch --push
   ```

3. GitHub Actions:
   - Build the portable Windows application with PyInstaller
   - Build the portable Linux application with PyInstaller
   - Create a GitHub Release with binaries and checksums
   - Upload artifacts

### Kids Client

1. Test the client:
   ```bash
   # Open bcd_kids/project.godot in Godot 4.6
   # Press F5 and test the features
   ```

2. Bump the version and push:
   ```bash
   python scripts/bump_godot_version.py patch --push
   ```

3. GitHub Actions:
   - Build the Windows client
   - Build the Linux client
   - Create a GitHub Release with binaries and checksums
   - Upload artifacts

## Versioning Scheme

Both projects follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (incompatible API or features)
- **MINOR**: New backward-compatible features
- **PATCH**: Backward-compatible bug fixes

### Examples

**Backend**:
- `1.0.0 → 1.0.1` — Fix a bug in the search API
- `1.0.1 → 1.1.0` — Add a statistics API endpoint
- `1.1.0 → 2.0.0` — Completely redesign the data model

**Kids Client**:
- `1.0.0 → 1.0.1` — Fix a search crash
- `1.0.1 → 1.1.0` — Add a statistics screen
- `1.1.0 → 2.0.0` — Change the architecture (incompatible with API v1)

## Other Scripts

### reset_and_simulate.py

Reset the database and simulate nine months of activity:
```bash
python reset_and_simulate.py
```

Useful for:
- Performance testing
- Demonstrations
- Development with realistic data

### build_web.mjs

Build the production Web UI with Vite:
```bash
node scripts/build_web.mjs
```

### verify_web_build.mjs

Build the Web UI and verify its structural integrity:
```bash
npm run verify:web-build
```

### web_ui.py

A single command to build, verify, test, and package the Web UI:
```bash
npm run web                         # build and verify build/web/
npm run web -- --manual             # serve build/web/ with FastAPI for manual testing
npm run web -- --client-only        # launch Kids client-only with the local mDNS proxy
npm run web -- --e2e                 # run the Playwright smoke test
npm run web -- --portable            # create the PyInstaller package
npm run web -- --portable --manual   # create and launch the portable executable
npm run web -- --e2e --portable      # run the smoke test, then create the portable package
```

`--manual` blocks until the server stops or the executable is closed. Use `--host` and
`--port` to configure its address (default: `127.0.0.1:8888`). `--client-only` launches
the Kids client directly without rebuilding the Web UI when `KIDS_CLIENT_PATH` points to
an existing executable. If the path is missing or invalid, the script displays a warning
and runs only the small mDNS discovery proxy on `127.0.0.1:<port>` (default port 8888)
until interrupted. It does not start the BCD API or database. The mDNS discovery lets the
Kids client find BCD servers on the network.

### take_screenshots.py

Generate screenshots for the documentation:
```bash
python scripts/take_screenshots.py
```

### generate_help_screenshots.py

Generate screenshots for the contextual help:
```bash
python scripts/generate_help_screenshots.py
```

### enrich_bibliopuce.py

Enrich a BiblioPuce export with BNF data:
```bash
python scripts/enrich_bibliopuce.py input.csv output.csv
```

## Notes

- All Python scripts use `#!/usr/bin/env python3`
- Version scripts require a clean Git working tree (no uncommitted changes)
- Version scripts ask for confirmation before proceeding
- Created tags are annotated with a descriptive message
- GitHub Actions workflows are triggered automatically by tags
