"""Web assets configuration and resolution for development and production modes."""

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from src.bcd_api.core.config import Settings


@dataclass(frozen=True)
class WebAssetsConfig:
    """Immutable configuration holding paths and metadata for Web UI assets."""

    web_dir: Path
    html_path: Path
    locales_dir: Path
    is_built: bool
    is_source: bool


def get_web_assets(
    is_portable_fn: Callable[[], bool],
    config_settings: Settings,
    bundled_resource_fn: Callable[[str], Optional[Path]],
) -> WebAssetsConfig:
    """Resolve assets paths and metadata based on portable/dev/build mode settings."""
    if is_portable_fn():
        web_resource = bundled_resource_fn("bcd_web_vue")
        web_dir = Path(web_resource) if web_resource else Path("bcd_web_vue")
        # In portable mode, we always use the pre-built web UI
        return WebAssetsConfig(
            web_dir=web_dir,
            html_path=web_dir / "index.html",
            locales_dir=web_dir / "locales",
            is_built=True,
            is_source=False,
        )

    mode = config_settings.web_assets_mode

    if mode == "build":
        web_dir = Path("build/web")
        html_path = web_dir / "index.html"
        manifest_path = web_dir / ".vite" / "manifest.json"

        # Check for presence of vital build components
        if not html_path.is_file() or not manifest_path.is_file():
            raise RuntimeError(
                f"Web build is missing at {web_dir}. Please run 'npm run build:web' "
                f"to generate the production assets before starting in 'build' mode."
            )

        return WebAssetsConfig(
            web_dir=web_dir,
            html_path=html_path,
            locales_dir=web_dir / "locales",
            is_built=True,
            is_source=False,
        )

    elif mode == "source":
        web_dir = Path("src/bcd_web_vue")
        # In development mode, check that node_modules/ exist
        node_modules_dir = Path("node_modules")
        if not node_modules_dir.is_dir():
            raise RuntimeError(
                "Development dependencies are missing. Please run 'npm ci' or 'npm install' "
                "before starting the server in 'source' mode."
            )

        return WebAssetsConfig(
            web_dir=web_dir,
            html_path=web_dir / "templates" / "spa-shell.html",
            locales_dir=web_dir / "locales",
            is_built=False,
            is_source=True,
        )

    else:
        raise ValueError(f"Invalid WEB_ASSETS_MODE: {mode}")


def render_spa_html(
    assets_config: WebAssetsConfig,
    library_code: str,
    app_version: str,
) -> str:
    """Load and render the SPA HTML with injected library code and assets."""
    escaped_code = html.escape(library_code)

    if assets_config.is_built:
        # For build or portable mode, we just read the Vite-generated index.html and inject the library code
        raw_html = assets_config.html_path.read_text(encoding="utf-8")
        return raw_html.replace("__BCD_LIBRARY_CODE__", escaped_code)

    # For source (dev) mode, we load the spa-shell.html and dynamically inject dev assets
    shell_html = assets_config.html_path.read_text(encoding="utf-8")

    head_assets = """
    <!-- Bootstrap 5.3.3 CSS -->
    <link href="/node_modules/bootstrap/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Bootstrap Icons 1.11.3 -->
    <link rel="stylesheet" href="/node_modules/bootstrap-icons/font/bootstrap-icons.min.css">

    <!-- Custom CSS -->
    <link rel="stylesheet" href="/static/css/main.css">
    <link rel="stylesheet" href="/static/css/loading.css">
    <link rel="stylesheet" href="/static/css/print-labels.css">
"""

    body_assets = f"""
    <!-- Vue 3.4.21 (Global Build) -->
    <script src="/node_modules/vue/dist/vue.global.prod.js"></script>

    <!-- Vue Router 4.2.5 (Global Build) -->
    <script src="/node_modules/vue-router/dist/vue-router.global.prod.js"></script>

    <!-- Vue I18n 9.14.5 (Global Build) -->
    <script src="/node_modules/vue-i18n/dist/vue-i18n.global.prod.js"></script>

    <!-- Bootstrap 5.3.3 JS Bundle (includes Popper) -->
    <script src="/node_modules/bootstrap/dist/js/bootstrap.bundle.min.js"></script>

    <!-- marked.js v9 for markdown rendering in help panels -->
    <script src="/node_modules/marked/marked.min.js"></script>

    <!-- JsBarcode for client-side barcode generation -->
    <script src="/node_modules/jsbarcode/dist/JsBarcode.all.min.js"></script>

    <!-- Chart.js v4.4.3 for collection analytics histograms -->
    <script src="/node_modules/chart.js/dist/chart.umd.js"></script>

    <!-- Application Scripts -->
    <script type="module" src="/static/js/app.js?v={app_version}"></script>
"""

    rendered = shell_html.replace("__BCD_LIBRARY_CODE__", escaped_code)
    rendered = rendered.replace("<!-- BCD_HEAD_ASSETS -->", head_assets)
    rendered = rendered.replace("<!-- BCD_BODY_ASSETS -->", body_assets)

    return rendered
