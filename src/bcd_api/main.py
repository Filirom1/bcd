"""Main FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from pathlib import Path

from src.bcd_api.core.config import settings
from src.bcd_api.core.logging_config import setup_logging
from src.bcd_api.core.exceptions import BCDException
from src.bcd_api.core.auth import DigestAuthMiddleware, is_auth_enabled
from src.bcd_api.api.v1.router import api_router
from src.bcd_api.core import mdns
from src.bcd_api.services.bnf_service import configure as configure_bnf
from src.bcd_api.services.cover_service import configure as configure_covers, migrate_covers_to_isbn13
from src.bcd_api.services.google_books_service import configure as configure_google_books
from src.bcd_api.services.sudoc_service import configure as configure_sudoc

# Initialize logging — returns the dict passed to uvicorn so its loggers
# (uvicorn.access, uvicorn.error) also write to bcd_api.log.
_log_config = setup_logging()
logger = logging.getLogger(__name__)

# Cached library_code for SPA injection — avoids a DB hit on every GET request.
# Updated once at startup by init_system_settings(); invalidated on settings save.
_cached_library_code: str = ""

# Import portable mode helpers
try:
    from src.bcd_api.core.portable import (
        is_portable,
        initialize_portable_environment,
        get_bundled_resource,
        get_app_dir,
    )
except ImportError:
    # Fallback for development/testing
    from typing import Optional

    def is_portable() -> bool:
        return False

    def initialize_portable_environment() -> None:
        pass

    def get_bundled_resource(resource_path: str) -> Optional[Path]:
        return Path(resource_path)


# Web UI directory (Vue 3 implementation)
# Set based on portable mode or development mode
if is_portable():
    # In portable mode, web UI is bundled in _internal or next to executable
    web_resource = get_bundled_resource('bcd_web_vue')
    WEB_DIR = str(web_resource) if web_resource else 'bcd_web_vue'
    # Help documentation is bundled separately
    help_resource = get_bundled_resource('docs/help')
    HELP_DIR = str(help_resource) if help_resource else 'docs/help'
else:
    WEB_DIR = 'src/bcd_web_vue'
    HELP_DIR = 'docs/help'

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url}")
    if is_auth_enabled():
        logger.info(f"Authentication enabled ({settings.auth_scheme.upper()}, user: {settings.auth_username})")

    if is_portable():
        logger.info("Running in portable mode")

    configure_bnf(url=settings.bnf_api_url, rate_limit=settings.bnf_rate_limit)
    configure_google_books(
        api_key=settings.google_books_api_key or None,
        rate_limit=settings.google_books_rate_limit,
    )
    configure_covers(google_api_key=settings.google_books_api_key or None)
    configure_sudoc(url=settings.sudoc_api_url, rate_limit=settings.sudoc_rate_limit)
    await init_system_settings()
    _migrate_covers()
    asyncio.create_task(auto_backup_if_needed())
    asyncio.create_task(init_mdns())

    yield

    # Shutdown
    await mdns.stop_mdns()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="School library management system (Bibliothèque que Claude a Développée)",
    docs_url=f"/api/v1/docs",
    redoc_url=f"/api/v1/redoc",
    openapi_url=f"/api/v1/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add HTTP Digest Authentication middleware (must be after CORS)
app.add_middleware(DigestAuthMiddleware)


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """Add Cache-Control headers for static assets.

    Vendor files never change between releases — tell WebView2/browsers to
    cache them for a full year (immutable).  App JS and locale files may
    change on update, so we allow 1 hour before revalidation.
    This avoids redundant HDD seeks on every app launch after the first.

    In development mode, disable caching to avoid stale file issues.
    """
    response = await call_next(request)
    path = request.url.path

    # In development, disable caching for all static files
    if settings.environment == "development":
        if path.startswith(("/static/", "/locales/", "/assets/", "/covers/")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    else:
        # Production caching behavior
        if path.startswith("/static/vendor/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/locales/"):
            # Always revalidate locale files so translation updates apply immediately.
            # ETags (from StaticFiles) allow 304 responses — no extra bandwidth.
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif path.startswith("/static/") or path.startswith("/assets/") or path.startswith("/covers/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
    return response


# Exception handlers
@app.exception_handler(BCDException)
async def bcd_exception_handler(request: Request, exc: BCDException):
    """Handle custom BCD exceptions with error codes and context."""
    logger.warning(f"BCD Exception: {exc.detail} - {exc.error_code}")
    content = {
        "success": False,
        "error": exc.detail,
        "error_code": getattr(exc, 'error_code', 'UNKNOWN_ERROR'),
        "context": getattr(exc, 'context', {})
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors."""
    logger.error(f"Database integrity error: {exc.orig}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error": "Database integrity error",
            "details": str(exc.orig),
        },
    )


