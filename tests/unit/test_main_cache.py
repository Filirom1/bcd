import pytest
from unittest.mock import MagicMock

from starlette.requests import Request
from starlette.responses import Response

from src.bcd_api import main


def request(path):
    return Request({"type": "http", "method": "GET", "path": path, "headers": []})


@pytest.mark.asyncio
async def test_cache_headers_development_static(monkeypatch):
    monkeypatch.setattr(main.settings, "environment", "development")
    result = await main.add_cache_headers(request("/static/app.js"), next_response)
    assert result.headers["cache-control"] == "no-cache, no-store, must-revalidate"


@pytest.mark.asyncio
async def test_cache_headers_production_vendor_and_locale(monkeypatch):
    monkeypatch.setattr(main.settings, "environment", "production")
    vendor = await main.add_cache_headers(request("/static/vendor/vue.js"), next_response)
    locale = await main.add_cache_headers(request("/locales/fr.json"), next_response)
    assert "immutable" in vendor.headers["cache-control"]
    assert locale.headers["cache-control"] == "no-cache, must-revalidate"


@pytest.mark.asyncio
async def test_cache_headers_leave_api_without_cache_header(monkeypatch):
    monkeypatch.setattr(main.settings, "environment", "production")
    result = await main.add_cache_headers(request("/api/v1/health"), next_response)
    assert "cache-control" not in result.headers


async def next_response(request):
    return Response("ok")
