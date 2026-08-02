from pathlib import Path

import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.bcd_api import main
from src.bcd_api.core.web_assets import WebAssetsConfig


def request(path):
    return Request({"type": "http", "method": "GET", "path": path, "headers": []})


@pytest.mark.asyncio
async def test_cache_headers_source_mode(monkeypatch):
    # Set web_assets_config as source mode
    config = WebAssetsConfig(
        web_dir=Path("src/bcd_web_vue"),
        html_path=Path("src/bcd_web_vue/templates/spa-shell.html"),
        locales_dir=Path("src/bcd_web_vue/locales"),
        is_built=False,
        is_source=True,
    )
    monkeypatch.setattr(main, "web_assets_config", config)

    result = await main.add_cache_headers(request("/static/app.js"), next_response)
    assert result.headers["cache-control"] == "no-cache, no-store, must-revalidate"

    result_locales = await main.add_cache_headers(request("/locales/fr.json"), next_response)
    assert result_locales.headers["cache-control"] == "no-cache, no-store, must-revalidate"


@pytest.mark.asyncio
async def test_cache_headers_production_build_mode(monkeypatch):
    # Set web_assets_config as built mode
    config = WebAssetsConfig(
        web_dir=Path("build/web"),
        html_path=Path("build/web/index.html"),
        locales_dir=Path("build/web/locales"),
        is_built=True,
        is_source=False,
    )
    monkeypatch.setattr(main, "web_assets_config", config)

    asset = await main.add_cache_headers(request("/static/assets/app-hash.js"), next_response)
    locale = await main.add_cache_headers(request("/locales/fr.json"), next_response)
    favicon = await main.add_cache_headers(request("/static/favicon.svg"), next_response)

    assert "immutable" in asset.headers["cache-control"]
    assert "max-age=31536000" in asset.headers["cache-control"]
    assert locale.headers["cache-control"] == "no-cache, must-revalidate"
    assert "max-age=3600" in favicon.headers["cache-control"]


@pytest.mark.asyncio
async def test_cache_headers_leave_api_without_cache_header(monkeypatch):
    config = WebAssetsConfig(
        web_dir=Path("build/web"),
        html_path=Path("build/web/index.html"),
        locales_dir=Path("build/web/locales"),
        is_built=True,
        is_source=False,
    )
    monkeypatch.setattr(main, "web_assets_config", config)

    result = await main.add_cache_headers(request("/api/v1/health"), next_response)
    assert "cache-control" not in result.headers


async def next_response(request):
    return Response("ok")
