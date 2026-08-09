# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for BCD API server (Windows and Linux portable distribution)."""

import sys
from pathlib import Path

# Verify that the Web UI production build is present before proceeding.
# This prevents packaging stale development sources or an incomplete build.
build_web_dir = Path('build/web')
if not (build_web_dir / 'index.html').is_file() or not (build_web_dir / '.vite' / 'manifest.json').is_file():
    print("\n" + "="*80)
    print("  ERROR: Web UI production build is missing or incomplete!")
    print("  Please run 'npm run build:web' before compiling the PyInstaller executable.")
    print("="*80 + "\n")
    sys.exit(1)

block_cipher = None
is_windows = sys.platform == 'win32'

# Collect all hidden imports required for FastAPI, uvicorn, SQLAlchemy, Alembic
hiddenimports = [
    # Uvicorn and ASGI server dependencies
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # FastAPI and Starlette dependencies
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.staticfiles',
    'starlette.middleware',
    'starlette.middleware.cors',
    # SQLAlchemy ORM and SQL
    'sqlalchemy',
    'sqlalchemy.ext.baked',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.sql',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.orm',
    'sqlalchemy.orm.strategies',
    'sqlalchemy.pool',
    # Alembic migrations
    'alembic',
    'alembic.runtime',
    'alembic.runtime.migration',
    'alembic.operations',
    'alembic.operations.ops',
    'alembic.script',
    'alembic.command',
    # Pydantic for validation
    'pydantic',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    'pydantic_settings',
    'pydantic.v1',
    # Click CLI (used by Alembic)
    'click',
    # XML parsing for BNF API (UNIMARC/SRU responses)
    'lxml',
    'lxml.etree',
    # HTTP client for BNF API
    'httpx',
    # Format converters (bcd_converters package)
    'bcd_converters',
    'bcd_converters.bibliopuce_to_dublin_core',
    'bcd_converters.onde_to_bcd_borrowers',
    'bcd_converters.xls_classes_to_csv',
    # Native webview window (uses OS WebView2/WebKit — no bundled browser)
    'webview',
    'webview.util',
    'webview.event',
    'webview.window',
    'webview.platforms',
    'webview.guilib',
    'webview.platforms.winforms' if is_windows else 'webview.platforms.gtk',
    # tkinter — used by the auto-updater dialog (stdlib, must be listed explicitly)
    'tkinter',
    'tkinter.messagebox',
]

# Data files to include in the bundle
datas = [
    # Web UI (Vue 3 Production Build) - compiled assets
    ('build/web', 'bcd_web_vue'),
    # Help documentation (served via symlink at src/bcd_web_vue/help)
    ('docs/help', 'docs/help'),
    # Alembic migrations - needed for database initialization
    ('migrations', 'migrations'),
    # Alembic configuration
    ('alembic.ini', '.'),
    # Configuration template
    ('.env.example', 'config'),
    # Version source - read by src/shared/version.py at runtime
    ('pyproject.toml', '.'),
    # Sample import files for catalog, borrowers, and classes
    ('data/sample_imports', 'data/sample_imports'),
    # CSV templates for catalog and borrowers imports
    ('data/templates', 'data/templates'),
    # Documentation
    ('LICENSE', '.'),
    ('README.md', '.'),
    ('README_FR.md', '.'),
    ('INSTALL.md', '.'),
    ('DEVELOPERS.md', '.'),
]

# Collect all Python source files
a = Analysis(
    ['src/bcd_api/main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude development/testing dependencies
        # Dev/test tools and data-science packages that may be present in the
        # build environment but must not end up in the portable bundle
        'pytest', 'pytest_asyncio', 'pytest_cov', 'pytest_mock',
        'black', 'ruff', 'mypy', 'ipython',
        'matplotlib', 'scipy', 'jupyter', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Bundle everything into the PYZ archive
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='bcd',
    icon='src/bcd_web_vue/favicon.ico' if is_windows else 'src/bcd_web_vue/favicon.png',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect all files into a directory (--onedir mode)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='bcd',
)
