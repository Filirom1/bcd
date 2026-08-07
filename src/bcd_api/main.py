"""Main FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from src.bcd_api.api.v1.router import api_router
from src.bcd_api.core import mdns
from src.bcd_api.core.auth import DigestAuthMiddleware, is_auth_enabled
from src.bcd_api.core.config import settings
from src.bcd_api.core.exception_handlers import register_handlers
from src.bcd_api.core.middleware import register_middlewares
from src.bcd_api.core.spa import serve_spa
from src.bcd_api.core.startup import run_startup_tasks, init_database_if_needed
from src.bcd_api.core.logging_config import setup_logging
from src.bcd_api.core.web_assets import get_web_assets, render_spa_html
from src.bcd_api.services.external.bnf import configure as configure_bnf
from src.bcd_api.services.external.cover import configure as configure_covers
from src.bcd_api.services.external.cover import migrate_covers_to_isbn13
from src.bcd_api.services.external.google_books import configure as configure_google_books
from src.bcd_api.services.external.sudoc import configure as configure_sudoc

# Initialize logging — returns the dict passed to uvicorn so its loggers
# (uvicorn.access, uvicorn.error) also write to bcd_api.log.
_log_config = setup_logging()
logger = logging.getLogger(__name__)



# Import portable mode helpers
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


# Web UI configuration and help assets
if is_portable():
    # Help documentation is bundled separately
    help_resource = get_bundled_resource("docs/help")
    HELP_DIR = str(help_resource) if help_resource else "docs/help"
else:
    HELP_DIR = "docs/help"

# Resolve web assets mode & paths
web_assets_config = get_web_assets(
    is_portable_fn=is_portable,
    config_settings=settings,
    bundled_resource_fn=get_bundled_resource,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    await run_startup_tasks(settings, is_portable)
    yield

    # Shutdown
    await mdns.stop_mdns()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="School library management system (Bibliothèque que Claude a Développée)",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

register_handlers(app)
register_middlewares(app, web_assets_config)







# Include API router
app.include_router(api_router)





@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Mount static assets (JS, CSS, images, etc.)
app.mount("/static", StaticFiles(directory=str(web_assets_config.web_dir)), name="static")
app.mount("/locales", StaticFiles(directory=str(web_assets_config.locales_dir)), name="locales")

# Mount node_modules only in dev (source) mode and non-portable
if web_assets_config.is_source:
    app.mount("/node_modules", StaticFiles(directory="node_modules"), name="node_modules")

_covers_dir = Path(settings.covers_dir_path) if settings.covers_dir_path else Path("data/covers")
_covers_dir.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=str(_covers_dir)), name="covers")

# Mount help documentation (markdown + images)
_help_dir = Path(HELP_DIR)
if _help_dir.is_dir():
    app.mount("/help", StaticFiles(directory=str(_help_dir)), name="help")


async def catch_all_spa():
    return await serve_spa(web_assets_config, settings.app_version)


# Catch-all SPA route — must be last to avoid intercepting API / static / locales routes
app.add_api_route("/{full_path:path}", catch_all_spa, methods=["GET"], include_in_schema=False)


from src.bcd_api.core.runner import main  # noqa: F401