# Include API router
app.include_router(api_router)



async def init_mdns():
    """Read library_code from DB and start mDNS if configured.

    Called as a background task so uvicorn has time to bind its socket before
    we detect the actual listening port.
    """
    # Yield control so uvicorn finishes creating the server socket
    await asyncio.sleep(0.5)

    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services import settings_service

        db = SessionLocal()
        try:
            sys_settings = settings_service.get_settings(db)
            library_code = getattr(sys_settings, "library_code", None)
        finally:
            db.close()

        if library_code:
            hostname = mdns.normalize_hostname(library_code)
            port = mdns.get_server_port(settings.api_port)
            try:
                await asyncio.wait_for(mdns.start_mdns(library_code, port), timeout=10)
                logger.info(
                    f"mDNS active — access via http://{hostname}.local:{port}"
                )
            except asyncio.TimeoutError:
                logger.warning("mDNS registration timed out after 10s — skipped")
        else:
            logger.info("library_code not set — mDNS advertisement skipped")
    except Exception as exc:
        logger.warning(f"mDNS initialisation failed (non-fatal): {exc}")


def _migrate_covers():
    """Rename any ISBN-10 cover files to ISBN-13 (idempotent, non-fatal)."""
    try:
        from src.bcd_api.core.database import SessionLocal
        db = SessionLocal()
        try:
            migrate_covers_to_isbn13(db=db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Cover migration failed (non-fatal): {e}")


def init_database_if_needed():
    """Run Alembic migrations synchronously to ensure the schema is up to date.

    Called from main() before uvicorn starts so no other connection holds the
    SQLite file open during DDL.  Alembic is idempotent — it is a no-op when
    already at head.
    """
    try:
        from alembic.config import Config
        from alembic.command import upgrade
        from src.bcd_api.core.portable import get_alembic_ini_path

        logger.info("Checking database schema (running migrations)...")

        alembic_ini = get_alembic_ini_path()
        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        # Resolve script_location to an absolute path so Alembic can find
        # the migrations folder regardless of the working directory.
        alembic_cfg.set_main_option(
            "script_location", str(alembic_ini.parent / "migrations")
        )

        upgrade(alembic_cfg, "head")

        logger.info("Database schema is up to date.")
    except Exception as e:
        logger.error(f"Error running database migrations: {e}")
        logger.error("Please run 'alembic upgrade head' manually.")


async def init_system_settings():
    """Initialize default system settings if not already present.

    This runs on every startup to ensure settings exist.
    Safe to call multiple times - only creates settings if missing.
    """
    global _cached_library_code
    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services import settings_service

        db = SessionLocal()
        try:
            settings_service.initialize_default_settings(db)
            sys_settings = settings_service.get_settings(db)
            _cached_library_code = getattr(sys_settings, "library_code", None) or ""
            logger.info("System settings initialized")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error initializing system settings: {e}")
        logger.warning("Application may not function correctly without system settings")


async def auto_backup_if_needed():
    """Create a backup on startup if the last one is older than 7 days."""
    try:
        from src.bcd_api.services import backup_service

        backups = sorted(backup_service.list_backups(), key=lambda b: b.created_at, reverse=True)
        if not backups or backups[0].age_days >= 7:
            backup = backup_service.create_backup()
            logger.info(f"Auto-backup created: {backup.filename}")
        else:
            logger.info(f"Auto-backup skipped: last backup is {backups[0].age_days} day(s) old")
    except Exception as e:
        logger.warning(f"Auto-backup failed (non-fatal): {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Mount static assets (JS, CSS, images, etc.)
_web_dir = Path(WEB_DIR)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/locales", StaticFiles(directory=str(_web_dir / "locales")), name="locales")
try:
    _assets_dir = _web_dir / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")
except OSError:
    pass

_covers_dir = Path("data/covers")
_covers_dir.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=str(_covers_dir)), name="covers")

