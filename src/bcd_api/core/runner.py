"""Runner for the BCD server in both portable and developer modes."""

import argparse
import asyncio
import logging
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn

from src.bcd_api.core import mdns
from src.bcd_api.core.config import settings
from src.bcd_api.core.startup import init_database_if_needed

logger = logging.getLogger(__name__)

try:
    from src.bcd_api.core.portable import (
        get_app_dir,
        get_bundled_resource,
        initialize_portable_environment,
        is_portable,
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

    def get_app_dir() -> Path:
        return Path(".")


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
    """Start uvicorn in a background thread and wait until ready."""
    from src.bcd_api.main import app, _log_config

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
    """Run in portable mode: open the system browser, no webview dependency."""
    import webbrowser

    url = f"http://{host}:{port}" if settings.client_only else f"http://127.0.0.1:{port}"

    if settings.client_only:
        logger.info(f"CLIENT_ONLY is enabled. Opening browser at {url}")
        webbrowser.open(url)
        print("\n" + "=" * 60)
        print("  BCD Client-Only Mode (Browser)")
        print("=" * 60)
        print(f"  Connected to remote server: {url}")
        print("  Press Ctrl+C to exit.")
        print("=" * 60 + "\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, exiting...")
        return

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
    """Run in portable mode: launch Kids client and keep server running."""
    import subprocess

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

    if settings.client_only:
        logger.info("CLIENT_ONLY is enabled. API server startup and migrations skipped.")
        try:
            process.wait()
            logger.info("Kids client closed.")
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, exiting...")
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
    """Run in portable mode: native webview window, no console."""
    import webview

    url = f"http://{host}:{port}" if settings.client_only else f"http://127.0.0.1:{port}"

    server = None
    if settings.client_only:
        logger.info(f"CLIENT_ONLY is enabled. Connecting webview to remote server at {url}")
    else:
        server, _server_thread = _start_server_thread(host, port)

    # Read library_name from DB for the window title (server is ready, settings exist)
    window_title = "BCD"
    if not settings.client_only:
        try:
            from src.bcd_api.core.database import SessionLocal
            from src.bcd_api.services import settings_service

            db = SessionLocal()
            try:
                sys_settings = settings_service.get_settings(db)
                window_title = getattr(sys_settings, "library_name", None) or "BCD"
            finally:
                db.close()
            # If server stopped or closed before webview, uvicorn doesn't get shut down.
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
        if server:
            server.should_exit = True

    window.events.closed += on_closed

    # Store WebView2 user data next to the executable, not in %APPDATA%.
    # On school domain machines %APPDATA% is a roaming network profile —
    # WebView2 would sync hundreds of MB over the LAN before showing anything.
    webview_cache_dir = str(get_app_dir() / "webview_cache")
    webview.start(storage_path=webview_cache_dir)


def _parse_args(args_list=None) -> argparse.Namespace:
    """Helper to parse command line arguments."""
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
    parser.add_argument(
        "--client-only",
        action="store_true",
        default=settings.client_only,
        help="Run in client-only mode (do not start the local server, only launch the client UI)",
    )
    if args_list is not None:
        return parser.parse_args(args_list)
    return parser.parse_args()


def main() -> None:
    """Run the application."""
    args = _parse_args()

    if args.client_only:
        settings.client_only = True

    # Portable mode: initialize environment, then open window
    if is_portable():
        initialize_portable_environment()

        if settings.auto_update:
            from src.bcd_api.core.updater import check_and_apply_update

            check_and_apply_update(settings.app_version, get_app_dir())

    # If running in portable mode OR client-only mode, launch the client UI directly
    if is_portable() or settings.client_only:
        ui_mode = args.ui_mode.lower()
        if ui_mode == "kids":
            _run_portable_kids(args.host, args.port)
        elif ui_mode == "webview":
            if not settings.client_only:
                init_database_if_needed()
            _run_portable(args.host, args.port)
        elif ui_mode == "browser":
            if not settings.client_only:
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
    from src.bcd_api.main import app, _log_config

    reload_enabled = settings.environment == "development"
    uvicorn.run(
        "src.bcd_api.main:app" if reload_enabled else app,
        host=args.host,
        port=args.port,
        reload=reload_enabled,
        log_config=_log_config,
    )
