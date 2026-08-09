"""Startup and lifecycle background tasks."""

import asyncio
import logging
from src.bcd_api.core import mdns
from src.bcd_api.core.auth import is_auth_enabled
from src.bcd_api.services.external.bnf import configure as configure_bnf
from src.bcd_api.services.external.google_books import configure as configure_google_books
from src.bcd_api.services.external.cover import (
    configure as configure_covers,
    migrate_covers_to_isbn13,
)
from src.bcd_api.services.external.sudoc import configure as configure_sudoc

logger = logging.getLogger(__name__)


async def run_startup_tasks(config_settings, is_portable_fn) -> None:
    """Point d'entrée unique appelé par lifespan."""
    _log_startup_info(config_settings, is_portable_fn)
    _configure_external_services(config_settings)
    library_code = await init_system_settings()
    expire_ready_holds_on_startup()
    _migrate_covers()
    asyncio.create_task(auto_backup_if_needed())
    asyncio.create_task(init_mdns(config_settings))


def _log_startup_info(config_settings, is_portable_fn) -> None:
    logger.info(f"Starting {config_settings.app_name} v{config_settings.app_version}")
    logger.info(f"Environment: {config_settings.environment}")
    logger.info(f"Database: {config_settings.database_url}")
    if is_auth_enabled():
        logger.info(
            f"Authentication enabled ({config_settings.auth_scheme.upper()}, user: {config_settings.auth_username})"
        )
    if is_portable_fn():
        logger.info("Running in portable mode")


def _configure_external_services(config_settings) -> None:
    configure_bnf(url=config_settings.bnf_api_url, rate_limit=config_settings.bnf_rate_limit)
    configure_google_books(
        api_key=config_settings.google_books_api_key or None,
        rate_limit=config_settings.google_books_rate_limit,
    )
    configure_covers(google_api_key=config_settings.google_books_api_key or None)
    configure_sudoc(url=config_settings.sudoc_api_url, rate_limit=config_settings.sudoc_rate_limit)


async def init_system_settings() -> str:
    """Initialize default system settings if not already present."""
    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services import settings_service

        db = SessionLocal()
        try:
            settings_service.initialize_default_settings(db)
            sys_settings = settings_service.get_settings(db)
            library_code = getattr(sys_settings, "library_code", None) or ""
            logger.info("System settings initialized")

            # Update cache in spa state
            from src.bcd_api.core.spa import update_library_code
            update_library_code(library_code)

            return library_code
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error initializing system settings: {e}")
        logger.warning("Application may not function correctly without system settings")
        return ""


def expire_ready_holds_on_startup() -> None:
    """Remove expired ready holds and promote their successors."""
    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services.holds import commands as hold_commands

        db = SessionLocal()
        try:
            expired_count = hold_commands.expire_ready_holds(db)
            if expired_count:
                logger.info("Expired %s ready hold(s) at startup", expired_count)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Ready-hold expiration failed at startup (non-fatal): %s", exc)


def _migrate_covers() -> None:
    """Rename any ISBN-10 cover files to ISBN-13 (idempotent, non-fatal)."""
    try:
        from src.bcd_api.core.database import SessionLocal

        db = SessionLocal()
        try:
            migrate_covers_to_isbn13(db=db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Cover migration failed (non-fatal): {e}")


async def auto_backup_if_needed() -> None:
    """Create a backup on startup if the last one is older than 7 days."""
    try:
        from src.bcd_api.services import backup_service

        backups = sorted(backup_service.list_backups(), key=lambda b: b.created_at, reverse=True)
        if not backups or backups[0].age_days >= 7:
            backup = backup_service.create_backup()
            logger.info(f"Auto-backup created: {backup.filename}")
        else:
            logger.info(f"Auto-backup skipped: last backup is {backups[0].age_days} day(s) old")
    except Exception as e:
        logger.warning(f"Auto-backup failed (non-fatal): {e}")


async def init_mdns(config_settings) -> None:
    """Read library_code from DB and start mDNS if configured."""
    await asyncio.sleep(0.5)

    try:
        from src.bcd_api.core.database import SessionLocal
        from src.bcd_api.services import settings_service

        db = SessionLocal()
        try:
            sys_settings = settings_service.get_settings(db)
            library_code = getattr(sys_settings, "library_code", None)
        finally:
            db.close()

        if library_code:
            hostname = mdns.normalize_hostname(library_code)
            port = mdns.get_server_port(config_settings.api_port)
            try:
                await asyncio.wait_for(mdns.start_mdns(library_code, port), timeout=10)
                logger.info(f"mDNS active — access via http://{hostname}.local:{port}")
            except asyncio.TimeoutError:
                logger.warning("mDNS registration timed out after 10s — skipped")
        else:
            logger.info("library_code not set — mDNS advertisement skipped")
    except Exception as exc:
        logger.warning(f"mDNS initialisation failed (non-fatal): {exc}")


def init_database_if_needed(config_settings=None) -> None:
    """Run Alembic migrations synchronously to ensure the schema is up to date."""
    if config_settings is None:
        from src.bcd_api.core.config import settings as default_settings
        config_settings = default_settings
    try:
        from alembic.command import upgrade
        from alembic.config import Config

        from src.bcd_api.core.portable import get_alembic_ini_path

        logger.info("Checking database schema (running migrations)...")

        alembic_ini = get_alembic_ini_path()
        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", config_settings.database_url)
        alembic_cfg.set_main_option("script_location", str(alembic_ini.parent / "migrations"))

        upgrade(alembic_cfg, "head")

        logger.info("Database schema is up to date.")
    except Exception as e:
        logger.error(f"Error running database migrations: {e}")
        logger.error("Please run 'alembic upgrade head' manually.")