# Mount help documentation (markdown + images)
_help_dir = Path(HELP_DIR)
if _help_dir.is_dir():
    app.mount("/help", StaticFiles(directory=str(_help_dir)), name="help")


async def _serve_spa() -> HTMLResponse:
    """Serve SPA index.html with library_code injected and cache-busting version."""
    html = (_web_dir / "index.html").read_text(encoding="utf-8")

    # Inject library_code into loading screen
    html = html.replace(
        '<h1 class="bcd-title"></h1>',
        f'<h1 class="bcd-title">{_cached_library_code}</h1>',
    )

    # Add cache-busting version to static assets (app.js, CSS, etc.)
    # This ensures browsers fetch new files after upgrades
    html = html.replace(
        'src="/static/js/app.js',
        f'src="/static/js/app.js?v={settings.app_version}',
    )

    return HTMLResponse(content=html)


# Catch-all SPA route — must be last to avoid intercepting API / static / locales routes
app.add_api_route("/{full_path:path}", _serve_spa, methods=["GET"], include_in_schema=False)


def _get_startup_library_code() -> str | None:
    """Read library_code from DB for the startup banner (best-effort)."""
    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services import settings_service

        db = SessionLocal()
        try:
            sys_settings = settings_service.get_settings(db)
            return getattr(sys_settings, "library_code", None)
        finally:
            db.close()
    except Exception:
        return None


def _start_server_thread(host: str, port: int) -> tuple:
    """Start uvicorn in a background thread and wait until ready.

    Returns (server, server_thread) once the server accepts connections.
    """
    import threading
    import time
    import urllib.request
    import uvicorn

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_config=_log_config,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            urllib.request.urlopen(url, timeout=0.5)
            break
        except Exception:
            time.sleep(0.5)

    return server, server_thread


def _run_portable_browser(host: str, port: int):
    """Run in portable mode: open the system browser, no webview dependency.

    Lighter than the webview mode — no WebView2/WebKit process, uses the
    browser already installed on the machine (Firefox, Chrome, Edge…).
    The server keeps running until the user closes the console window or
    presses Ctrl+C.
    """
    import webbrowser

    url = f"http://127.0.0.1:{port}"

    server, server_thread = _start_server_thread(host, port)

    webbrowser.open(url)
    logger.info(f"Browser opened at {url}")

    # Block until the server stops (user kills the process)
    try:
        server_thread.join()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        server.should_exit = True
        server_thread.join(timeout=5)


def _run_portable_kids(host: str, port: int):
    """Run in portable mode: launch Kids client and keep server running.

    Launches the Kids client immediately so its splash screen is visible
    while Alembic migrations run and the API server starts up in the
    background.  By the time the splash ends (~1.5 s), the server is
    usually ready to accept connections.
    """
    import subprocess
    from pathlib import Path

    kids_path = settings.kids_client_path.strip()
    if not kids_path:
        logger.error("KIDS_CLIENT_PATH is not set in config/.env")
        print("\nERROR: KIDS_CLIENT_PATH is not configured.")
        print("Please edit config/.env and set KIDS_CLIENT_PATH to the Kids client executable.")
        print("Example: KIDS_CLIENT_PATH=BCD-Kids.exe")
        return

    # Resolve path (absolute or relative to BCD executable directory)
    kids_path_obj = Path(kids_path)
    if not kids_path_obj.is_absolute():
        kids_path_obj = get_app_dir() / kids_path

    if not kids_path_obj.exists():
        logger.error(f"Kids client not found at: {kids_path_obj}")
        print(f"\nERROR: Kids client executable not found at: {kids_path_obj}")
        print("Please check your KIDS_CLIENT_PATH setting in config/.env")
        return

    # Launch Kids client FIRST so its splash screen is visible immediately
    # while Alembic runs and the server starts in the background.
    process = None
    try:
        logger.info(f"Launching Kids client: {kids_path_obj}")
        process = subprocess.Popen(
            [str(kids_path_obj)],
            cwd=kids_path_obj.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Kids client started (PID: {process.pid})")
    except FileNotFoundError:
        logger.error(f"Failed to launch Kids client: {kids_path_obj}")
        print(f"\nERROR: Could not execute Kids client at: {kids_path_obj}")
        return

    # Run migrations and start API server while the Kids splash is showing
    init_database_if_needed()
    server, server_thread = _start_server_thread(host, port)
    logger.info(f"API server running at http://127.0.0.1:{port}")

    try:
        # Wait for Kids client to exit
        process.wait()
        logger.info("Kids client closed, shutting down server...")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)


