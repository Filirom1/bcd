"""Portable mode detection and path helpers for PyInstaller bundles."""

import sys
import shutil
from pathlib import Path
from typing import Optional


def is_portable() -> bool:
    """Check if running as PyInstaller bundle.

    Returns:
        True if running as frozen PyInstaller executable, False otherwise.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_app_dir() -> Path:
    """Get application directory (works in dev and portable mode).

    In portable mode, returns directory containing the executable.
    In development mode, returns project root directory.

    Returns:
        Path to application directory.
    """
    if is_portable():
        # In PyInstaller bundle, sys.executable points to the .exe
        return Path(sys.executable).parent
    else:
        # In development, go up from src/bcd_api/core to project root
        return Path(__file__).parent.parent.parent.parent


def get_data_dir() -> Path:
    """Get data directory for database and user files.

    Creates directory if it doesn't exist.

    Returns:
        Path to data directory.
    """
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir() -> Path:
    """Get configuration directory for .env and settings.

    Creates directory if it doesn't exist.

    Returns:
        Path to config directory.
    """
    config_dir = get_app_dir() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_migrations_dir() -> Path:
    """Get Alembic migrations directory.

    In portable mode, migrations are bundled in _internal/migrations.
    In development mode, migrations are in project root.

    Returns:
        Path to migrations directory.
    """
    if is_portable():
        # In PyInstaller bundle, check _internal directory first
        internal_migrations = get_app_dir() / "_internal" / "migrations"
        if internal_migrations.exists():
            return internal_migrations
        # Fallback to app directory
        return get_app_dir() / "migrations"
    else:
        return get_app_dir() / "migrations"


def get_bundled_resource(resource_path: str) -> Optional[Path]:
    """Get path to bundled resource file.

    In portable mode, resources are in _MEIPASS temporary directory.
    In development mode, resources are relative to project root.

    Args:
        resource_path: Relative path to resource (e.g., 'src/bcd_web_vue')

    Returns:
        Path to resource, or None if not found.
    """
    if is_portable() and hasattr(sys, '_MEIPASS'):
        # PyInstaller extracts bundled files to _MEIPASS temporary directory
        resource = Path(sys._MEIPASS) / resource_path
        if resource.exists():
            return resource

    # Development mode or resource not in _MEIPASS
    resource = get_app_dir() / resource_path
    if resource.exists():
        return resource

    return None


def initialize_portable_environment() -> None:
    """Initialize portable environment on first run.

    Creates necessary directories and copies configuration templates.
    Should be called during application startup when in portable mode.
    """
    if not is_portable():
        return

    # Create required directories
    get_data_dir()
    get_config_dir()

    # Create sample_imports directory for user CSV imports
    sample_imports_dir = get_data_dir() / "sample_imports"
    sample_imports_dir.mkdir(exist_ok=True)

    # Copy .env.example to config/.env if it doesn't exist
    env_file = get_config_dir() / ".env"
    if not env_file.exists():
        env_example = get_bundled_resource("config/.env.example")
        if env_example and env_example.exists():
            shutil.copy(env_example, env_file)
        else:
            # Create minimal .env if template not found
            create_default_env_file(env_file)


def create_default_env_file(env_path: Path) -> None:
    """Create a default .env file with minimal configuration.

    Args:
        env_path: Path where .env file should be created.
    """
    if sys.platform == "win32":
        kids_client_path = "BCD-Kids.exe"
    else:
        kids_client_path = "./BCD-Kids.x86_64"

    default_env = f"""# BCD Library Management System — Configuration
# Copied to config/.env on first run. Edit to customize.

# Database
# Leave commented out — BCD auto-detects the correct absolute path.
# Uncomment only to override with a custom database location.
# DATABASE_URL=sqlite:///./data/bcd.db

# API Server
API_HOST=127.0.0.1
API_PORT=8000

# Logging: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=production

# BNF API — French National Library ISBN lookup
BNF_API_URL=https://catalogue.bnf.fr/api/SRU
BNF_RATE_LIMIT=1

# UI Mode
# UI_MODE: Choose which interface to launch on startup
#   webview = native OS window (WebView2 on Windows, WebKit on Linux)
#   browser = system browser (Firefox, Chrome, Edge, etc.)
#   kids    = launch BCD Kids client (interface enfants 6-11 ans)
UI_MODE=kids

# Path to BCD Kids executable (required when UI_MODE=kids)
# Can be absolute path or relative to the BCD executable directory
KIDS_CLIENT_PATH={kids_client_path}

# Authentication (HTTP Basic or Digest Auth)
# If both AUTH_USERNAME and AUTH_PASSWORD are set, authentication is enabled.
# Otherwise, no authentication is required (open access).
# AUTH_SCHEME: "basic" (widely supported, better browser compatibility) or "digest" (more secure over HTTP)
# Leave AUTH_USERNAME and AUTH_PASSWORD empty to disable authentication.
AUTH_USERNAME=
AUTH_PASSWORD=
AUTH_SCHEME=basic
"""
    env_path.write_text(default_env, encoding='utf-8')


def get_alembic_ini_path() -> Path:
    """Get path to alembic.ini configuration file.

    Returns:
        Path to alembic.ini.
    """
    if is_portable():
        # In bundle, alembic.ini should be in _internal or app directory
        internal_ini = get_app_dir() / "_internal" / "alembic.ini"
        if internal_ini.exists():
            return internal_ini
        return get_app_dir() / "alembic.ini"
    else:
        return get_app_dir() / "alembic.ini"
