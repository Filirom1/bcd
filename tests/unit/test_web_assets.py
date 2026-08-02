import html
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.bcd_api.core.config import Settings
from src.bcd_api.core.web_assets import WebAssetsConfig, get_web_assets, render_spa_html


def test_get_web_assets_source_non_portable(tmp_path, monkeypatch):
    """Test asset resolution in non-portable source (dev) mode with node_modules present."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.web_assets_mode = "source"

    # Mock is_portable to return False
    def is_portable_fn():
        return False

    def bundled_resource_fn(path):
        return None

    # Patch Path.is_dir to pretend node_modules exists
    original_is_dir = Path.is_dir

    def mock_is_dir(self):
        if str(self) == "node_modules":
            return True
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", mock_is_dir)

    config = get_web_assets(is_portable_fn, settings_mock, bundled_resource_fn)

    assert config.is_source is True
    assert config.is_built is False
    assert config.web_dir == Path("src/bcd_web_vue")
    assert config.html_path == Path("src/bcd_web_vue/templates/spa-shell.html")
    assert config.locales_dir == Path("src/bcd_web_vue/locales")


def test_get_web_assets_source_missing_node_modules(monkeypatch):
    """Test that source mode raises RuntimeError if node_modules is missing."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.web_assets_mode = "source"

    def is_portable_fn():
        return False

    def bundled_resource_fn(path):
        return None

    # Patch Path.is_dir to pretend node_modules does not exist
    original_is_dir = Path.is_dir

    def mock_is_dir(self):
        if str(self) == "node_modules":
            return False
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", mock_is_dir)

    with pytest.raises(RuntimeError, match="Development dependencies are missing"):
        get_web_assets(is_portable_fn, settings_mock, bundled_resource_fn)


def test_get_web_assets_build_non_portable(monkeypatch):
    """Test asset resolution in non-portable build mode with built files present."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.web_assets_mode = "build"

    def is_portable_fn():
        return False

    def bundled_resource_fn(path):
        return None

    # Patch Path.is_file to pretend build files exist
    original_is_file = Path.is_file

    def mock_is_file(self):
        if str(self) in ("build/web/index.html", "build/web/.vite/manifest.json"):
            return True
        return original_is_file(self)

    monkeypatch.setattr(Path, "is_file", mock_is_file)

    config = get_web_assets(is_portable_fn, settings_mock, bundled_resource_fn)

    assert config.is_source is False
    assert config.is_built is True
    assert config.web_dir == Path("build/web")
    assert config.html_path == Path("build/web/index.html")
    assert config.locales_dir == Path("build/web/locales")


def test_get_web_assets_build_missing_files(monkeypatch):
    """Test that build mode raises RuntimeError if index.html or manifest is missing."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.web_assets_mode = "build"

    def is_portable_fn():
        return False

    def bundled_resource_fn(path):
        return None

    # Patch Path.is_file to pretend files do not exist
    original_is_file = Path.is_file

    def mock_is_file(self):
        if str(self) in ("build/web/index.html", "build/web/.vite/manifest.json"):
            return False
        return original_is_file(self)

    monkeypatch.setattr(Path, "is_file", mock_is_file)

    with pytest.raises(RuntimeError, match="Web build is missing at build/web"):
        get_web_assets(is_portable_fn, settings_mock, bundled_resource_fn)


def test_get_web_assets_portable(monkeypatch):
    """Test asset resolution in portable mode (always treated as built)."""
    settings_mock = MagicMock(spec=Settings)
    # Even if mode is set to "source", portable mode forces build-like behavior
    settings_mock.web_assets_mode = "source"

    def is_portable_fn():
        return True

    def bundled_resource_fn(path):
        return Path("/mocked/bundled_dir")

    config = get_web_assets(is_portable_fn, settings_mock, bundled_resource_fn)

    assert config.is_source is False
    assert config.is_built is True
    assert config.web_dir == Path("/mocked/bundled_dir")
    assert config.html_path == Path("/mocked/bundled_dir/index.html")
    assert config.locales_dir == Path("/mocked/bundled_dir/locales")


def test_get_web_assets_invalid_mode():
    """Test that an invalid web_assets_mode raises ValueError."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.web_assets_mode = "invalid_mode"

    def is_portable_fn():
        return False

    def bundled_resource_fn(path):
        return None

    with pytest.raises(ValueError, match="Invalid WEB_ASSETS_MODE: invalid_mode"):
        get_web_assets(is_portable_fn, settings_mock, bundled_resource_fn)


def test_render_spa_html_source(monkeypatch):
    """Test SPA HTML rendering in source mode (escaped code, no markers left)."""
    # Create fake spa-shell.html
    shell_content = "<html><head><!-- BCD_HEAD_ASSETS --></head><body><h1>__BCD_LIBRARY_CODE__</h1><!-- BCD_BODY_ASSETS --></body></html>"

    original_read_text = Path.read_text

    def mock_read_text(self, encoding=None):
        if "spa-shell.html" in str(self):
            return shell_content
        return original_read_text(self, encoding)

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    config = WebAssetsConfig(
        web_dir=Path("src/bcd_web_vue"),
        html_path=Path("src/bcd_web_vue/templates/spa-shell.html"),
        locales_dir=Path("src/bcd_web_vue/locales"),
        is_built=False,
        is_source=True,
    )

    library_code = 'L’École & "Claude" <test>'
    app_version = "1.2.3"

    html_out = render_spa_html(config, library_code, app_version)

    # Check that library code is properly HTML-escaped
    expected_escaped = html.escape(library_code)
    assert expected_escaped in html_out
    assert (
        "L’École &amp; &#x27;&#x27;Claude&#x27;&#x27; &lt;test&gt;" not in html_out
    )  # Ensure exact escaping
    assert "L’École &amp; &quot;Claude&quot; &lt;test&gt;" in html_out

    # Check that markers are replaced
    assert "<!-- BCD_HEAD_ASSETS -->" not in html_out
    assert "<!-- BCD_BODY_ASSETS -->" not in html_out
    assert "__BCD_LIBRARY_CODE__" not in html_out

    # Check that app.js version-busting is added
    assert "app.js?v=1.2.3" in html_out

    # Check that node_modules are loaded
    assert "/node_modules/vue/dist/vue.global.prod.js" in html_out


def test_render_spa_html_build(monkeypatch):
    """Test SPA HTML rendering in build mode (escaped code, keeps Vite-generated assets)."""
    # Create fake index.html from Vite
    index_content = "<html><head><script type='module' src='/static/assets/main-hash.js'></script></head><body><h1>__BCD_LIBRARY_CODE__</h1></body></html>"

    original_read_text = Path.read_text

    def mock_read_text(self, encoding=None):
        if "index.html" in str(self):
            return index_content
        return original_read_text(self, encoding)

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    config = WebAssetsConfig(
        web_dir=Path("build/web"),
        html_path=Path("build/web/index.html"),
        locales_dir=Path("build/web/locales"),
        is_built=True,
        is_source=False,
    )

    library_code = 'L’École & "Claude" <test>'
    app_version = "1.2.3"

    html_out = render_spa_html(config, library_code, app_version)

    # Check that library code is properly HTML-escaped
    expected_escaped = html.escape(library_code)
    assert expected_escaped in html_out

    # Ensure Vite-generated code is preserved
    assert "/static/assets/main-hash.js" in html_out
    assert "node_modules" not in html_out