def _run_portable(host: str, port: int):
    """Run in portable mode: native webview window, no console.

    Starts uvicorn in a background thread, waits for the server to be ready,
    then opens a native OS webview window (WebView2 on Windows, WebKit on Linux).
    Blocks until the user closes the window, then stops the server.
    """
    import webview

    url = f"http://127.0.0.1:{port}"

    server, _server_thread = _start_server_thread(host, port)

    # Read library_name from DB for the window title (server is ready, settings exist)
    window_title = "BCD"
    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services import settings_service

        db = SessionLocal()
        try:
            sys_settings = settings_service.get_settings(db)
            window_title = getattr(sys_settings, "library_name", None) or "BCD"
        finally:
            db.close()
    except Exception:
        pass

    # Open native webview window — blocks until the user closes it
    window = webview.create_window(
        window_title,
        url,
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    def on_closed():
        server.should_exit = True

    window.events.closed += on_closed

    # Store WebView2 user data next to the executable, not in %APPDATA%.
    # On school domain machines %APPDATA% is a roaming network profile —
    # WebView2 would sync hundreds of MB over the LAN before showing anything.
    webview_cache_dir = str(get_app_dir() / "webview_cache")
    webview.start(storage_path=webview_cache_dir)


def main():
    """Run the application."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(
        prog="bcd",
        description="BCD Library Management System — school library server",
    )
    parser.add_argument(
        "--host",
        default=settings.api_host,
        metavar="HOST",
        help=f"bind address (default: {settings.api_host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        metavar="PORT",
        help=f"listen port (default: {settings.api_port})",
    )
    parser.add_argument(
        "--ui-mode",
        default=settings.ui_mode,
        choices=["webview", "browser", "kids"],
        metavar="MODE",
        help="UI mode: webview (native window), browser (system browser), or kids (Kids client); default: %(default)s",
    )
    args = parser.parse_args()

    # Portable mode: initialize environment, then open window
    if is_portable():
        initialize_portable_environment()

        if settings.auto_update:
            from src.bcd_api.core.updater import check_and_apply_update
            check_and_apply_update(settings.app_version, get_app_dir())

        ui_mode = args.ui_mode.lower()
        if ui_mode == "kids":
            # Kids mode runs migrations internally, after launching the client
            # so the splash screen is visible immediately.
            _run_portable_kids(args.host, args.port)
        elif ui_mode == "webview":
            init_database_if_needed()
            _run_portable(args.host, args.port)
        elif ui_mode == "browser":
            init_database_if_needed()
            _run_portable_browser(args.host, args.port)
        else:
            logger.error(f"Invalid UI mode: {ui_mode}")
            print(f"ERROR: Invalid UI mode '{ui_mode}'. Must be: webview, browser, or kids")
        return

    # Development mode: console output + optional hot reload
    library_code = _get_startup_library_code()

    print("\n" + "=" * 60)
    print("  BCD Library Management System")
    print("  Starting API + Web UI Server (Vue 3)")
    print("=" * 60)
    print(f"  Web UI:   http://{args.host}:{args.port}")
    print(f"  API Docs: http://{args.host}:{args.port}/api/v1/docs")
    if library_code:
        hostname = mdns.normalize_hostname(library_code)
        print(f"  mDNS:     http://{hostname}.local:{args.port}")
    print("=" * 60 + "\n")

    # When reload is enabled uvicorn needs a module string so it can re-import
    # the app in the reloader subprocess.
    reload_enabled = settings.environment == "development"
    uvicorn.run(
        "src.bcd_api.main:app" if reload_enabled else app,
        host=args.host,
        port=args.port,
        reload=reload_enabled,
        log_config=_log_config,
    )


if __name__ == "__main__":
    main()
