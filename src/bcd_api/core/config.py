"""Application configuration using Pydantic Settings."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.version import get_version

# Import portable mode helpers
try:
    from src.bcd_api.core.portable import get_config_dir, get_data_dir, is_portable
except ImportError:
    # Fallback for development/testing when module might not be in path
    from pathlib import Path

    def is_portable() -> bool:
        return False

    def get_data_dir() -> Path:
        return Path("./data")

    def get_config_dir() -> Path:
        return Path(".")


# Determine env_file path based on mode
def _get_env_file_path() -> str:
    """Get path to .env file based on portable mode."""
    if is_portable():
        return str(get_config_dir() / ".env")
    return ".env"


# Determine database URL based on mode
def _get_database_url() -> str:
    """Get default database URL based on portable mode."""
    if is_portable():
        db_path = get_data_dir() / "bcd.db"
        return f"sqlite:///{db_path}"
    return "sqlite:///./data/bcd.db"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_get_env_file_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = _get_database_url()

    # API Server
    api_host: str = "127.0.0.1"
    api_port: int = 8888

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8888"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Logging
    log_level: str = "INFO"

    # Application
    environment: str = "development"
    app_name: str = "BCD Library System"
    # Version is read from pyproject.toml (single source of truth)
    app_version: str = get_version()

    # BNF API
    bnf_api_url: str = "https://catalogue.bnf.fr/api/SRU"
    bnf_rate_limit: int = 1  # requests per second

    # Google Books API
    google_books_api_key: str = ""  # optional — empty = no key (~1 000 req/day)
    google_books_rate_limit: int = 1  # requests per second

    # SUDOC API — French university library catalog (fallback for periodicals)
    sudoc_api_url: str = "https://www.sudoc.abes.fr/cbs/sru/"
    sudoc_rate_limit: int = 1  # requests per second

    # Catalog source enable/disable (set in .env)
    bnf_enabled: bool = True
    google_books_enabled: bool = True
    sudoc_enabled: bool = True

    # Pagination
    default_page_size: int = 50
    max_page_size: int = 100

    # UI Mode (portable mode only)
    # UI_MODE: "webview" (native window), "browser" (system browser), or "kids" (launch Kids client)
    ui_mode: str = "webview"

    # Client Only Mode
    # If True, does not start the local API server, only launches the specified UI client
    client_only: bool = False

    # Auto-update (portable mode only)
    auto_update: bool = True

    # Path to Kids client executable (used when ui_mode=kids)
    # Can be absolute path or relative to the BCD executable directory
    # Examples: "BCD-Kids.exe", "./kids/BCD-Kids.x86_64", "C:\\Programs\\BCD-Kids\\BCD-Kids.exe"
    kids_client_path: str = ""

    # Authentication (HTTP Basic or Digest Auth)
    # If both auth_username and auth_password are set, authentication is enabled
    # Otherwise, no authentication is required
    auth_username: str = ""
    auth_password: str = ""
    auth_scheme: str = "basic"  # "basic" or "digest"


# Global settings instance
settings = Settings()
