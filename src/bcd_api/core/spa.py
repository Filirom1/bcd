"""SPA rendering and state."""

from fastapi.responses import HTMLResponse
from src.bcd_api.core.web_assets import WebAssetsConfig, render_spa_html


class _SPAState:
    library_code: str = ""


_state = _SPAState()


def update_library_code(code: str) -> None:
    """Appelé par startup.init_system_settings() après lecture DB."""
    _state.library_code = code


def get_library_code() -> str:
    """Retourne le code bibliothèque actuel."""
    return _state.library_code


async def serve_spa(assets_config: WebAssetsConfig, app_version: str) -> HTMLResponse:
    """Serve SPA index.html with library_code injected and cache-busting version."""
    content = render_spa_html(
        assets_config=assets_config,
        library_code=_state.library_code,
        app_version=app_version,
    )
    response = HTMLResponse(content=content)
    if not assets_config.is_source:
        response.headers["Cache-Control"] = "no-cache"
    return response
