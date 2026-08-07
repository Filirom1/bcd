from pathlib import Path
import pytest

from src.bcd_api.core.spa import update_library_code, serve_spa, _state
from src.bcd_api.core.web_assets import WebAssetsConfig


def test_update_library_code_persists():
    update_library_code("BCD42")
    assert _state.library_code == "BCD42"


@pytest.mark.asyncio
async def test_serve_spa_injects_library_code(monkeypatch):
    config = WebAssetsConfig(
        web_dir=Path("src/bcd_web_vue"),
        html_path=Path("src/bcd_web_vue/templates/spa-shell.html"),
        locales_dir=Path("src/bcd_web_vue/locales"),
        is_built=False,
        is_source=True,
    )
    # Mock render_spa_html to check it receives library_code
    calls = []

    def mock_render_spa_html(assets_config, library_code, app_version):
        calls.append((assets_config, library_code, app_version))
        return "<html>injected</html>"

    monkeypatch.setattr("src.bcd_api.core.spa.render_spa_html", mock_render_spa_html)

    update_library_code("BCD-TEST-CODE")
    response = await serve_spa(config, "1.0.0")

    assert len(calls) == 1
    assert calls[0][1] == "BCD-TEST-CODE"
    assert response.body == b"<html>injected</html>"


@pytest.mark.asyncio
async def test_serve_spa_sets_no_cache_in_prod(monkeypatch):
    config = WebAssetsConfig(
        web_dir=Path("build/web"),
        html_path=Path("build/web/index.html"),
        locales_dir=Path("build/web/locales"),
        is_built=True,
        is_source=False,
    )

    monkeypatch.setattr("src.bcd_api.core.spa.render_spa_html", lambda *a, **k: "<html></html>")

    response = await serve_spa(config, "1.0.0")
    assert response.headers["Cache-Control"] == "no-cache"
