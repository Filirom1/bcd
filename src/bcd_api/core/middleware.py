"""FastAPI Middlewares configuration."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.bcd_api.core.auth import DigestAuthMiddleware
from src.bcd_api.core.config import settings
from src.bcd_api.core.web_assets import WebAssetsConfig


def register_middlewares(app: FastAPI, assets_config: WebAssetsConfig) -> None:
    """Register all middlewares on the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Add HTTP Digest Authentication middleware (must be after CORS)
    app.add_middleware(DigestAuthMiddleware)

    # Cache middleware
    app.middleware("http")(make_cache_middleware(assets_config))


def make_cache_middleware(assets_config: WebAssetsConfig):
    """Factory : retourne le middleware configuré avec assets_config."""
    async def add_cache_headers(request: Request, call_next):
        """Add Cache-Control headers for static assets."""
        response = await call_next(request)
        path = request.url.path

        if assets_config.is_source:
            if path.startswith(("/static/", "/locales/", "/node_modules/", "/covers/")):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        else:
            # Production (built) caching behavior
            if path.startswith("/static/assets/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif path.startswith("/locales/"):
                # Always revalidate locale files so translation updates apply immediately.
                response.headers["Cache-Control"] = "no-cache, must-revalidate"
            elif path.startswith("/static/favicon."):
                response.headers["Cache-Control"] = "public, max-age=3600"
            elif (
                path.startswith("/static/")
                or path.startswith("/covers/")
            ):
                response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    return add_cache_headers
